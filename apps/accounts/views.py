from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.rate_limiting import RateLimitExceeded

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
        return Response({'detail': str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
    if isinstance(e, TwilioRestException):
        return Response({'detail': 'Error al enviar el SMS. Intenta de nuevo más tarde.'}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    raise e


class EmployeeRegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmployeeRegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        try:
            send_activation_otp(user)
        except Exception as e:
            return _sms_error(e)
        return Response(EmployeeUserSerializer(user).data, status=status.HTTP_201_CREATED)


class EmployeeActivateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmployeeActivateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']

        try:
            user = User.objects.get(phone_number=phone, role=Role.EMPLOYEE)
        except User.DoesNotExist:
            return Response({'phone_number': ['No existe un empleado con este número.']}, status=status.HTTP_400_BAD_REQUEST)

        if user.is_active:
            return Response({'detail': 'La cuenta ya está activa.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            approved = verify_sms_otp(user, code)
        except Exception as e:
            return _sms_error(e)

        if not approved:
            return Response({'code': ['Código incorrecto o expirado.']}, status=status.HTTP_400_BAD_REQUEST)

        user.is_active = True
        user.save()

        from .models import UserProfile
        UserProfile.objects.get_or_create(user=user)

        try:
            send_confirmation_sms(user)
        except Exception:
            pass

        return Response({'detail': 'Cuenta activada exitosamente.'}, status=status.HTTP_200_OK)


class EmployeePasswordResetView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmployeePasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone_number']
        generic_response = Response(
            {'detail': 'Si el número está registrado y activo, recibirás un código.'},
            status=status.HTTP_200_OK,
        )

        try:
            user = User.objects.get(phone_number=phone, role=Role.EMPLOYEE, is_active=True)
        except User.DoesNotExist:
            return generic_response

        try:
            send_password_reset_otp(user)
        except RateLimitExceeded as e:
            return Response({'detail': str(e)}, status=status.HTTP_429_TOO_MANY_REQUESTS)
        except Exception:
            pass

        return generic_response


class EmployeePasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmployeePasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data['phone_number']
        code = serializer.validated_data['code']
        new_password = serializer.validated_data['new_password']

        try:
            user = User.objects.get(phone_number=phone, role=Role.EMPLOYEE, is_active=True)
        except User.DoesNotExist:
            return Response({'phone_number': ['No existe un empleado activo con este número.']}, status=status.HTTP_400_BAD_REQUEST)

        try:
            approved = verify_sms_otp(user, code)
        except Exception as e:
            return _sms_error(e)

        if not approved:
            return Response({'code': ['Código incorrecto o expirado.']}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        try:
            send_password_reset_confirm_sms(user)
        except Exception:
            pass

        return Response({'detail': 'Contraseña restablecida exitosamente.'}, status=status.HTTP_200_OK)


class EmployeeSetPasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.role != Role.EMPLOYEE:
            return Response({'detail': 'Solo los empleados pueden usar este endpoint.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = EmployeeSetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.check_password(serializer.validated_data['current_password']):
            return Response({'current_password': ['Contraseña actual incorrecta.']}, status=status.HTTP_400_BAD_REQUEST)

        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()

        try:
            send_password_changed_sms(request.user)
        except Exception:
            pass

        return Response({'detail': 'Contraseña actualizada exitosamente.'}, status=status.HTTP_200_OK)
