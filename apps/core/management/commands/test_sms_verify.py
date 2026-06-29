from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Tests Twilio Verify SMS. "
        "Without --code: sends an OTP (and logs it if --email is given). "
        "With --code: verifies the OTP received."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--phone",
            type=str,
            required=True,
            help="Phone number in E.164 format (e.g. +521234567890).",
        )
        parser.add_argument(
            "--code",
            type=str,
            default=None,
            help="OTP code to verify. Omit to just send the code.",
        )
        parser.add_argument(
            "--email",
            type=str,
            default=None,
            help=(
                "User email to look up and log the SMS in the message bitácora. "
                "If omitted, the OTP is sent but not logged."
            ),
        )

    def handle(self, *args, **options):
        from twilio.base.exceptions import TwilioRestException

        phone = options["phone"]
        code = options.get("code")
        email = options.get("email")

        if not code:
            self._send(phone, email)
        else:
            self._verify(phone, code)

    def _send(self, phone, email):
        if email:
            from django.contrib.auth import get_user_model
            from apps.accounts.models import MessageType
            from apps.accounts.services import send_sms_otp
            from twilio.base.exceptions import TwilioRestException

            User = get_user_model()
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                raise CommandError(f"No se encontró un usuario con el correo '{email}'.")

            try:
                verification = send_sms_otp(user, MessageType.ACTIVATION, phone=phone)
                self.stdout.write(self.style.SUCCESS(
                    f"OTP enviado a {phone} — status: {verification.status}"
                ))
                self.stdout.write(self.style.SUCCESS(
                    "Mensaje registrado en bitácora."
                ))
            except TwilioRestException as e:
                raise CommandError(f"Error al enviar OTP: {e}")
        else:
            from django.conf import settings
            from twilio.rest import Client
            from twilio.base.exceptions import TwilioRestException

            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            try:
                verification = client.verify.v2.services(
                    settings.TWILIO_VERIFY_SERVICE_SID
                ).verifications.create(to=phone, channel="sms")
                self.stdout.write(self.style.SUCCESS(
                    f"OTP enviado a {phone} — status: {verification.status}"
                ))
                self.stdout.write(
                    "Pasa --email <correo> para registrar el envío en la bitácora."
                )
            except TwilioRestException as e:
                raise CommandError(f"Error al enviar OTP: {e}")

        self.stdout.write("Corre de nuevo con --code <código> para verificarlo.")

    def _verify(self, phone, code):
        from django.conf import settings
        from twilio.rest import Client
        from twilio.base.exceptions import TwilioRestException

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        try:
            check = client.verify.v2.services(
                settings.TWILIO_VERIFY_SERVICE_SID
            ).verification_checks.create(to=phone, code=code)

            if check.status == "approved":
                self.stdout.write(self.style.SUCCESS(
                    f"Código correcto — verificación aprobada para {phone}."
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"Código incorrecto o expirado — status: {check.status}"
                ))
        except TwilioRestException as e:
            raise CommandError(f"Error al verificar OTP: {e}")
