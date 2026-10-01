from contextvars import ContextVar

from django.dispatch import receiver
from django.utils import timezone
from django_tasks.signals import task_started, task_finished

current_task_id = ContextVar("email_task_id", default=None)


@receiver(task_started)
def track_task_start(sender, task_result, **kwargs):
    current_task_id.set(task_result.id)


@receiver(task_finished)
def track_task_finish(sender, task_result, **kwargs):
    current_task_id.set(None)


def send_tracked_email(message, kind):
    from core.models import EmailDelivery
    from django_tasks.backends.database.models import DBTaskResult

    task_id = current_task_id.get()
    # Chamadas diretas e outros backends não têm DBTaskResult associado.
    if task_id and not DBTaskResult.objects.filter(pk=task_id).exists():
        task_id = None
    delivery = EmailDelivery.objects.create(
        task_id=task_id, kind=kind, subject=message.subject,
        recipients=list(message.to), from_email=message.from_email,
        reply_to=list(message.reply_to), body=message.body,
    )
    try:
        if message.send(fail_silently=False) != 1:
            raise RuntimeError("O backend de email não confirmou o envio da mensagem.")
    except Exception as exc:
        delivery.status = "failed"
        delivery.error = f"{type(exc).__name__}: {exc}"
        delivery.finished_at = timezone.now()
        delivery.save(update_fields=["status", "error", "finished_at"])
        raise
    delivery.status = "sent"
    delivery.finished_at = timezone.now()
    delivery.save(update_fields=["status", "finished_at"])
    return {"historico_email_id": delivery.pk, "tipo": kind, "assunto": message.subject, "destinatarios": list(message.to), "status": "aceito_pelo_servidor", "finalizado_em": delivery.finished_at.isoformat()}
