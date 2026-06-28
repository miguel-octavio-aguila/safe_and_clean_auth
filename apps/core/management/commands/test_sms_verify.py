from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Tests Twilio Verify SMS. "
        "Without --code: sends an OTP to the given phone number. "
        "With --code: verifies the OTP entered."
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

    def handle(self, *args, **options):
        from django.conf import settings
        from twilio.rest import Client
        from twilio.base.exceptions import TwilioRestException

        phone = options["phone"]
        code = options.get("code")

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        service_sid = settings.TWILIO_VERIFY_SERVICE_SID

        if not code:
            try:
                verification = client.verify.v2.services(service_sid).verifications.create(
                    to=phone,
                    channel="sms",
                )
                self.stdout.write(self.style.SUCCESS(
                    f"OTP enviado a {phone} — status: {verification.status}"
                ))
                self.stdout.write("Corre de nuevo con --code <código> para verificarlo.")
            except TwilioRestException as e:
                raise CommandError(f"Error al enviar OTP: {e}")
        else:
            try:
                check = client.verify.v2.services(service_sid).verification_checks.create(
                    to=phone,
                    code=code,
                )
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
