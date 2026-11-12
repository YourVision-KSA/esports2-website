"""Kept so existing imports keep working; the verifier now lives in core/turnstile.py
because registration uses it too (audit 2026-11-13)."""

from core.turnstile import SITEVERIFY_URL, verify  # noqa: F401
