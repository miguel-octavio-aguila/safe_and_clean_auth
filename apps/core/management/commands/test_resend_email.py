from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Sends a test email via Resend to verify the email backend is working."

    def add_arguments(self, parser):
        parser.add_argument(
            "--to",
            type=str,
            required=True,
            help="Recipient email address.",
        )

    def handle(self, *args, **options):
        from django.conf import settings
        from django.core.mail import send_mail

        recipient = options["to"]

        send_mail(
            subject="[TEST] Safe & Clean Querétaro — Resend email backend",
            message="Este es un correo de prueba enviado desde el backend de autenticación usando Resend.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            html_message=(
                "<h2>Prueba de correo — Safe &amp; Clean Querétaro</h2>"
                "<p>Este correo confirma que el backend de Resend está correctamente configurado.</p>"
                "<p><em>Si lo ves, todo funciona.</em></p>"
            ),
            fail_silently=False,
        )

        self.stdout.write(self.style.SUCCESS(f"Email de prueba enviado a {recipient}"))
