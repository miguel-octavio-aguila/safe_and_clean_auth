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

from apps.core.models import BaseModel

class Role(models.TextChoices):
    ADMIN = 'ADMIN', 'Administrador'
    EMPLOYEE = 'EMPLOYEE', 'Empleado'
    CLIENT = 'CLIENT', 'Cliente'


class UserAccountManager(BaseUserManager):
    """
    Manager for user accounts.
    """

    RESTRICTED_USERNAMES = ['admin', 'superuser', 'staff', 'undefined', 'null', 'root', 'system']
    
    def create_user(self, email, phone, password=None, **extra_fields):
        if Role.EMPLOYEE and not phone:
            raise ValueError('Este tipo de usuario debe de tener un teléfono registrado')
        
        if Role.CLIENT or Role.ADMIN and not phone and not email:
            raise ValueError('Este tipo de usuario debe de tener un teléfono o correo electrónico registrado')
        
        email = self.normalize_email(email)
        phone = phone
        user = self.model(email=email, phone=phone, **extra_fields)

        first_name = extra_fields.get('first_name', '')
        last_name = extra_fields.get('last_name', '')

        if not first_name and not last_name:
            raise ValueError('Los usuarios deben de tener un nombre y apellido registrado')
        
        user.first_name = first_name
        user.last_name = last_name

        username = extra_fields.get('username', None)
        if username and username.lower() in self.RESTRICTED_USERNAMES:
            raise ValueError(f'El nombre de usuario "{username}" no está permitido.')

        if not username:
            username = self.email
        
        user.save(using=self._db)
        
        return user

    def create_superuser(self, email, phone,password, **extra_fields):
        user = self.create_user(email, phone, password, **extra_fields)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model for Safe + Clean Qro.
    Uses email as the primary authentication field.
    Supports three roles: Admin, Employee, and Client.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField("nombre de usuario", max_length=150, unique=True)
    email = models.EmailField("correo electrónico", unique=True)
    phone = models.CharField("teléfono", max_length=15, blank=True)
    first_name = models.CharField("nombre", max_length=150)
    last_name = models.CharField("apellido", max_length=150)

    role = models.CharField(
        "rol",
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username", "first_name", "last_name"]


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

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN

    @property
    def is_employee_role(self):
        return self.role == self.Role.EMPLOYEE

    @property
    def is_client_role(self):
        return self.role == self.Role.CLIENT


class ClientProfile(BaseModel):
    """
    Extended profile for CLIENT-role users.
    Represents a company or organization (corporativo, industrial, plaza comercial)
    that contracts Safe + Clean Qro's services.
    """

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="client_profile",
        verbose_name="usuario",
    )
    company_name = models.CharField("nombre de empresa", max_length=200)
    contact_name = models.CharField("nombre de contacto", max_length=200)
    address = models.CharField("dirección", max_length=300, blank=True)
    notes = models.TextField("notas", blank=True)


    class Meta:
        db_table = '"accounts"."client_profile"'
        verbose_name = "perfil de cliente"
        verbose_name_plural = "perfiles de clientes"
        ordering = ["company_name"]


    def __str__(self):
        return self.company_name


def post_user_registered(user, *args, **kwargs):
    print("Usuario registrado exitosamente")

def post_user_activated(user, *args, **kwargs):
    print("Usuario activado exitosamente")

user_registered.connect(post_user_registered)
user_activated.connect(post_user_activated)
