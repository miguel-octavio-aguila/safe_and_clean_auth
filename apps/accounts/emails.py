"""
Djoser email overrides for Admin and Client users.

Each class:
    1. Enforces email rate limits before sending.
    2. Calls super().send() — the actual email goes out via Resend.
    3. Logs success or failure to AdminMessages / ClientMessages.

Employees do NOT use email — they use the SMS service in services.py.
"""

import logging

from djoser import email as djoser_email
from rest_framework.exceptions import Throttled

from apps.core.rate_limiting import RateLimitExceeded, enforce_rate_limit

from .models import AdminMessages, ClientMessages, MessageChannel, MessageStatus, MessageType, Role

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_limits(user_id):
    enforce_rate_limit('email', user_id)


def _log(user, msg_type, recipient, status, error_message=''):
    if status == MessageStatus.SUCCESS:
        description = f"Correo de {MessageType(msg_type).label.lower()} enviado a {recipient}"
    else:
        description = f"Error al enviar correo de {MessageType(msg_type).label.lower()} a {recipient}"

    kwargs = dict(
        messageType=msg_type,
        channel=MessageChannel.EMAIL,
        status=status,
        message=description,
        error_message=error_message,
    )
    try:
        if user.role == Role.ADMIN:
            AdminMessages.objects.create(admin=user, **kwargs)
        elif user.role == Role.CLIENT:
            ClientMessages.objects.create(client=user, **kwargs)
    except Exception:
        logger.exception("Error al guardar registro de correo en bitácora")


def _send(instance, to, msg_type):
    """
    Shared send logic used by all subclasses:
        - Rate limit check  (blocks + logs failure on limit)
        - super().send()    (logs failure on error)
        - Success log
    """
    user = instance.context.get('user')
    recipient = to[0] if to else (user.email if user else 'desconocido')

    if user:
        try:
            _check_limits(user.id)
        except RateLimitExceeded as e:
            _log(user, msg_type, recipient, MessageStatus.FAILED, str(e))
            raise Throttled(detail=str(e))

    try:
        super(type(instance), instance).send(to)
    except Throttled:
        raise
    except Exception as e:
        if user:
            _log(user, msg_type, recipient, MessageStatus.FAILED, str(e))
        raise

    if user:
        _log(user, msg_type, recipient, MessageStatus.SUCCESS)


# ---------------------------------------------------------------------------
# Djoser email overrides
# ---------------------------------------------------------------------------

class ActivationEmail(djoser_email.ActivationEmail):
    def send(self, to, *args, **kwargs):
        _send(self, to, MessageType.ACTIVATION)


class ConfirmationEmail(djoser_email.ConfirmationEmail):
    def send(self, to, *args, **kwargs):
        _send(self, to, MessageType.CONFIRMATION)


class PasswordResetEmail(djoser_email.PasswordResetEmail):
    def send(self, to, *args, **kwargs):
        _send(self, to, MessageType.PASSWORD_RESET)


class PasswordChangedConfirmationEmail(djoser_email.PasswordChangedConfirmationEmail):
    def send(self, to, *args, **kwargs):
        _send(self, to, MessageType.PASSWORD_CHANGE)
