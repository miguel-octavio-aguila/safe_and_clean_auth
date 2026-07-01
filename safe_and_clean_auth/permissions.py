from rest_framework import permissions
from django.conf import settings


class has_valid_api_key(permissions.BasePermission):
    """
    Custom permission to only allow access to users with a valid API key.
    """
    def has_permission(self, request, view):
        api_key = request.headers.get("x-api-key")
        if api_key not in getattr(settings, "VALID_API_KEYS", []):
            return False
        return True


class admin_permission(has_valid_api_key):
    """
    Custom permission to only allow admins to access the endpoint.
    """
    def has_permission(self, request, view):
        api_key = request.headers.get("x-api-key")
        if api_key != getattr(settings, "ADMIN_API_KEY"):
            return False
        return True


class employee_permission(has_valid_api_key):
    """
    Custom permission to only allow employees to access the endpoint.
    """
    def has_permission(self, request, view):
        api_key = request.headers.get("x-api-key")
        if api_key != getattr(settings, "EMPLOYEE_API_KEY"):
            return False
        return True


class client_permission(has_valid_api_key):
    """
    Custom permission to only allow clients to access the endpoint.
    """
    def has_permission(self, request, view):
        api_key = request.headers.get("x-api-key")
        if api_key != getattr(settings, "CLIENT_API_KEY"):
            return False
        return True
