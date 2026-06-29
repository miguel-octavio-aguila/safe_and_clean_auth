from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html

from .models import (
    AdminMessages,
    ClientMessages,
    CustomUser,
    EmployeeMessages,
    MessageChannel,
    MessageStatus,
    UserProfile,
)


# ---------------------------------------------------------------------------
# Badge helpers
# ---------------------------------------------------------------------------

def _status_badge(obj):
    color = '#27ae60' if obj.status == MessageStatus.SUCCESS else '#e74c3c'
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 10px;'
        'border-radius:4px;font-size:0.82em;font-weight:600">{}</span>',
        color,
        obj.get_status_display(),
    )


def _channel_badge(obj):
    color = '#2980b9' if obj.channel == MessageChannel.EMAIL else '#8e44ad'
    return format_html(
        '<span style="background:{};color:#fff;padding:2px 10px;'
        'border-radius:4px;font-size:0.82em;font-weight:600">{}</span>',
        color,
        obj.get_channel_display(),
    )


# ---------------------------------------------------------------------------
# CustomUser + UserProfile inline
# ---------------------------------------------------------------------------

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    extra = 0
    readonly_fields = ('id', 'created_at', 'updated_at')
    fields = ('profile_picture',)
    verbose_name = 'Foto de perfil'


class CustomUserAdmin(UserAdmin):
    inlines = [UserProfileInline]

    list_display = (
        'username',
        'email',
        'first_name',
        'last_name',
        'role',
        'phone_number',
        'is_active',
        'is_staff',
    )
    list_filter = ('role', 'is_active', 'is_staff', 'is_superuser', 'created_at')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'role')
    ordering = ('email',)
    readonly_fields = ('id', 'created_at', 'updated_at', 'last_login')
    save_on_top = True

    fieldsets = (
        ('Cuenta', {
            'fields': ('id', 'email', 'phone_number', 'role', 'username', 'password')
        }),
        ('Información personal', {
            'fields': ('first_name', 'last_name')
        }),
        ('Permisos', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Fechas', {
            'fields': ('last_login', 'created_at', 'updated_at')
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email',
                'phone_number',
                'role',
                'username',
                'first_name',
                'last_name',
                'password1',
                'password2',
                'is_active',
                'is_staff',
                'is_superuser',
            ),
        }),
    )


admin.site.register(CustomUser, CustomUserAdmin)


# ---------------------------------------------------------------------------
# Bitácoras de mensajes — solo lectura
# ---------------------------------------------------------------------------

class _MessageLogAdmin(admin.ModelAdmin):
    """
    Base admin for all three notification log models.
    Logs are immutable — add, change, and delete are disabled.
    """

    ordering = ('-created_at',)
    save_on_top = True

    @admin.display(description='Estado')
    def display_status(self, obj):
        return _status_badge(obj)

    @admin.display(description='Canal')
    def display_channel(self, obj):
        return _channel_badge(obj)

    @admin.display(description='Mensaje')
    def short_message(self, obj):
        return (obj.message[:90] + '…') if len(obj.message) > 90 else obj.message

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(EmployeeMessages)
class EmployeeMessagesAdmin(_MessageLogAdmin):
    list_display = (
        'display_status',
        'display_channel',
        'messageType',
        'employee_name',
        'phone_number',
        'short_message',
        'created_at',
    )
    list_filter = ('status', 'channel', 'messageType', 'created_at')
    search_fields = ('employee_name', 'phone_number', 'message', 'error_message')
    readonly_fields = (
        'id',
        'employee',
        'employee_name',
        'phone_number',
        'messageType',
        'channel',
        'status',
        'message',
        'error_message',
        'created_at',
        'updated_at',
    )
    fieldsets = (
        ('Destinatario', {
            'fields': ('id', 'employee', 'employee_name', 'phone_number')
        }),
        ('Mensaje enviado', {
            'fields': ('messageType', 'channel', 'status', 'message')
        }),
        ('Error', {
            'fields': ('error_message',)
        }),
        ('Fechas de registro', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(AdminMessages)
class AdminMessagesAdmin(_MessageLogAdmin):
    list_display = (
        'display_status',
        'display_channel',
        'messageType',
        'admin_name',
        'short_message',
        'created_at',
    )
    list_filter = ('status', 'channel', 'messageType', 'created_at')
    search_fields = ('admin_name', 'message', 'error_message')
    readonly_fields = (
        'id',
        'admin',
        'admin_name',
        'phone_number',
        'messageType',
        'channel',
        'status',
        'message',
        'error_message',
        'created_at',
        'updated_at',
    )
    fieldsets = (
        ('Destinatario', {
            'fields': ('id', 'admin', 'admin_name', 'phone_number')
        }),
        ('Mensaje enviado', {
            'fields': ('messageType', 'channel', 'status', 'message')
        }),
        ('Error', {
            'fields': ('error_message',)
        }),
        ('Fechas de registro', {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(ClientMessages)
class ClientMessagesAdmin(_MessageLogAdmin):
    list_display = (
        'display_status',
        'display_channel',
        'messageType',
        'client_name',
        'short_message',
        'created_at',
    )
    list_filter = ('status', 'channel', 'messageType', 'created_at')
    search_fields = ('client_name', 'message', 'error_message')
    readonly_fields = (
        'id',
        'client',
        'client_name',
        'phone_number',
        'messageType',
        'channel',
        'status',
        'message',
        'error_message',
        'created_at',
        'updated_at',
    )
    fieldsets = (
        ('Destinatario', {
            'fields': ('id', 'client', 'client_name', 'phone_number')
        }),
        ('Mensaje enviado', {
            'fields': ('messageType', 'channel', 'status', 'message')
        }),
        ('Error', {
            'fields': ('error_message',)
        }),
        ('Fechas de registro', {
            'fields': ('created_at', 'updated_at')
        }),
    )
