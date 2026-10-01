from django.contrib import admin
from django.utils.html import format_html
from django_tasks.backends.database.admin import DBTaskResultAdmin
from django_tasks.backends.database.models import DBTaskResult

from core.models import EmailDelivery, Registration


class EmailDeliveryInline(admin.StackedInline):
    model = EmailDelivery
    extra = 0
    can_delete = False
    readonly_fields = ("kind", "status", "subject", "recipients", "from_email", "reply_to", "body", "error", "created_at", "finished_at")
    fields = readonly_fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(EmailDelivery)
class EmailDeliveryAdmin(admin.ModelAdmin):
    list_display = ("created_at", "kind", "subject", "recipients", "status", "task")
    list_filter = ("kind", "status")
    search_fields = ("subject", "body", "from_email", "recipients", "reply_to")
    readonly_fields = tuple(field.name for field in EmailDelivery._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class DetailedTaskResultAdmin(DBTaskResultAdmin):
    list_display = ("id", "task_name", "email_summary", "status", "enqueued_at", "finished_at")
    search_fields = ("id", "task_path", "args_kwargs", "email_deliveries__subject", "email_deliveries__body", "email_deliveries__recipients")
    inlines = (EmailDeliveryInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("email_deliveries")

    def get_readonly_fields(self, request, obj=None):
        return ["email_summary", "submitted_contact", *super().get_readonly_fields(request, obj)]

    @admin.display(description="Email / destinatário")
    def email_summary(self, obj):
        delivery = next(iter(obj.email_deliveries.all()), None)
        if delivery:
            return f"{delivery.kind}: {delivery.subject} → {', '.join(delivery.recipients)}"
        args = obj.args_kwargs.get("args", [])
        kwargs = obj.args_kwargs.get("kwargs", {})
        if obj.task_path == "core.tasks.send_registration_email":
            pk = args[0] if args else kwargs.get("registration_id")
            person = Registration.objects.filter(pk=pk).first()
            return f"Inscrição: {person.email}" if person else "Inscrição não encontrada"
        if obj.task_path == "core.tasks.send_email":
            return f"Contato: {args[0] if args else kwargs.get('subject', '')}"
        return "—"

    @admin.display(description="Mensagem recebida pelo formulário")
    def submitted_contact(self, obj):
        if obj.task_path != "core.tasks.send_email":
            return "—"
        values = dict(zip(("subject", "message", "sender_name", "sender_email", "to"), obj.args_kwargs.get("args", [])))
        values.update(obj.args_kwargs.get("kwargs", {}))
        return format_html('<div style="white-space:pre-wrap">De: {} &lt;{}&gt;\nAssunto: {}\n\n{}</div>', values.get("sender_name", ""), values.get("sender_email", ""), values.get("subject", ""), values.get("message", ""))


admin.site.unregister(DBTaskResult)
admin.site.register(DBTaskResult, DetailedTaskResultAdmin)
