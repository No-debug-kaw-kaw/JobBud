"""Shared, bounded, single-flight cache for slow external data services.

Workers never access Streamlit state. Rendering only reads completed futures.
"""
from concurrent.futures import ThreadPoolExecutor
from threading import RLock
from time import monotonic

_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="jobbud-data")
_lock = RLock()
_entries = {}
MAX_ENTRIES = 128


def get_background_value(key, loader, fallback, ttl=21600):
    """Return (value, pending), never waiting for a network request."""
    with _lock:
        now = monotonic()
        entry = _entries.get(key)
        if entry and entry["future"].done():
            if entry["expires"] is None:
                try:
                    entry["value"] = entry["future"].result()
                    failed = not entry["value"] or (
                        isinstance(entry["value"], dict)
                        and (entry["value"].get("error") or entry["value"].get("available") is False)
                    )
                    entry["expires"] = now + (60 if failed else ttl)
                except Exception:
                    entry["value"] = fallback
                    entry["expires"] = now + 60
            if entry["expires"] > now:
                return entry["value"], False
            del _entries[key]
            entry = None
        if entry:
            return fallback, True
        if len(_entries) >= MAX_ENTRIES:
            completed = next((k for k, v in _entries.items() if v["future"].done()), None)
            if completed is not None:
                del _entries[completed]
            else:
                return fallback, False
        _entries[key] = {"future": _pool.submit(loader), "expires": None}
        return fallback, True


def any_completed(keys):
    with _lock:
        return any(key in _entries and _entries[key]["future"].done() for key in keys)
