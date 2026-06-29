from django.urls import path

from .views import (
    EmployeeActivateView,
    EmployeePasswordResetConfirmView,
    EmployeePasswordResetView,
    EmployeeRegisterView,
    EmployeeSetPasswordView,
)

urlpatterns = [
    path('employee/register/', EmployeeRegisterView.as_view(), name='employee-register'),
    path('employee/activate/', EmployeeActivateView.as_view(), name='employee-activate'),
    path('employee/password-reset/', EmployeePasswordResetView.as_view(), name='employee-password-reset'),
    path('employee/password-reset/confirm/', EmployeePasswordResetConfirmView.as_view(), name='employee-password-reset-confirm'),
    path('employee/set-password/', EmployeeSetPasswordView.as_view(), name='employee-set-password'),
]
