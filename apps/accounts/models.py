import uuid

from django.db.models import EmailField
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

from apps.core.models import BaseModel


class CustomUser(AbstractUser):
    """
    Custom user model for Safe + Clean Qro.
    Uses email as the primary authentication field.
    Supports three roles: Admin, Employee, and Client.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Administrador'
        EMPLOYEE = 'EMPLOYEE', 'Empleado'
        CLIENT = 'CLIENT', 'Cliente'


    # Remove default username field - use email instead
    username = None
    email = models.EmailField("correo electrónico", unique=True)
    phone = models.CharField("teléfono", max_length=15, blank=True)
    role = models.CharField(
        "rol",
        max_length=20,
        choices=Role.choices,
        default=Role.EMPLOYEE,
    )

    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]


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

