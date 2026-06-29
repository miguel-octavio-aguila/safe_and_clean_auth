from django.contrib.auth import get_user_model
from django.contrib.auth.models import update_last_login
from rest_framework import serializers, exceptions
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from djoser.serializers import UserCreatePasswordRetypeSerializer
from apps.accounts.models import Role

User = get_user_model()


class UserCreateSerializer(UserCreatePasswordRetypeSerializer):
    class Meta(UserCreatePasswordRetypeSerializer.Meta):
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
                user = User.objects.get(phone_number=phone)
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
        update_last_login(None, self.user)

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
                user = User.objects.get(phone_number=phone)
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


# ---------------------------------------------------------------------------
# Employee SMS flow
# ---------------------------------------------------------------------------

class EmployeeUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'phone_number', 'first_name', 'last_name', 'role', 'is_active', 'created_at', 'updated_at']
        read_only_fields = fields


class EmployeeRegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)
    re_password = serializers.CharField(write_only=True)

    def validate_phone_number(self, value):
        if User.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError('Ya existe un usuario con este número de teléfono.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['re_password']:
            raise serializers.ValidationError({'re_password': ['Las contraseñas no coinciden.']})
        from django.contrib.auth.password_validation import validate_password
        validate_password(attrs['password'])
        return attrs

    def create(self, validated_data):
        validated_data.pop('re_password')
        password = validated_data.pop('password')
        user = User.objects.create_user(email=None, role=Role.EMPLOYEE, **validated_data)
        user.set_password(password)
        user.save()
        return user


class EmployeeActivateSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    code = serializers.CharField()


class EmployeePasswordResetSerializer(serializers.Serializer):
    phone_number = serializers.CharField()


class EmployeePasswordResetConfirmSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    code = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    re_new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['re_new_password']:
            raise serializers.ValidationError({'re_new_password': ['Las contraseñas no coinciden.']})
        from django.contrib.auth.password_validation import validate_password
        validate_password(attrs['new_password'])
        return attrs


class EmployeeSetPasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    re_new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['re_new_password']:
            raise serializers.ValidationError({'re_new_password': ['Las contraseñas no coinciden.']})
        from django.contrib.auth.password_validation import validate_password
        validate_password(attrs['new_password'])
        return attrs
