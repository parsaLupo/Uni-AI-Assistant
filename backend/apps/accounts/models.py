"""Authentication domain: identity, roles and refresh-token records.

Policy decisions implemented here are recorded in ADR-014 (closing OA-01, OA-02,
OA-09, OA-23): email is the identity, the role enum drives authorization
(OA-03), refresh tokens rotate with reuse detection, and passwords are hashed
with Argon2id.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class Role(models.TextChoices):
    """Authorization roles (docs/05-authentication.md section 2)."""

    STUDENT = "STUDENT", "Student"
    PROFESSOR = "PROFESSOR", "Professor"
    ADMIN = "ADMIN", "Admin"
    SUPERADMIN = "SUPERADMIN", "Superadmin"

    @classmethod
    def privileged(cls) -> set[str]:
        """Roles that may only be granted or removed by a SUPERADMIN."""
        return {cls.ADMIN, cls.SUPERADMIN}


class UserManager(BaseUserManager):
    """User manager keyed on a normalized (lowercased) email."""

    use_in_migrations = True

    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("Users must have an email address.")
        # Full lowercase, not just the domain (Django's default
        # normalize_email): docs/api/auth.md promises case-insensitive identity
        # and login lookups are exact, so storage and lookup must agree.
        user = self.model(email=self.normalize_email(email).lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", Role.STUDENT)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", Role.SUPERADMIN)
        if extra_fields.get("role") != Role.SUPERADMIN:
            raise ValueError("A superuser must have the SUPERADMIN role.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Project user (docs/03 section 3, ADR-014).

    `is_staff`/`is_superuser` come from PermissionsMixin but only gate Django
    internals; application authorization keys on `role` (OA-03) and the Django
    admin UI is not installed.
    """

    email = models.EmailField("email address", unique=True, max_length=254)
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(
        max_length=16,
        choices=Role.choices,
        default=Role.STUDENT,
        db_index=True,
    )
    is_active = models.BooleanField(default=True)
    date_joined = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    objects = UserManager()

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.email

    @property
    def is_privileged(self) -> bool:
        return self.role in Role.privileged()


class RefreshTokenRecord(models.Model):
    """Server-side refresh-token ledger (ADR-014 decision 3).

    One row per issued refresh token. `family` links every rotation of the same
    login session, so a replayed (already revoked) token allows revoking the
    entire family at once — the standard response to token theft.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="refresh_tokens",
    )
    jti = models.CharField(max_length=64, unique=True)
    family = models.UUIDField(db_index=True)
    issued_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(null=True, blank=True)
    replaced_by_jti = models.CharField(max_length=64, null=True, blank=True)

    class Meta:
        ordering = ["-issued_at"]

    def __str__(self) -> str:
        state = "revoked" if self.revoked_at else "active"
        return f"{self.jti} ({state})"

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None
