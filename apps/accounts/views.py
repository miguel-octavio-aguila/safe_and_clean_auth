from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework_api.views import StandardAPIView

from apps.core.rate_limiting import RateLimitExceeded
from safe_and_clean_auth.permissions import admin_permission, employee_permission

from .models import Role

User = get_user_model()
from .serializers import (
    EmployeeActivateSerializer,
    EmployeePasswordResetConfirmSerializer,
    EmployeePasswordResetSerializer,
    EmployeeRegisterSerializer,
    EmployeeSetPasswordSerializer,
    EmployeeUserSerializer,
)
from .services import (
    send_activation_otp,
    send_confirmation_sms,
    send_password_changed_sms,
    send_password_reset_confirm_sms,
    send_password_reset_otp,
    verify_sms_otp,
)


def _sms_error(e):
    from twilio.base.exceptions import TwilioRestException
    if isinstance(e, RateLimitExceeded):
        return {'detail': str(e)}, status.HTTP_429_TOO_MANY_REQUESTS
    if isinstance(e, TwilioRestException):
        return {'detail': 'Error al enviar el SMS. Intenta de nuevo más tarde.'}, status.HTTP_503_SERVICE_UNAVAILABLE
    raise e


class EmployeeRegisterView(StandardAPIView):
    permission_classes = [admin_permission | employee_permission]

    def post(self, request):
        try:
            serializer = EmployeeRegisterSerializer(data=request.data)
            if not serializer.is_valid():
                return self.error(error=serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            user = serializer.save()

            try:
                send_activation_otp(user)
            except Exception as e:
                error, err_status = _sms_error(e)
                return self.error(error=error, status=err_status)

            return self.response(data=EmployeeUserSerializer(user).data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return self.error(error=str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmployeeActivateView(StandardAPIView):
    permission_classes = [employee_permission]

    def post(self, request):
        try:
            serializer = EmployeeActivateSerializer(data=request.data)
            if not serializer.is_valid():
                return self.error(error=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            phone = serializer.validated_data['phone_number']
            code = serializer.validated_data['code']

            try:
                user = User.objects.get(phone_number=phone, role=Role.EMPLOYEE)
            except User.DoesNotExist:
                return self.error(error={'phone_number': ['No existe un empleado con este número.']}, status=status.HTTP_400_BAD_REQUEST)

            if user.is_active:
                return self.error(error={'detail': 'La cuenta ya está activa.'}, status=status.HTTP_400_BAD_REQUEST)

            try:
                approved = verify_sms_otp(user, code)
            except Exception as e:
                error, err_status = _sms_error(e)
                return self.error(error=error, status=err_status)

            if not approved:
                return self.error(error={'code': ['Código incorrecto o expirado.']}, status=status.HTTP_400_BAD_REQUEST)

            user.is_active = True
            user.save()

            from .models import UserProfile
            UserProfile.objects.get_or_create(user=user)

            try:
                send_confirmation_sms(user)
            except Exception:
                pass

            return self.response(data={'detail': 'Cuenta activada exitosamente.'})
        except Exception as e:
            return self.error(error=str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmployeePasswordResetView(StandardAPIView):
    permission_classes = [employee_permission]

    def post(self, request):
        try:
            serializer = EmployeePasswordResetSerializer(data=request.data)
            if not serializer.is_valid():
                return self.error(error=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            phone = serializer.validated_data['phone_number']
            generic_data = {'detail': 'Si el número está registrado y activo, recibirás un código.'}

            try:
                user = User.objects.get(phone_number=phone, role=Role.EMPLOYEE, is_active=True)
            except User.DoesNotExist:
                return self.response(data=generic_data)

            try:
                send_password_reset_otp(user)
            except RateLimitExceeded as e:
                return self.error(error={'detail': str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
            except Exception:
                pass

            return self.response(data=generic_data)
        except Exception as e:
            return self.error(error=str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmployeePasswordResetConfirmView(StandardAPIView):
    permission_classes = [employee_permission]

    def post(self, request):
        try:
            serializer = EmployeePasswordResetConfirmSerializer(data=request.data)
            if not serializer.is_valid():
                return self.error(error=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            phone = serializer.validated_data['phone_number']
            code = serializer.validated_data['code']
            new_password = serializer.validated_data['new_password']

            try:
                user = User.objects.get(phone_number=phone, role=Role.EMPLOYEE, is_active=True)
            except User.DoesNotExist:
                return self.error(error={'phone_number': ['No existe un empleado activo con este número.']}, status=status.HTTP_400_BAD_REQUEST)

            try:
                approved = verify_sms_otp(user, code)
            except Exception as e:
                error, err_status = _sms_error(e)
                return self.error(error=error, status=err_status)

            if not approved:
                return self.error(error={'code': ['Código incorrecto o expirado.']}, status=status.HTTP_400_BAD_REQUEST)

            user.set_password(new_password)
            user.save()

            try:
                send_password_reset_confirm_sms(user)
            except Exception:
                pass

            return self.response(data={'detail': 'Contraseña restablecida exitosamente.'})
        except Exception as e:
            return self.error(error=str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class EmployeeSetPasswordView(StandardAPIView):
    permission_classes = [IsAuthenticated, employee_permission]

    def post(self, request):
        try:
            if request.user.role != Role.EMPLOYEE:
                return self.error(error={'detail': 'Solo los empleados pueden usar este endpoint.'}, status=status.HTTP_403_FORBIDDEN)

            serializer = EmployeeSetPasswordSerializer(data=request.data)
            if not serializer.is_valid():
                return self.error(error=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            if not request.user.check_password(serializer.validated_data['current_password']):
                return self.error(error={'current_password': ['Contraseña actual incorrecta.']}, status=status.HTTP_400_BAD_REQUEST)

            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()

            try:
                send_password_changed_sms(request.user)
            except Exception:
                pass

            return self.response(data={'detail': 'Contraseña actualizada exitosamente.'})
        except Exception as e:
            return self.error(error=str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
