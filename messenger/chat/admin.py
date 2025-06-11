from django.contrib import admin
from .models import Ban

@admin.register(Ban)
class BanAdmin(admin.ModelAdmin):
    list_display = ('user', 'reason', 'banned_by', 'banned_at', 'expires_at', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('user__username', 'reason')
    actions = ['lift_ban']

    def lift_ban(self, request, queryset):
        queryset.update(is_active=False)
    lift_ban.short_description = "Снять выбранные баны"