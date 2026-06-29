from django.utils.http import is_same_domain
import uuid

from django.db.models import EmailField
from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin
)
from djoser.signals import user_registered, user_activated
from django.utils import timezone

from ..core.models import BaseModel

class Role(models.TextChoices):
    ADMIN = 'ADMIN', 'Administrador'
    EMPLOYEE = 'EMPLOYEE', 'Empleado'
    CLIENT = 'CLIENT', 'Cliente'


class MessageType(models.TextChoices):
    ACTIVATION = 'ACTIVATION', 'Activación'
    CONFIRMATION = 'CONFIRMATION', 'Confirmación'
    PASSWORD_CHANGE = 'PASSWORD_CHANGE', 'Cambio de contraseña'
    PASSWORD_RESET = 'PASSWORD_RESET', 'Restablecimiento de contraseña'
    PASSWORD_RESET_CONFIRM = 'PASSWORD_RESET_CONFIRM', 'Confirmación de restablecimiento de contraseña'


class MessageChannel(models.TextChoices):
    EMAIL = 'EMAIL', 'Correo electrónico'
    SMS = 'SMS', 'SMS'


class MessageStatus(models.TextChoices):
    SUCCESS = 'SUCCESS', 'Enviado'
    FAILED  = 'FAILED',  'Fallido'

class UserAccountManager(BaseUserManager):
    """
    Manager for user accounts.
    """

    RESTRICTED_USERNAMES = ['admin', 'superuser', 'staff', 'undefined', 'null', 'root', 'system']

    def create_user(self, email, password=None, **extra_fields):
        phone = extra_fields.get('phone_number', '')
        role = extra_fields.get('role', Role.EMPLOYEE)

        if role == Role.EMPLOYEE and not phone:
            raise ValueError('Este tipo de usuario debe de tener un teléfono registrado')

        if role in [Role.CLIENT, Role.ADMIN] and not phone and not email:
            raise ValueError('Este tipo de usuario debe de tener un teléfono o correo electrónico registrado')

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)

        first_name = extra_fields.get('first_name', '')
        last_name = extra_fields.get('last_name', '')

        if not first_name or not last_name:
            raise ValueError('Los usuarios deben de tener un nombre y apellido registrado')

        username = extra_fields.get('username', None)
        if username and username.lower() in self.RESTRICTED_USERNAMES:
            raise ValueError(f'El nombre de usuario "{username}" no está permitido.')

        if not username:
            user.username = email

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', Role.ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for Safe + Clean Qro.
    Uses email as the primary authentication field.
    Supports three roles: Admin, Employee, and Client.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, unique=True)
    username = models.CharField("nombre de usuario", max_length=150, unique=True)
    email = models.EmailField("correo electrónico", unique=True)
    phone_number = models.CharField("teléfono", max_length=15, blank=True, unique=True)
    first_name = models.CharField("nombre", max_length=150)
    last_name = models.CharField("apellido", max_length=150)

    role = models.CharField(
        "rol",
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,
    )

    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]

    objects = UserAccountManager()

    class Meta:
        db_table = '"accounts"."custom_user"'
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["last_name", "first_name"]
        indexes = [
            models.Index(fields=["role"]),
            models.Index(fields=["email"]),
        ]


    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    @property
    def is_employee_role(self):
        return self.role == self.Role.EMPLOYEE

    @property
    def is_client_role(self):
        return self.role == self.Role.CLIENT


def profile_picture_upload_to(instance, filename):
    """Upload path: media/profile_pictures/<first_name><last_name>/<filename>"""
    return f"profile_pictures/{instance.first_name.lower()}_{instance.last_name.lower()}/{filename}"


class UserProfile(BaseModel):
    """
    Minimal profile for ALL users (Admin, Employee, Client).
    Stored in Auth because it is universal — every user can have a photo.

    Business-specific data lives in the Backend service:
        - Employee details  → personnel.Employee (safe_and_clean_backend)
        - Client details    → accounts.Client    (safe_and_clean_backend)
    """

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name="usuario",
    )
    profile_picture = models.ImageField(
        "foto de perfil",
        upload_to=profile_picture_upload_to,
        blank=True,
        null=True,
    )

    class Meta:
        db_table = '"accounts"."user_profile"'
        verbose_name = "perfil de usuario"
        verbose_name_plural = "perfiles de usuario"

    def __str__(self):
        return f"Perfil de {self.user.get_full_name()}"


class EmployeeMessages(BaseModel):
    employee = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="employee_messages",
        verbose_name="empleado",
        limit_choices_to={'role': Role.EMPLOYEE}
    )
    messageType = models.CharField(
        "tipo de mensaje",
        max_length=50,
        choices=MessageType.choices,
    )
    channel = models.CharField(
        "canal",
        max_length=5,
        choices=MessageChannel.choices,
        default=MessageChannel.SMS,
    )
    status = models.CharField(
        "estado",
        max_length=10,
        choices=MessageStatus.choices,
        default=MessageStatus.SUCCESS,
    )
    message = models.TextField("mensaje")
    error_message = models.TextField("mensaje de error", blank=True)

    employee_name = models.CharField("nombre del empleado", max_length=255, blank=True)
    phone_number = models.CharField("teléfono", max_length=15, blank=True)

    class Meta:
        db_table = '"accounts"."employee_messages"'
        verbose_name = "mensaje de empleado"
        verbose_name_plural = "mensajes de empleados"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.employee:
            if not self.employee_name:
                self.employee_name = self.employee.get_full_name()
            if not self.phone_number:
                self.phone_number = self.employee.phone_number
        super().save(*args, **kwargs)

    def __str__(self):
        return self.message


class AdminMessages(BaseModel):
    admin = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="admin_messages",
        verbose_name="admin",
        limit_choices_to={'role': Role.ADMIN}
    )
    messageType = models.CharField(
        "tipo de mensaje",
        max_length=50,
        choices=MessageType.choices,
    )
    channel = models.CharField(
        "canal",
        max_length=5,
        choices=MessageChannel.choices,
        default=MessageChannel.EMAIL,
    )
    status = models.CharField(
        "estado",
        max_length=10,
        choices=MessageStatus.choices,
        default=MessageStatus.SUCCESS,
    )
    message = models.TextField("mensaje")
    error_message = models.TextField("mensaje de error", blank=True)

    admin_name = models.CharField("nombre del admin", max_length=255, blank=True)
    phone_number = models.CharField("teléfono", max_length=15, blank=True)

    class Meta:
        db_table = '"accounts"."admin_messages"'
        verbose_name = "mensaje de admin"
        verbose_name_plural = "mensajes de admins"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.admin:
            if not self.admin_name:
                self.admin_name = self.admin.get_full_name()
            if not self.phone_number:
                self.phone_number = self.admin.phone_number
        super().save(*args, **kwargs)

    def __str__(self):
        return self.message


class ClientMessages(BaseModel):
    client = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="client_messages",
        verbose_name="cliente",
        limit_choices_to={'role': Role.CLIENT}
    )
    messageType = models.CharField(
        "tipo de mensaje",
        max_length=50,
        choices=MessageType.choices,
    )
    channel = models.CharField(
        "canal",
        max_length=5,
        choices=MessageChannel.choices,
        default=MessageChannel.EMAIL,
    )
    status = models.CharField(
        "estado",
        max_length=10,
        choices=MessageStatus.choices,
        default=MessageStatus.SUCCESS,
    )
    message = models.TextField("mensaje")
    error_message = models.TextField("mensaje de error", blank=True)

    client_name = models.CharField("nombre del cliente", max_length=255, blank=True)
    phone_number = models.CharField("teléfono", max_length=15, blank=True)

    class Meta:
        db_table = '"accounts"."client_messages"'
        verbose_name = "mensaje de cliente"
        verbose_name_plural = "mensajes de clientes"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.client:
            if not self.client_name:
                self.client_name = self.client.get_full_name()
            if not self.phone_number:
                self.phone_number = self.client.phone_number
        super().save(*args, **kwargs)

    def __str__(self):
        return self.message



def post_user_registered(user, *args, **kwargs):
    print("Usuario registrado exitosamente")

def post_user_activated(user, *args, **kwargs):
    print("Usuario activado exitosamente")

user_registered.connect(post_user_registered)
user_activated.connect(post_user_activated)
