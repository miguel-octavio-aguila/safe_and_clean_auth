from rest_framework import serializers, exceptions
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from djoser.serializers import UserCreateSerializer
from djoser.conf import settings as djoser_settings
from django.contrib.auth import get_user_model
from apps.accounts.models import Role

User = get_user_model()


class UserCreateSerializer(UserCreateSerializer):
    class Meta(UserCreateSerializer.Meta):
        model = User
        fields = "__all__"


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'username',
            'first_name',
            'last_name',
            'updated_at'
        ]

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields[self.username_field].required = False
        self.fields['phone'] = serializers.CharField(required=False)

    def validate(self, attrs):
        password = attrs.get('password')
        email = attrs.get(self.username_field)
        phone = attrs.get('phone')

        if not email and not phone:
            raise serializers.ValidationError('Debe proporcionar email o teléfono.')

        user = None

        if email:
            try:
                user = User.objects.get(email=email)
                if user.role not in [Role.ADMIN, Role.CLIENT]:
                    raise serializers.ValidationError('Los empleados deben iniciar sesión con su teléfono.')
            except User.DoesNotExist:
                pass
        elif phone:
            try:
                user = User.objects.get(phone=phone)
                if user.role != Role.EMPLOYEE:
                    raise serializers.ValidationError('Los administradores y clientes deben iniciar sesión con su correo electrónico.')
            except User.DoesNotExist:
                pass

        if not user or not user.check_password(password):
            raise exceptions.AuthenticationFailed(
                self.error_messages.get('no_active_account', 'No active account found with the given credentials'),
                'no_active_account',
            )

        if not user.is_active:
            raise exceptions.AuthenticationFailed(
                self.error_messages.get('no_active_account', 'No active account found with the given credentials'),
                'no_active_account',
            )

        self.user = user

        refresh = self.get_token(self.user)

        data = {}
        data['refresh'] = str(refresh)
        data['access'] = str(refresh.access_token)

        return data

class CustomPasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    phone = serializers.CharField(required=False)

    def validate(self, attrs):
        email = attrs.get("email")
        phone = attrs.get("phone")

        if not email and not phone:
            raise serializers.ValidationError("Debe proporcionar email o teléfono.")

        self.user = None
        if email:
            try:
                user = User.objects.get(email=email)
                if user.role not in [Role.ADMIN, Role.CLIENT]:
                    raise serializers.ValidationError("Los empleados deben recuperar contraseña con su teléfono.")
                self.user = user
            except User.DoesNotExist:
                pass
        elif phone:
            try:
                user = User.objects.get(phone=phone)
                if user.role != Role.EMPLOYEE:
                    raise serializers.ValidationError("Los administradores y clientes deben recuperar contraseña con su correo.")
                self.user = user
            except User.DoesNotExist:
                pass

        if self.user and not self.user.is_active:
            raise serializers.ValidationError("Esta cuenta está inactiva.")

        return attrs

    def get_user(self):
        return self.user
