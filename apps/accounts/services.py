"""
SMS notification service for employee account management.

Employees authenticate and manage their accounts entirely via SMS/OTP because
they may not have an email address. Admins and clients use email instead.

OTP flows   (Twilio Verify — Twilio sends the code):
    - send_activation_otp        → account activation
    - send_password_reset_otp    → password reset request

Notification flows (Twilio Messages — we send the text via template):
    - send_confirmation_sms      → account activated successfully
    - send_password_changed_sms  → password changed successfully
    - send_password_reset_confirm_sms → password reset successfully

Verification:
    - verify_sms_otp             → validate the OTP the user provided

Every send (success or failure) is logged to the corresponding message table.
"""

import logging

from django.conf import settings
from django.template.loader import render_to_string

from apps.core.rate_limiting import RateLimitExceeded, enforce_rate_limit

from .models import (
    AdminMessages,
    ClientMessages,
    EmployeeMessages,
    MessageChannel,
    MessageStatus,
    MessageType,
    Role,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _twilio_client():
    from twilio.rest import Client
    return Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def _render_sms(template_name, user):
    context = {'first_name': user.first_name, 'site_name': settings.SITE_NAME}
    return render_to_string(f'sms/{template_name}.txt', context).strip()


def _log(user, msg_type, status, message, error_message=''):
    kwargs = dict(
        messageType=msg_type,
        channel=MessageChannel.SMS,
        status=status,
        message=message,
        error_message=error_message,
    )
    try:
        if user.role == Role.EMPLOYEE:
            EmployeeMessages.objects.create(employee=user, **kwargs)
        elif user.role == Role.ADMIN:
            AdminMessages.objects.create(admin=user, **kwargs)
        elif user.role == Role.CLIENT:
            ClientMessages.objects.create(client=user, **kwargs)
    except Exception:
        logger.exception("Error al guardar registro de SMS en bitácora")


def _check_limits(user_id):
    """Enforces SMS rate limits. Raises RateLimitExceeded if exceeded."""
    enforce_rate_limit('sms', user_id)


# ---------------------------------------------------------------------------
# OTP flows — Twilio Verify handles the message content
# ---------------------------------------------------------------------------

def send_activation_otp(user, phone=None):
    """
    Sends an OTP for account activation via Twilio Verify.
    Returns the Twilio Verification object.
    """
    from twilio.base.exceptions import TwilioRestException

    target_phone = phone or user.phone_number

    try:
        _check_limits(user.id)
    except RateLimitExceeded as e:
        _log(user, MessageType.ACTIVATION, MessageStatus.FAILED,
                f"OTP de activación bloqueado para {target_phone}", str(e))
        raise

    try:
        verification = _twilio_client().verify.v2.services(
            settings.TWILIO_VERIFY_SERVICE_SID
        ).verifications.create(to=target_phone, channel='sms')

        _log(user, MessageType.ACTIVATION, MessageStatus.SUCCESS,
                f"OTP de activación enviado a {target_phone} — status: {verification.status}")
        return verification

    except TwilioRestException as e:
        _log(user, MessageType.ACTIVATION, MessageStatus.FAILED,
                f"Error al enviar OTP de activación a {target_phone}", str(e))
        raise


def send_password_reset_otp(user, phone=None):
    """
    Sends an OTP for password reset via Twilio Verify.
    Returns the Twilio Verification object.
    """
    from twilio.base.exceptions import TwilioRestException

    target_phone = phone or user.phone_number

    try:
        _check_limits(user.id)
    except RateLimitExceeded as e:
        _log(user, MessageType.PASSWORD_RESET, MessageStatus.FAILED,
                f"OTP de restablecimiento bloqueado para {target_phone}", str(e))
        raise

    try:
        verification = _twilio_client().verify.v2.services(
            settings.TWILIO_VERIFY_SERVICE_SID
        ).verifications.create(to=target_phone, channel='sms')

        _log(user, MessageType.PASSWORD_RESET, MessageStatus.SUCCESS,
                f"OTP de restablecimiento enviado a {target_phone} — status: {verification.status}")
        return verification

    except TwilioRestException as e:
        _log(user, MessageType.PASSWORD_RESET, MessageStatus.FAILED,
                f"Error al enviar OTP de restablecimiento a {target_phone}", str(e))
        raise


# ---------------------------------------------------------------------------
# Notification flows — we send the text using our templates
# ---------------------------------------------------------------------------

def send_confirmation_sms(user, phone=None):
    """
    Sends a confirmation SMS after the employee activates their account.
    Returns the Twilio Message object.
    """
    from twilio.base.exceptions import TwilioRestException

    target_phone = phone or user.phone_number
    body = _render_sms('confirmation', user)

    try:
        _check_limits(user.id)
    except RateLimitExceeded as e:
        _log(user, MessageType.CONFIRMATION, MessageStatus.FAILED,
                f"SMS de confirmación bloqueado para {target_phone}", str(e))
        raise

    try:
        message = _twilio_client().messages.create(
            to=target_phone,
            from_=settings.TWILIO_FROM_NUMBER,
            body=body,
        )
        _log(user, MessageType.CONFIRMATION, MessageStatus.SUCCESS, body)
        return message

    except TwilioRestException as e:
        _log(user, MessageType.CONFIRMATION, MessageStatus.FAILED,
                f"Error al enviar SMS de confirmación a {target_phone}", str(e))
        raise


def send_password_changed_sms(user, phone=None):
    """
    Sends an SMS notifying the employee that their password was changed.
    Returns the Twilio Message object.
    """
    from twilio.base.exceptions import TwilioRestException

    target_phone = phone or user.phone_number
    body = _render_sms('password_changed', user)

    try:
        _check_limits(user.id)
    except RateLimitExceeded as e:
        _log(user, MessageType.PASSWORD_CHANGE, MessageStatus.FAILED,
                f"SMS de cambio de contraseña bloqueado para {target_phone}", str(e))
        raise

    try:
        message = _twilio_client().messages.create(
            to=target_phone,
            from_=settings.TWILIO_FROM_NUMBER,
            body=body,
        )
        _log(user, MessageType.PASSWORD_CHANGE, MessageStatus.SUCCESS, body)
        return message

    except TwilioRestException as e:
        _log(user, MessageType.PASSWORD_CHANGE, MessageStatus.FAILED,
                f"Error al enviar SMS de cambio de contraseña a {target_phone}", str(e))
        raise


def send_password_reset_confirm_sms(user, phone=None):
    """
    Sends an SMS confirming the employee's password was successfully reset.
    Returns the Twilio Message object.
    """
    from twilio.base.exceptions import TwilioRestException

    target_phone = phone or user.phone_number
    body = _render_sms('password_reset_confirm', user)

    try:
        _check_limits(user.id)
    except RateLimitExceeded as e:
        _log(user, MessageType.PASSWORD_RESET_CONFIRM, MessageStatus.FAILED,
                f"SMS de confirmación de restablecimiento bloqueado para {target_phone}", str(e))
        raise

    try:
        message = _twilio_client().messages.create(
            to=target_phone,
            from_=settings.TWILIO_FROM_NUMBER,
            body=body,
        )
        _log(user, MessageType.PASSWORD_RESET_CONFIRM, MessageStatus.SUCCESS, body)
        return message

    except TwilioRestException as e:
        _log(user, MessageType.PASSWORD_RESET_CONFIRM, MessageStatus.FAILED,
                f"Error al enviar SMS de confirmación de restablecimiento a {target_phone}", str(e))
        raise


# ---------------------------------------------------------------------------
# OTP verification — not logged (no message is sent to the user)
# ---------------------------------------------------------------------------

def verify_sms_otp(user, code, phone=None):
    """
    Verifies an OTP code via Twilio Verify.
    Returns True if approved, False if the code is wrong or expired.
    Raises TwilioRestException on API errors.
    """
    from twilio.base.exceptions import TwilioRestException

    target_phone = phone or user.phone_number
    try:
        check = _twilio_client().verify.v2.services(
            settings.TWILIO_VERIFY_SERVICE_SID
        ).verification_checks.create(to=target_phone, code=code)
        return check.status == 'approved'
    except TwilioRestException:
        logger.exception(f"Error al verificar OTP para {target_phone}")
        raise
