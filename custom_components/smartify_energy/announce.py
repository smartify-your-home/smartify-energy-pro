"""Sprachansagen für fertige Haushaltsgeräte.

SEP spricht nicht selbst: Es ruft ein frei wählbares Home-Assistant-Script
auf und übergibt den Text in der Variable ``message``. Wo und wie angesagt
wird (Lautsprecher, TTS, Lautstärke), entscheidet allein dieses Script.
"""
from __future__ import annotations

from datetime import datetime, time

from .helpers import in_window

KIND_FINISHED = "finished"
KIND_REMINDER = "reminder"
REMINDER_SECONDS = 30 * 60

_TEXTS = {
    "de": {
        KIND_FINISHED: "{name} ist fertig.",
        KIND_REMINDER: "{name} ist fertig – bitte ausräumen.",
    },
    "en": {
        KIND_FINISHED: "{name} has finished.",
        KIND_REMINDER: "{name} has finished – please unload.",
    },
}


def announce_text(kind: str, name: str, language: str | None) -> str:
    """Ansagetext in der HA-Sprache (Deutsch, sonst Englisch)."""
    lang = "de" if str(language or "de").lower().startswith("de") else "en"
    return _TEXTS[lang].get(kind, _TEXTS[lang][KIND_FINISHED]).format(name=name)


def announce_window_open(now: datetime, start: time, end: time) -> bool:
    """Ansagen sind erlaubt; gleiche Zeiten bedeuten: rund um die Uhr."""
    return start == end or in_window(now, start, end)
