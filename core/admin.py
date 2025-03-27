from django.contrib import admin

from core.models import Registration


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    list_display = ("full_name", "created_at")
    list_filter = ("activity", "workshop")
