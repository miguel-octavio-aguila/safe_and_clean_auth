import resend
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail import EmailMessage


class ResendEmailBackend(BaseEmailBackend):
    def open(self):
        resend.api_key = settings.RESEND_API_KEY
        return True

    def close(self):
        pass

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        resend.api_key = settings.RESEND_API_KEY
        sent = 0

        for message in email_messages:
            try:
                params = {
                    "from": message.from_email or settings.DEFAULT_FROM_EMAIL,
                    "to": message.to,
                    "subject": message.subject,
                }

                html_body = None
                text_body = message.body

                for content, mimetype in getattr(message, "alternatives", []):
                    if mimetype == "text/html":
                        html_body = content
                        break

                if html_body:
                    params["html"] = html_body
                    if text_body:
                        params["text"] = text_body
                else:
                    params["text"] = text_body

                if message.cc:
                    params["cc"] = message.cc
                if message.bcc:
                    params["bcc"] = message.bcc
                if message.reply_to:
                    params["reply_to"] = list(message.reply_to)

                resend.Emails.send(params)
                sent += 1
            except Exception as e:
                if not self.fail_silently:
                    raise
        return sent
