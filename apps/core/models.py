import uuid

from django.db import models
from django.utils import timezone


class BaseModel(models.Model):
    """
    Abstract base model for all Safe + Clean Qro models.
    Provides audit timestamps and soft-delete suppport via is_active.
    All models in the project must inherit from this class.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField("Fecha de creación", default=timezone.now)
    updated_at = models.DateTimeField("Fecha de actualización", auto_now=True)

    is_active = models.BooleanField("Activo", default=True)

    class Meta:
        abstract = True

