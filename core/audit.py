"""Audit trail writer. Call record() for every action listed in docs/data-model.md:
result entry/correction, ballot hold/invalidate, registration remove/promote,
invitation revoke/check-in, SiteConfig changes, every PII export."""

from .models import AuditLog


def record(actor, action: str, obj=None, before=None, after=None, model="", object_id=""):
    AuditLog.objects.create(
        actor=actor if getattr(actor, "pk", None) else None,
        action=action,
        model=model or (obj._meta.label if obj is not None else ""),
        object_id=str(object_id or (obj.pk if obj is not None else "")),
        before=before,
        after=after,
    )
