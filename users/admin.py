from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """
    Account/branch assignment is a SuperAdmin-only capability: letting a
    branch employee manage users (even their own branch's) would let them
    grant themselves another branch or elevate their own permissions.
    """

    list_display = ('username', 'first_name', 'last_name', 'branch', 'is_staff', 'is_superuser', 'is_active')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'branch')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'phone_number')

    fieldsets = DjangoUserAdmin.fieldsets + (
        ('CRM', {'fields': ('phone_number', 'image', 'branch')}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ('CRM', {'fields': ('phone_number', 'branch')}),
    )

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
