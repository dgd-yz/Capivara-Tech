from django.contrib import admin
from solo.admin import SingletonModelAdmin

from .models import CourseSettings, Highlight, Subject, Topic


@admin.register(CourseSettings)
class CourseSettingsAdmin(SingletonModelAdmin):
    fieldsets = (
        ("Identificação", {"fields": ("name", "short_name", "degree", "diploma", "tagline", "institution", "logo")}),
        ("Textos", {"fields": ("intro", "about", "graduate_profile", "careers")}),
        ("Dados do curso", {
            "description": "Itens vazios ficam escondidos no site.",
            "fields": ("duration", "shift", "seats", "workload"),
        }),
        ("Ingresso", {"fields": ("admission", "admission_url")}),
        ("Matriz", {"fields": ("electives", "ppc")}),
        ("Contato", {"fields": ("coordinator", "contact_email", "instagram_url", "address", "map_url")}),
    )


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "published")
    list_editable = ("order", "published")


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "module", "workload", "order")
    list_editable = ("module", "workload", "order")
    list_filter = ("module",)
    search_fields = ("name",)



@admin.register(Highlight)
class HighlightAdmin(admin.ModelAdmin):
    list_display = ("title", "date", "published")
    list_editable = ("published",)
    date_hierarchy = "date"
