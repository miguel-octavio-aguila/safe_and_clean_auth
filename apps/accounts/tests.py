"""
Tests for the notification services (SMS + Email) and rate limiting.

Requirements:
    • Redis must be running (cache is used for rate limiting).
    • No real SMS or email is sent — Twilio and Resend are mocked.

Run inside the container:
    docker exec sc_auth python manage.py test apps.accounts --verbosity=2
"""

from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings

from apps.accounts.emails import _log as email_log
from apps.accounts.models import (
    AdminMessages,
    ClientMessages,
    EmployeeMessages,
    MessageChannel,
    MessageStatus,
    MessageType,
    Role,
)
from apps.accounts.services import (
    send_activation_otp,
    send_confirmation_sms,
    send_password_changed_sms,
    send_password_reset_confirm_sms,
    send_password_reset_otp,
    verify_sms_otp,
)
from apps.core.rate_limiting import RateLimitExceeded, enforce_rate_limit

User = get_user_model()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SMALL_LIMITS = {
    'SMS_RATE_LIMITS': {
        'per_user': {'1h': 2, '6h': 5, '1d': 10},
        'global':   {'1h': 5, '6h': 10, '1d': 20},
    },
    'EMAIL_RATE_LIMITS': {
        'per_user': {'1h': 2, '6h': 5, '1d': 10},
        'global':   {'1h': 5, '6h': 10, '1d': 20},
    },
}


def _make_employee(n=1):
    return User.objects.create_user(
        email=f'empleado{n}@test.internal',
        password='testpass123',
        first_name='Juan',
        last_name='Pérez',
        phone_number=f'+5212345{n:05d}',
        role=Role.EMPLOYEE,
        is_active=True,
    )


def _make_admin(n=1):
    return User.objects.create_user(
        email=f'admin{n}@test.internal',
        password='testpass123',
        first_name='Admin',
        last_name='Uno',
        role=Role.ADMIN,
        is_active=True,
    )


def _make_client(n=1):
    return User.objects.create_user(
        email=f'cliente{n}@test.internal',
        password='testpass123',
        first_name='Cliente',
        last_name='Uno',
        role=Role.CLIENT,
        is_active=True,
    )


def _mock_twilio():
    """Returns a (mock_client, mock_verification) pair for Twilio Verify flows."""
    mock_verification = MagicMock()
    mock_verification.status = 'pending'
    mock_client = MagicMock()
    (mock_client.verify.v2
        .services.return_value
        .verifications.create
        .return_value) = mock_verification
    return mock_client, mock_verification


def _mock_twilio_message():
    """Returns a (mock_client, mock_message) pair for Twilio Messages flows."""
    mock_message = MagicMock()
    mock_message.sid = 'SMtest1234'
    mock_client = MagicMock()
    mock_client.messages.create.return_value = mock_message
    return mock_client, mock_message


# ===========================================================================
# Model save() auto-fill
# ===========================================================================

class MessageModelSaveTest(TestCase):
    """Verifies that save() auto-fills name and phone_number from the FK."""

    def setUp(self):
        cache.clear()
        self.employee = _make_employee()
        self.admin    = _make_admin()
        self.client   = _make_client()

    def test_employee_message_autofill(self):
        log = EmployeeMessages.objects.create(
            employee=self.employee,
            messageType=MessageType.ACTIVATION,
            channel=MessageChannel.SMS,
            status=MessageStatus.SUCCESS,
            message='OTP enviado',
        )
        self.assertEqual(log.employee_name, self.employee.get_full_name())
        self.assertEqual(log.phone_number, self.employee.phone_number)

    def test_admin_message_autofill(self):
        log = AdminMessages.objects.create(
            admin=self.admin,
            messageType=MessageType.ACTIVATION,
            channel=MessageChannel.EMAIL,
            status=MessageStatus.SUCCESS,
            message='Correo enviado',
        )
        self.assertEqual(log.admin_name, self.admin.get_full_name())

    def test_client_message_autofill(self):
        log = ClientMessages.objects.create(
            client=self.client,
            messageType=MessageType.PASSWORD_RESET,
            channel=MessageChannel.EMAIL,
            status=MessageStatus.SUCCESS,
            message='Correo enviado',
        )
        self.assertEqual(log.client_name, self.client.get_full_name())

    def test_failed_message_stores_error(self):
        log = EmployeeMessages.objects.create(
            employee=self.employee,
            messageType=MessageType.ACTIVATION,
            channel=MessageChannel.SMS,
            status=MessageStatus.FAILED,
            message='Error al enviar OTP',
            error_message='Twilio 400: Invalid phone number',
        )
        self.assertEqual(log.status, MessageStatus.FAILED)
        self.assertIn('Twilio', log.error_message)

    def test_status_defaults_to_success(self):
        log = EmployeeMessages.objects.create(
            employee=self.employee,
            messageType=MessageType.CONFIRMATION,
            channel=MessageChannel.SMS,
            message='Cuenta activada',
        )
        self.assertEqual(log.status, MessageStatus.SUCCESS)
        self.assertEqual(log.error_message, '')


# ===========================================================================
# Rate limiter
# ===========================================================================

@override_settings(**SMALL_LIMITS)
class RateLimiterTest(TestCase):
    """
    Tests for apps.core.rate_limiting.enforce_rate_limit.
    Uses real Redis — cache is cleared in setUp.
    """

    def setUp(self):
        cache.clear()
        self.user = _make_employee()

    def test_first_call_allowed(self):
        # Should not raise
        enforce_rate_limit('sms', self.user.id)

    def test_per_user_limit_blocks_after_threshold(self):
        # per_user 1h = 2
        enforce_rate_limit('sms', self.user.id)
        enforce_rate_limit('sms', self.user.id)
        with self.assertRaises(RateLimitExceeded) as ctx:
            enforce_rate_limit('sms', self.user.id)
        self.assertEqual(ctx.exception.scope, 'per_user')

    def test_global_limit_blocks_after_threshold(self):
        # global 1h = 5 — use 5 different users to avoid per_user limit (2)
        for i in range(2, 7):  # users 2..6 → 5 distinct users × 1 call = 5 global uses
            user = _make_employee(n=i)
            enforce_rate_limit('sms', user.id)
        new_user = _make_employee(n=99)
        with self.assertRaises(RateLimitExceeded) as ctx:
            enforce_rate_limit('sms', new_user.id)
        self.assertEqual(ctx.exception.scope, 'global')

    def test_different_services_have_separate_limits(self):
        # Exhaust SMS limit for user
        enforce_rate_limit('sms', self.user.id)
        enforce_rate_limit('sms', self.user.id)
        with self.assertRaises(RateLimitExceeded):
            enforce_rate_limit('sms', self.user.id)
        # Email limit is untouched for same user
        enforce_rate_limit('email', self.user.id)  # should not raise

    def test_exception_carries_window_and_limit(self):
        enforce_rate_limit('sms', self.user.id)
        enforce_rate_limit('sms', self.user.id)
        with self.assertRaises(RateLimitExceeded) as ctx:
            enforce_rate_limit('sms', self.user.id)
        exc = ctx.exception
        self.assertEqual(exc.window, '1h')
        self.assertEqual(exc.limit, 2)

    def test_counters_not_incremented_when_blocked(self):
        # Exhaust the limit
        enforce_rate_limit('sms', self.user.id)
        enforce_rate_limit('sms', self.user.id)
        # 3rd and 4th calls should both raise (counter stays at 2, not growing)
        with self.assertRaises(RateLimitExceeded):
            enforce_rate_limit('sms', self.user.id)
        with self.assertRaises(RateLimitExceeded):
            enforce_rate_limit('sms', self.user.id)


# ===========================================================================
# SMS — OTP flows (send_activation_otp, send_password_reset_otp)
# ===========================================================================

@override_settings(**SMALL_LIMITS)
class SMSOTPTest(TestCase):

    def setUp(self):
        cache.clear()
        self.employee = _make_employee()

    # --- send_activation_otp ---

    @patch('apps.accounts.services._twilio_client')
    def test_activation_otp_success_creates_log(self, mock_get_client):
        mock_client, _ = _mock_twilio()
        mock_get_client.return_value = mock_client

        send_activation_otp(self.employee)

        self.assertEqual(EmployeeMessages.objects.count(), 1)
        log = EmployeeMessages.objects.first()
        self.assertEqual(log.messageType, MessageType.ACTIVATION)
        self.assertEqual(log.channel, MessageChannel.SMS)
        self.assertEqual(log.status, MessageStatus.SUCCESS)
        self.assertIn(self.employee.phone_number, log.message)
        self.assertEqual(log.error_message, '')
        self.assertEqual(log.employee_name, self.employee.get_full_name())

    @patch('apps.accounts.services._twilio_client')
    def test_activation_otp_uses_custom_phone(self, mock_get_client):
        mock_client, _ = _mock_twilio()
        mock_get_client.return_value = mock_client
        custom_phone = '+521112223333'

        send_activation_otp(self.employee, phone=custom_phone)

        mock_client.verify.v2.services.return_value.verifications.create.assert_called_once_with(
            to=custom_phone, channel='sms'
        )

    @patch('apps.accounts.services._twilio_client')
    def test_activation_otp_twilio_error_creates_failed_log(self, mock_get_client):
        from twilio.base.exceptions import TwilioRestException
        mock_client = MagicMock()
        mock_client.verify.v2.services.return_value.verifications.create.side_effect = (
            TwilioRestException(status=400, uri='/v2/Services/VAxxx/Verifications')
        )
        mock_get_client.return_value = mock_client

        with self.assertRaises(TwilioRestException):
            send_activation_otp(self.employee)

        self.assertEqual(EmployeeMessages.objects.count(), 1)
        log = EmployeeMessages.objects.first()
        self.assertEqual(log.status, MessageStatus.FAILED)
        self.assertNotEqual(log.error_message, '')

    @patch('apps.accounts.services._twilio_client')
    def test_activation_otp_rate_limit_creates_failed_log(self, mock_get_client):
        mock_client, _ = _mock_twilio()
        mock_get_client.return_value = mock_client

        send_activation_otp(self.employee)
        send_activation_otp(self.employee)

        with self.assertRaises(RateLimitExceeded):
            send_activation_otp(self.employee)

        logs = EmployeeMessages.objects.all()
        self.assertEqual(logs.count(), 3)
        failed = logs.filter(status=MessageStatus.FAILED)
        self.assertEqual(failed.count(), 1)
        self.assertIn('bloqueado', failed.first().message)

    # --- send_password_reset_otp ---

    @patch('apps.accounts.services._twilio_client')
    def test_password_reset_otp_success_creates_log(self, mock_get_client):
        mock_client, _ = _mock_twilio()
        mock_get_client.return_value = mock_client

        send_password_reset_otp(self.employee)

        log = EmployeeMessages.objects.first()
        self.assertEqual(log.messageType, MessageType.PASSWORD_RESET)
        self.assertEqual(log.status, MessageStatus.SUCCESS)

    @patch('apps.accounts.services._twilio_client')
    def test_password_reset_otp_twilio_error_creates_failed_log(self, mock_get_client):
        from twilio.base.exceptions import TwilioRestException
        mock_client = MagicMock()
        mock_client.verify.v2.services.return_value.verifications.create.side_effect = (
            TwilioRestException(status=400, uri='/v2/Services/VAxxx/Verifications')
        )
        mock_get_client.return_value = mock_client

        with self.assertRaises(TwilioRestException):
            send_password_reset_otp(self.employee)

        log = EmployeeMessages.objects.first()
        self.assertEqual(log.messageType, MessageType.PASSWORD_RESET)
        self.assertEqual(log.status, MessageStatus.FAILED)


# ===========================================================================
# SMS — Notification flows (uses Twilio Messages API with templates)
# ===========================================================================

@override_settings(**SMALL_LIMITS)
class SMSNotificationTest(TestCase):

    def setUp(self):
        cache.clear()
        self.employee = _make_employee()

    def _setup_messages_mock(self, mock_get_client):
        mock_client, mock_msg = _mock_twilio_message()
        mock_get_client.return_value = mock_client
        return mock_client, mock_msg

    # --- send_confirmation_sms ---

    @patch('apps.accounts.services._twilio_client')
    def test_confirmation_sms_success_creates_log(self, mock_get_client):
        mock_client, _ = self._setup_messages_mock(mock_get_client)

        send_confirmation_sms(self.employee)

        log = EmployeeMessages.objects.first()
        self.assertEqual(log.messageType, MessageType.CONFIRMATION)
        self.assertEqual(log.channel, MessageChannel.SMS)
        self.assertEqual(log.status, MessageStatus.SUCCESS)
        self.assertIn(self.employee.first_name, log.message)
        self.assertEqual(log.error_message, '')

    @patch('apps.accounts.services._twilio_client')
    def test_confirmation_sms_calls_twilio_messages_api(self, mock_get_client):
        from django.conf import settings
        mock_client, _ = self._setup_messages_mock(mock_get_client)

        send_confirmation_sms(self.employee)

        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args.kwargs
        self.assertEqual(call_kwargs['to'], self.employee.phone_number)
        self.assertEqual(call_kwargs['from_'], settings.TWILIO_FROM_NUMBER)
        self.assertIn(self.employee.first_name, call_kwargs['body'])

    @patch('apps.accounts.services._twilio_client')
    def test_confirmation_sms_twilio_error_creates_failed_log(self, mock_get_client):
        from twilio.base.exceptions import TwilioRestException
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = (
            TwilioRestException(status=400, uri='/2010-04-01/Accounts/ACxxx/Messages')
        )
        mock_get_client.return_value = mock_client

        with self.assertRaises(TwilioRestException):
            send_confirmation_sms(self.employee)

        log = EmployeeMessages.objects.first()
        self.assertEqual(log.messageType, MessageType.CONFIRMATION)
        self.assertEqual(log.status, MessageStatus.FAILED)
        self.assertNotEqual(log.error_message, '')

    # --- send_password_changed_sms ---

    @patch('apps.accounts.services._twilio_client')
    def test_password_changed_sms_success_creates_log(self, mock_get_client):
        mock_client, _ = self._setup_messages_mock(mock_get_client)

        send_password_changed_sms(self.employee)

        log = EmployeeMessages.objects.first()
        self.assertEqual(log.messageType, MessageType.PASSWORD_CHANGE)
        self.assertEqual(log.status, MessageStatus.SUCCESS)
        self.assertIn(self.employee.first_name, log.message)

    @patch('apps.accounts.services._twilio_client')
    def test_password_changed_sms_rate_limit_creates_failed_log(self, mock_get_client):
        mock_client, _ = self._setup_messages_mock(mock_get_client)

        send_password_changed_sms(self.employee)
        send_password_changed_sms(self.employee)

        with self.assertRaises(RateLimitExceeded):
            send_password_changed_sms(self.employee)

        self.assertEqual(
            EmployeeMessages.objects.filter(status=MessageStatus.FAILED).count(), 1
        )

    # --- send_password_reset_confirm_sms ---

    @patch('apps.accounts.services._twilio_client')
    def test_password_reset_confirm_sms_success_creates_log(self, mock_get_client):
        mock_client, _ = self._setup_messages_mock(mock_get_client)

        send_password_reset_confirm_sms(self.employee)

        log = EmployeeMessages.objects.first()
        self.assertEqual(log.messageType, MessageType.PASSWORD_RESET_CONFIRM)
        self.assertEqual(log.status, MessageStatus.SUCCESS)
        self.assertIn(self.employee.first_name, log.message)


# ===========================================================================
# SMS — OTP verification (verify_sms_otp)
# ===========================================================================

class SMSVerifyOTPTest(TestCase):

    def setUp(self):
        cache.clear()
        self.employee = _make_employee()

    @patch('apps.accounts.services._twilio_client')
    def test_verify_approved_returns_true(self, mock_get_client):
        mock_check = MagicMock()
        mock_check.status = 'approved'
        mock_client = MagicMock()
        mock_client.verify.v2.services.return_value.verification_checks.create.return_value = mock_check
        mock_get_client.return_value = mock_client

        result = verify_sms_otp(self.employee, code='123456')

        self.assertTrue(result)
        # verify_sms_otp does NOT create a log entry
        self.assertEqual(EmployeeMessages.objects.count(), 0)

    @patch('apps.accounts.services._twilio_client')
    def test_verify_wrong_code_returns_false(self, mock_get_client):
        mock_check = MagicMock()
        mock_check.status = 'pending'
        mock_client = MagicMock()
        mock_client.verify.v2.services.return_value.verification_checks.create.return_value = mock_check
        mock_get_client.return_value = mock_client

        result = verify_sms_otp(self.employee, code='000000')

        self.assertFalse(result)

    @patch('apps.accounts.services._twilio_client')
    def test_verify_twilio_error_raises(self, mock_get_client):
        from twilio.base.exceptions import TwilioRestException
        mock_client = MagicMock()
        mock_client.verify.v2.services.return_value.verification_checks.create.side_effect = (
            TwilioRestException(status=404, uri='/v2/Services/VAxxx/VerificationChecks')
        )
        mock_get_client.return_value = mock_client

        with self.assertRaises(TwilioRestException):
            verify_sms_otp(self.employee, code='123456')

    @patch('apps.accounts.services._twilio_client')
    def test_verify_uses_custom_phone(self, mock_get_client):
        mock_check = MagicMock()
        mock_check.status = 'approved'
        mock_client = MagicMock()
        mock_client.verify.v2.services.return_value.verification_checks.create.return_value = mock_check
        mock_get_client.return_value = mock_client
        custom_phone = '+521119998888'

        verify_sms_otp(self.employee, code='123456', phone=custom_phone)

        mock_client.verify.v2.services.return_value.verification_checks.create.assert_called_once_with(
            to=custom_phone, code='123456'
        )


# ===========================================================================
# Email — _log() function and Djoser class integration
# ===========================================================================

@override_settings(**SMALL_LIMITS)
class EmailLogFunctionTest(TestCase):
    """Tests the _log() helper in emails.py directly."""

    def setUp(self):
        cache.clear()
        self.admin  = _make_admin()
        self.client = _make_client()
        self.employee = _make_employee()

    def test_log_admin_success_creates_admin_message(self):
        email_log(self.admin, MessageType.ACTIVATION, 'admin@test.internal', MessageStatus.SUCCESS)

        self.assertEqual(AdminMessages.objects.count(), 1)
        log = AdminMessages.objects.first()
        self.assertEqual(log.admin, self.admin)
        self.assertEqual(log.messageType, MessageType.ACTIVATION)
        self.assertEqual(log.channel, MessageChannel.EMAIL)
        self.assertEqual(log.status, MessageStatus.SUCCESS)
        self.assertEqual(log.error_message, '')
        self.assertEqual(log.admin_name, self.admin.get_full_name())

    def test_log_client_success_creates_client_message(self):
        email_log(self.client, MessageType.PASSWORD_RESET, 'cliente@test.internal', MessageStatus.SUCCESS)

        self.assertEqual(ClientMessages.objects.count(), 1)
        log = ClientMessages.objects.first()
        self.assertEqual(log.client, self.client)
        self.assertEqual(log.messageType, MessageType.PASSWORD_RESET)
        self.assertEqual(log.status, MessageStatus.SUCCESS)

    def test_log_failed_stores_error_message(self):
        email_log(self.admin, MessageType.CONFIRMATION, 'admin@test.internal',
                    MessageStatus.FAILED, 'Resend API error 500')

        log = AdminMessages.objects.first()
        self.assertEqual(log.status, MessageStatus.FAILED)
        self.assertEqual(log.error_message, 'Resend API error 500')
        self.assertIn('error', log.message.lower())

    def test_log_employee_does_not_create_any_record(self):
        email_log(self.employee, MessageType.ACTIVATION, 'emp@test.internal', MessageStatus.SUCCESS)

        self.assertEqual(AdminMessages.objects.count(), 0)
        self.assertEqual(ClientMessages.objects.count(), 0)
        self.assertEqual(EmployeeMessages.objects.count(), 0)

    def test_log_all_message_types_for_admin(self):
        types = [
            MessageType.ACTIVATION,
            MessageType.CONFIRMATION,
            MessageType.PASSWORD_RESET,
            MessageType.PASSWORD_CHANGE,
        ]
        for msg_type in types:
            email_log(self.admin, msg_type, 'admin@test.internal', MessageStatus.SUCCESS)

        self.assertEqual(AdminMessages.objects.count(), len(types))


@override_settings(**SMALL_LIMITS)
class EmailClassIntegrationTest(TestCase):
    """
    Tests that the Djoser email subclasses (ActivationEmail, etc.) correctly
    log to the DB on success, failure, and rate limit.

    Patches djoser.email.ActivationEmail.send (and siblings) so that no actual
    email is sent and no template rendering occurs.
    """

    def setUp(self):
        cache.clear()
        self.admin  = _make_admin()
        self.client = _make_client()

    def _make_email_instance(self, cls, user):
        """Creates a bare email class instance with only the context needed."""
        instance = cls.__new__(cls)
        instance.context = {'user': user}
        return instance

    # --- ActivationEmail ---

    @patch('djoser.email.ActivationEmail.send')
    def test_activation_email_success_logs_admin(self, _mock_send):
        from apps.accounts.emails import ActivationEmail
        instance = self._make_email_instance(ActivationEmail, self.admin)

        ActivationEmail.send(instance, [self.admin.email])

        self.assertEqual(AdminMessages.objects.count(), 1)
        log = AdminMessages.objects.first()
        self.assertEqual(log.messageType, MessageType.ACTIVATION)
        self.assertEqual(log.channel, MessageChannel.EMAIL)
        self.assertEqual(log.status, MessageStatus.SUCCESS)

    @patch('djoser.email.ActivationEmail.send')
    def test_activation_email_success_logs_client(self, _mock_send):
        from apps.accounts.emails import ActivationEmail
        instance = self._make_email_instance(ActivationEmail, self.client)

        ActivationEmail.send(instance, [self.client.email])

        self.assertEqual(ClientMessages.objects.count(), 1)
        log = ClientMessages.objects.first()
        self.assertEqual(log.messageType, MessageType.ACTIVATION)
        self.assertEqual(log.status, MessageStatus.SUCCESS)

    @patch('djoser.email.ActivationEmail.send', side_effect=Exception('SMTP error'))
    def test_activation_email_error_logs_failure(self, _mock_send):
        from apps.accounts.emails import ActivationEmail
        instance = self._make_email_instance(ActivationEmail, self.admin)

        with self.assertRaises(Exception):
            ActivationEmail.send(instance, [self.admin.email])

        log = AdminMessages.objects.first()
        self.assertIsNotNone(log)
        self.assertEqual(log.status, MessageStatus.FAILED)
        self.assertIn('SMTP error', log.error_message)

    @patch('djoser.email.ActivationEmail.send')
    def test_activation_email_rate_limit_logs_failure_and_raises_throttled(self, _mock_send):
        from rest_framework.exceptions import Throttled
        from apps.accounts.emails import ActivationEmail

        instance = self._make_email_instance(ActivationEmail, self.admin)
        ActivationEmail.send(instance, [self.admin.email])
        ActivationEmail.send(instance, [self.admin.email])

        with self.assertRaises(Throttled):
            ActivationEmail.send(instance, [self.admin.email])

        failed_logs = AdminMessages.objects.filter(status=MessageStatus.FAILED)
        self.assertEqual(failed_logs.count(), 1)
        self.assertIn('Límite', failed_logs.first().error_message)

    # --- Other email types ---

    @patch('djoser.email.ConfirmationEmail.send')
    def test_confirmation_email_logs_correctly(self, _mock_send):
        from apps.accounts.emails import ConfirmationEmail
        instance = self._make_email_instance(ConfirmationEmail, self.admin)

        ConfirmationEmail.send(instance, [self.admin.email])

        log = AdminMessages.objects.first()
        self.assertEqual(log.messageType, MessageType.CONFIRMATION)
        self.assertEqual(log.status, MessageStatus.SUCCESS)

    @patch('djoser.email.PasswordResetEmail.send')
    def test_password_reset_email_logs_correctly(self, _mock_send):
        from apps.accounts.emails import PasswordResetEmail
        instance = self._make_email_instance(PasswordResetEmail, self.client)

        PasswordResetEmail.send(instance, [self.client.email])

        log = ClientMessages.objects.first()
        self.assertEqual(log.messageType, MessageType.PASSWORD_RESET)
        self.assertEqual(log.status, MessageStatus.SUCCESS)

    @patch('djoser.email.PasswordChangedConfirmationEmail.send')
    def test_password_changed_email_logs_correctly(self, _mock_send):
        from apps.accounts.emails import PasswordChangedConfirmationEmail
        instance = self._make_email_instance(PasswordChangedConfirmationEmail, self.admin)

        PasswordChangedConfirmationEmail.send(instance, [self.admin.email])

        log = AdminMessages.objects.first()
        self.assertEqual(log.messageType, MessageType.PASSWORD_CHANGE)
        self.assertEqual(log.status, MessageStatus.SUCCESS)
