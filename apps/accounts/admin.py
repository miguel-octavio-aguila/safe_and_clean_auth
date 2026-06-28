from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    # User's list fields to show
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "phone_number",
        "is_active",
        "is_staff",
    )
    list_filter = (
        "role",
        "is_active",
        "is_staff",
        "is_superuser",
        "created_at",
    )

    # Fields to show in the edit form
    fieldsets = (
        (None, {
            'fields': (
                'email',
                'phone_number',
                'role',
                'username',
                'password'
            )
        }),
        ('Personal Info', {
            'fields': (
                'first_name',
                'last_name'
            )
        }),
        ('Permissions', {
            'fields': (
                'is_active',
                'is_staff',
                'is_superuser',
                'groups',
                'user_permissions'
            )
        }),
        ('Important Dates', {
            'fields': (
                'last_login',
                'created_at',
                'updated_at'
            )
        })
    )

    # Fields to show when create a new user
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
                'is_superuser'
            )
        }),
    )

    search_fields = ('username', 'email', 'first_name', 'last_name', 'phone_number', 'role')
    ordering = ('email',)
    readonly_fields = ('created_at', 'updated_at', 'last_login')


admin.site.register(CustomUser, CustomUserAdmin)
