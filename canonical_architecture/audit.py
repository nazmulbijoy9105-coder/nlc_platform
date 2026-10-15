"""
R-020: append-only, hash-chained audit trail (in-memory reference implementation).
Production persistence must be an append-only table; this only guarantees
tamper evidence within one process.
"""
import dataclasses
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class AuditEvent:
    seq: int
    ts: str
    kind: str
    subject: str
    detail_json: str
    prev_hash: str
    hash: str


def _digest(seq: int, ts: str, kind: str, subject: str, detail_json: str, prev: str) -> str:
    raw = f"{seq}|{ts}|{kind}|{subject}|{detail_json}|{prev}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AuditTrail:
    def __init__(self) -> None:
        self._events: List[AuditEvent] = []

    def record(self, kind: str, subject: str,
               detail: Optional[Dict[str, Any]] = None,
               ts: Optional[str] = None) -> AuditEvent:
        seq = len(self._events)
        ts = ts or datetime.now(timezone.utc).isoformat()
        detail_json = json.dumps(detail or {}, sort_keys=True, default=str)
        prev = self._events[-1].hash if self._events else "GENESIS"
        ev = AuditEvent(seq, ts, kind, subject, detail_json, prev,
                        _digest(seq, ts, kind, subject, detail_json, prev))
        self._events.append(ev)
        return ev

    def events(self) -> Tuple[AuditEvent, ...]:
        return tuple(self._events)

    def verify(self) -> bool:
        prev = "GENESIS"
        for i, e in enumerate(self._events):
            if e.seq != i or e.prev_hash != prev:
                return False
            if e.hash != _digest(e.seq, e.ts, e.kind, e.subject, e.detail_json, e.prev_hash):
                return False
            prev = e.hash
        return True
