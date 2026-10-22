"""Persistent purchase missions, event snapshots, and controlled contact attempts."""
from __future__ import annotations

import uuid

from django.db import models

from apps.catalog.models import Offer, Shop


class PurchaseMission(models.Model):
    class Status(models.TextChoices):
        CREATED = "created", "ایجاد شده"
        ACTIVE = "active", "در حال اجرا"
        WAITING_FOR_USER = "waiting_for_user", "در انتظار کاربر"
        COMPLETED = "completed", "تکمیل شده"
        FAILED = "failed", "ناموفق"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    initial_message = models.TextField(max_length=2000)
    # Random server-side session owner. Never serialized into the public mission snapshot.
    owner_token = models.CharField(max_length=64, null=True, blank=True, db_index=True)
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.CREATED)
    current_stage = models.CharField(max_length=80, default="created")
    constraints = models.JSONField(default=dict, blank=True)
    state = models.JSONField(default=dict, blank=True)
    client_request_id = models.CharField(max_length=100, blank=True, null=True)
    last_event_seq = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "purchase_mission"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "updated_at"], name="mission_status_updated_idx"),
        ]

    def __str__(self) -> str:
        return f"Mission {self.pk} ({self.status})"


class MissionEvent(models.Model):
    mission = models.ForeignKey(
        PurchaseMission, on_delete=models.CASCADE, related_name="events"
    )
    seq = models.PositiveIntegerField()
    event_type = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "purchase_mission_event"
        ordering = ["seq"]
        constraints = [
            models.UniqueConstraint(fields=["mission", "seq"], name="mission_event_seq_uniq")
        ]
        indexes = [models.Index(fields=["mission", "created_at"], name="mission_event_time_idx")]

    def __str__(self) -> str:
        return f"{self.mission_id}:{self.seq} {self.event_type}"


class ContactAttempt(models.Model):
    class Purpose(models.TextChoices):
        VERIFY_AVAILABILITY = "verify_availability", "بررسی موجودی"
        VERIFY_PRICE = "verify_price", "بررسی قیمت"
        VERIFY_HOURS = "verify_hours", "بررسی ساعت کاری"

    class Outcome(models.TextChoices):
        CONFIRMED_AVAILABLE = "confirmed_available", "موجودی تأیید شد"
        UNAVAILABLE = "unavailable", "ناموجود"
        NO_ANSWER = "no_answer", "بدون پاسخ"
        CLOSED = "closed", "بسته"
        ERROR = "error", "خطا"
        PRICE_CHANGED = "price_changed", "تغییر قیمت گزارش‌شده در شبیه‌سازی"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    mission = models.ForeignKey(
        PurchaseMission, on_delete=models.CASCADE, related_name="contact_attempts"
    )
    shop = models.ForeignKey(
        Shop, to_field="source_id", on_delete=models.PROTECT, related_name="contact_attempts"
    )
    offer = models.ForeignKey(
        Offer,
        to_field="source_id",
        on_delete=models.PROTECT,
        related_name="contact_attempts",
        null=True,
        blank=True,
    )
    purpose = models.CharField(max_length=32, choices=Purpose.choices)
    outcome = models.CharField(max_length=32, choices=Outcome.choices)
    source_type = models.CharField(max_length=32, default="demo_simulation")
    scenario_index = models.PositiveIntegerField(default=0)
    response_text = models.TextField(blank=True, default="")
    # Retry a contact with the same key without changing its simulated outcome.
    client_request_id = models.CharField(max_length=100, blank=True, null=True)
    response_snapshot = models.JSONField(blank=True, default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "purchase_contact_attempt"
        ordering = ["created_at", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["mission", "client_request_id"],
                name="contact_attempt_idempotent_uniq",
            ),
        ]
        indexes = [
            models.Index(fields=["mission", "created_at"], name="contact_mission_time_idx"),
            models.Index(fields=["shop", "outcome"], name="contact_shop_outcome_idx"),
        ]

    def __str__(self) -> str:
        return f"Contact {self.id} to {self.shop_id}: {self.outcome}"
