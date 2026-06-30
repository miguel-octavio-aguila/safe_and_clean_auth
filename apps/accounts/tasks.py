import logging

from celery import shared_task
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger(__name__)

_DAYS_WARNING = 7


def _get_admin_emails():
    from .models import CustomUser, Role
    return list(
        CustomUser.objects.filter(role=Role.ADMIN, email__isnull=False, is_active=True)
        .values_list('email', flat=True)
    )


def _send_contract_email(subject, template_name, context, admin_email, profile):
    """Render and send one contract notification email; log result to AdminMessages."""
    from .models import AdminMessages, MessageChannel, MessageStatus, MessageType

    html_body = render_to_string(f'email/auth/{template_name}', context)
    text_body = (
        f"{subject}\n\n"
        f"Usuario: {profile.user.get_full_name()}\n"
        f"Fin del contrato: {profile.contract_end}\n"
    )

    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[admin_email],
    )
    msg.attach_alternative(html_body, 'text/html')

    msg_type = (
        MessageType.CONTRACT_EXPIRING
        if 'expiring' in template_name
        else MessageType.CONTRACT_EXPIRED
    )

    try:
        msg.send()
        AdminMessages.objects.create(
            messageType=msg_type,
            channel=MessageChannel.EMAIL,
            status=MessageStatus.SUCCESS,
            message=f"Aviso de contrato enviado a {admin_email} para {profile.user.get_full_name()}",
        )
    except Exception as exc:
        AdminMessages.objects.create(
            messageType=msg_type,
            channel=MessageChannel.EMAIL,
            status=MessageStatus.FAILED,
            message=f"Error al enviar aviso de contrato a {admin_email} para {profile.user.get_full_name()}",
            error_message=str(exc),
        )
        logger.exception(
            "Error al enviar correo de contrato a %s para usuario %s",
            admin_email,
            profile.user_id,
        )


@shared_task
def notify_contracts_expiring_soon():
    """
    Notifies all active admin users of contracts expiring in exactly DAYS_WARNING days.
    Runs daily via Celery Beat.
    """
    from .models import UserProfile

    target_date = timezone.localdate() + timezone.timedelta(days=_DAYS_WARNING)
    expiring = UserProfile.objects.filter(contract_end=target_date).select_related('user')

    if not expiring.exists():
        logger.info("notify_contracts_expiring_soon: no contracts expire on %s", target_date)
        return

    admin_emails = _get_admin_emails()
    if not admin_emails:
        logger.warning("notify_contracts_expiring_soon: no admin emails found, skipping")
        return

    count = 0
    for profile in expiring:
        context = {
            'user': profile.user,
            'profile': profile,
            'contract_end': profile.contract_end,
            'days_remaining': _DAYS_WARNING,
            'site_name': settings.SITE_NAME,
        }
        subject = f"[{settings.SITE_NAME}] Contrato próximo a expirar — {profile.user.get_full_name()}"
        for email in admin_emails:
            _send_contract_email(subject, 'contract_expiring_soon.html', context, email, profile)
        count += 1

    logger.info(
        "notify_contracts_expiring_soon: processed %d contract(s) expiring on %s",
        count,
        target_date,
    )


@shared_task
def notify_contracts_expired():
    """
    Notifies all active admin users of contracts that expire today.
    Runs daily via Celery Beat.
    """
    from .models import UserProfile

    today = timezone.localdate()
    expired = UserProfile.objects.filter(contract_end=today).select_related('user')

    if not expired.exists():
        logger.info("notify_contracts_expired: no contracts expire today (%s)", today)
        return

    admin_emails = _get_admin_emails()
    if not admin_emails:
        logger.warning("notify_contracts_expired: no admin emails found, skipping")
        return

    count = 0
    for profile in expired:
        context = {
            'user': profile.user,
            'profile': profile,
            'contract_end': profile.contract_end,
            'site_name': settings.SITE_NAME,
        }
        subject = f"[{settings.SITE_NAME}] Contrato expirado — {profile.user.get_full_name()}"
        for email in admin_emails:
            _send_contract_email(subject, 'contract_expired.html', context, email, profile)
        count += 1

    logger.info(
        "notify_contracts_expired: processed %d contract(s) expired on %s",
        count,
        today,
    )
