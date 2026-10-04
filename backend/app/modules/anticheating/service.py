import json
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.anticheating.model import AntiCheatingEvent
from app.modules.anticheating.schema import (
    AntiCheatingEventCreateRequest,
    AntiCheatingEventResponse,
    AntiCheatingSummaryResponse,
    FaceRegistrationRequest,
    FaceRegistrationResponse,
)


def _serialize_event(event: AntiCheatingEvent) -> AntiCheatingEventResponse:
    metadata_val = None
    if event.metadata_json:
        try:
            metadata_val = json.loads(event.metadata_json)
        except Exception:
            metadata_val = None

    return AntiCheatingEventResponse(
        id=event.id,
        interview_id=event.interview_id,
        event_type=event.event_type,
        severity=event.severity,
        timestamp=event.timestamp,
        duration=event.duration,
        confidence=event.confidence,
        description=event.description,
        evidence_reference=event.evidence_reference,
        metadata=metadata_val,
        created_at=event.created_at,
    )


async def record_anti_cheating_event(
    db: AsyncSession,
    interview_id: UUID,
    data: AntiCheatingEventCreateRequest,
) -> AntiCheatingEventResponse:
    metadata_str = json.dumps(data.metadata) if data.metadata else None
    event_timestamp = data.timestamp or datetime.now(timezone.utc)

    event = AntiCheatingEvent(
        interview_id=interview_id,
        event_type=data.event_type,
        severity=data.severity,
        timestamp=event_timestamp,
        duration=data.duration,
        confidence=data.confidence,
        description=data.description,
        evidence_reference=data.evidence_reference,
        metadata_json=metadata_str,
    )

    db.add(event)
    await db.commit()
    await db.refresh(event)

    return _serialize_event(event)


async def get_interview_events(
    db: AsyncSession,
    interview_id: UUID,
) -> list[AntiCheatingEventResponse]:
    stmt = (
        select(AntiCheatingEvent)
        .where(AntiCheatingEvent.interview_id == interview_id)
        .order_by(AntiCheatingEvent.timestamp.asc())
    )
    result = await db.execute(stmt)
    records = result.scalars().all()
    return [_serialize_event(rec) for rec in records]


async def get_interview_summary(
    db: AsyncSession,
    interview_id: UUID,
) -> AntiCheatingSummaryResponse:
    events = await get_interview_events(db, interview_id)

    total_events = len(events)
    face_missing_events = sum(
        1 for e in events if e.event_type in ("FACE_MISSING", "SUSPICIOUS_ABSENCE")
    )
    multiple_person_events = sum(
        1 for e in events if e.event_type == "MULTIPLE_PERSON"
    )
    identity_mismatch_events = sum(
        1 for e in events if e.event_type == "IDENTITY_MISMATCH"
    )
    device_events = sum(
        1 for e in events if e.event_type in ("MOBILE_DETECTED", "DEVICE_DETECTED")
    )
    total_suspicious_duration = round(sum(e.duration for e in events), 2)

    # Deterministic rule-based risk calculation
    raw_score = 0.0
    has_high_severity = False

    for e in events:
        if e.severity == "HIGH":
            raw_score += 25.0 * e.confidence
            if e.confidence >= 0.7:
                has_high_severity = True
        elif e.severity == "MEDIUM":
            raw_score += 15.0 * e.confidence
        else:
            raw_score += 5.0 * e.confidence

    # Additional duration penalty (up to 20 points)
    duration_penalty = min(20.0, total_suspicious_duration * 0.5)
    risk_score = min(100.0, round(raw_score + duration_penalty, 1))

    # Determine overall status
    if has_high_severity or risk_score >= 60.0:
        overall_status = "SUSPICIOUS"
    elif risk_score >= 20.0 or total_events > 0:
        overall_status = "REVIEW"
    else:
        overall_status = "CLEAR"

    return AntiCheatingSummaryResponse(
        overall_status=overall_status,
        total_events=total_events,
        face_missing_events=face_missing_events,
        multiple_person_events=multiple_person_events,
        identity_mismatch_events=identity_mismatch_events,
        device_events=device_events,
        total_suspicious_duration=total_suspicious_duration,
        risk_score=risk_score,
    )


# In-memory session registry for privacy-preserving, session-scoped face encodings
_SESSION_FACE_REGISTRY: dict[UUID, dict] = {}


def register_candidate_face(
    interview_id: UUID,
    data: FaceRegistrationRequest,
) -> FaceRegistrationResponse:
    now = data.captured_at or datetime.now(timezone.utc)
    _SESSION_FACE_REGISTRY[interview_id] = {
        "encoding": data.encoding,
        "registered_at": now,
        "metadata": data.metadata,
    }
    return FaceRegistrationResponse(
        registered=True,
        interview_id=interview_id,
        vector_dimension=len(data.encoding),
        registered_at=now,
    )


def get_session_face_encoding(interview_id: UUID) -> list[float] | None:
    session_data = _SESSION_FACE_REGISTRY.get(interview_id)
    return session_data["encoding"] if session_data else None


def clear_session_face(interview_id: UUID) -> None:
    _SESSION_FACE_REGISTRY.pop(interview_id, None)

