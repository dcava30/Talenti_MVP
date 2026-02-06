from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models import Application, Interview, InterviewScore, ScoreDimension, TranscriptSegment, User
from app.schemas.applications import ApplicationResponse
from app.schemas.interviews import (
    InterviewCreate,
    InterviewReportResponse,
    InterviewResponse,
    InterviewScoreResponse,
    InterviewScoreSave,
    InterviewUpdate,
    ScoreDimensionResponse,
    TranscriptSegmentCreate,
    TranscriptSegmentResponse,
)

router = APIRouter(prefix="/api/v1/interviews", tags=["interviews"])


def _build_application_response(application: Application | None) -> ApplicationResponse | None:
    if not application:
        return None
    return ApplicationResponse(
        id=application.id,
        job_role_id=application.job_role_id,
        candidate_profile_id=application.candidate_profile_id,
        status=application.status,
        source=application.source,
        cover_letter=application.cover_letter,
        created_at=application.created_at,
        updated_at=application.updated_at,
    )


def _build_interview_response(
    interview: Interview, application: Application | None = None
) -> InterviewResponse:
    return InterviewResponse(
        id=interview.id,
        application_id=interview.application_id,
        status=interview.status,
        scheduled_at=interview.scheduled_at,
        started_at=interview.started_at,
        ended_at=interview.ended_at,
        duration_seconds=interview.duration_seconds,
        recording_url=interview.recording_url,
        transcript_status=interview.transcript_status,
        summary=interview.summary,
        created_at=interview.created_at,
        updated_at=interview.updated_at,
        application=_build_application_response(application),
    )


@router.post("", response_model=InterviewResponse)
def create_interview(
    payload: InterviewCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InterviewResponse:
    interview = Interview(
        application_id=payload.application_id,
        status=payload.status or "pending",
        scheduled_at=payload.scheduled_at,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    return _build_interview_response(interview, db.get(Application, interview.application_id))


@router.get("/active", response_model=InterviewResponse | None)
def get_active_interview(
    application_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InterviewResponse | None:
    interview = (
        db.query(Interview)
        .filter(
            Interview.application_id == application_id,
            Interview.status.in_(["pending", "in_progress"]),
        )
        .order_by(Interview.created_at.desc())
        .first()
    )
    if not interview:
        return None
    return _build_interview_response(interview, db.get(Application, interview.application_id))


@router.get("/{interview_id}", response_model=InterviewResponse)
def get_interview(
    interview_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InterviewResponse:
    interview = db.get(Interview, interview_id)
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    return _build_interview_response(interview, db.get(Application, interview.application_id))


@router.patch("/{interview_id}", response_model=InterviewResponse)
def update_interview(
    interview_id: str,
    payload: InterviewUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InterviewResponse:
    interview = db.get(Interview, interview_id)
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    for field in (
        "status",
        "scheduled_at",
        "started_at",
        "ended_at",
        "duration_seconds",
        "recording_url",
        "transcript_status",
        "summary",
    ):
        value = getattr(payload, field)
        if value is not None:
            setattr(interview, field, value)
    interview.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(interview)
    return _build_interview_response(interview, db.get(Application, interview.application_id))


@router.get("/{interview_id}/transcripts", response_model=list[TranscriptSegmentResponse])
def list_transcripts(
    interview_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TranscriptSegmentResponse]:
    segments = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.interview_id == interview_id)
        .order_by(TranscriptSegment.sequence.asc())
        .all()
    )
    return [
        TranscriptSegmentResponse(
            id=segment.id,
            interview_id=segment.interview_id,
            sequence=segment.sequence,
            speaker=segment.speaker,
            content=segment.content,
            created_at=segment.created_at,
            start_time_ms=None,
            end_time_ms=None,
        )
        for segment in segments
    ]


@router.post("/{interview_id}/transcripts", response_model=TranscriptSegmentResponse)
def create_transcript(
    interview_id: str,
    payload: TranscriptSegmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> TranscriptSegmentResponse:
    interview = db.get(Interview, interview_id)
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    last_sequence = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.interview_id == interview_id)
        .order_by(TranscriptSegment.sequence.desc())
        .first()
    )
    sequence = (last_sequence.sequence + 1) if last_sequence else 1
    segment = TranscriptSegment(
        interview_id=interview_id,
        sequence=sequence,
        speaker=payload.speaker,
        content=payload.content,
        created_at=datetime.utcnow(),
    )
    db.add(segment)
    db.commit()
    db.refresh(segment)
    return TranscriptSegmentResponse(
        id=segment.id,
        interview_id=segment.interview_id,
        sequence=segment.sequence,
        speaker=segment.speaker,
        content=segment.content,
        created_at=segment.created_at,
        start_time_ms=payload.start_time_ms,
        end_time_ms=payload.end_time_ms,
    )


@router.get("/{interview_id}/score", response_model=InterviewScoreResponse | None)
def get_score(
    interview_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InterviewScoreResponse | None:
    score = (
        db.query(InterviewScore).filter(InterviewScore.interview_id == interview_id).first()
    )
    if not score:
        return None
    return InterviewScoreResponse(
        id=score.id,
        interview_id=score.interview_id,
        overall_score=score.overall_score,
        summary=score.summary,
        recommendation=score.recommendation,
        created_at=score.created_at,
    )


@router.get("/{interview_id}/dimensions", response_model=list[ScoreDimensionResponse])
def list_dimensions(
    interview_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[ScoreDimensionResponse]:
    dimensions = (
        db.query(ScoreDimension)
        .filter(ScoreDimension.interview_id == interview_id)
        .order_by(ScoreDimension.created_at.asc())
        .all()
    )
    return [
        ScoreDimensionResponse(
            id=dimension.id,
            interview_id=dimension.interview_id,
            name=dimension.name,
            score=dimension.score,
            rationale=dimension.rationale,
            created_at=dimension.created_at,
        )
        for dimension in dimensions
    ]


@router.post("/{interview_id}/scores", response_model=InterviewScoreResponse)
def save_scores(
    interview_id: str,
    payload: InterviewScoreSave,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InterviewScoreResponse:
    interview = db.get(Interview, interview_id)
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    score = (
        db.query(InterviewScore).filter(InterviewScore.interview_id == interview_id).first()
    )
    if score:
        score.overall_score = payload.overall_score
        score.summary = payload.narrative_summary
        score.recommendation = payload.candidate_feedback
    else:
        score = InterviewScore(
            interview_id=interview_id,
            overall_score=payload.overall_score,
            summary=payload.narrative_summary,
            recommendation=payload.candidate_feedback,
            created_at=datetime.utcnow(),
        )
        db.add(score)
    db.query(ScoreDimension).filter(ScoreDimension.interview_id == interview_id).delete()
    for dimension in payload.dimensions:
        db.add(
            ScoreDimension(
                interview_id=interview_id,
                name=dimension.name,
                score=dimension.score,
                rationale=dimension.rationale,
                created_at=datetime.utcnow(),
            )
        )
    db.commit()
    db.refresh(score)
    return InterviewScoreResponse(
        id=score.id,
        interview_id=score.interview_id,
        overall_score=score.overall_score,
        summary=score.summary,
        recommendation=score.recommendation,
        created_at=score.created_at,
    )


@router.get("/{interview_id}/report", response_model=InterviewReportResponse)
def get_report(
    interview_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> InterviewReportResponse:
    interview = db.get(Interview, interview_id)
    if not interview:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found")
    application = db.get(Application, interview.application_id)
    score = (
        db.query(InterviewScore).filter(InterviewScore.interview_id == interview_id).first()
    )
    dimensions = (
        db.query(ScoreDimension)
        .filter(ScoreDimension.interview_id == interview_id)
        .order_by(ScoreDimension.created_at.asc())
        .all()
    )
    transcripts = (
        db.query(TranscriptSegment)
        .filter(TranscriptSegment.interview_id == interview_id)
        .order_by(TranscriptSegment.sequence.asc())
        .all()
    )
    return InterviewReportResponse(
        interview=_build_interview_response(interview, application),
        score=(
            InterviewScoreResponse(
                id=score.id,
                interview_id=score.interview_id,
                overall_score=score.overall_score,
                summary=score.summary,
                recommendation=score.recommendation,
                created_at=score.created_at,
            )
            if score
            else None
        ),
        dimensions=[
            ScoreDimensionResponse(
                id=dimension.id,
                interview_id=dimension.interview_id,
                name=dimension.name,
                score=dimension.score,
                rationale=dimension.rationale,
                created_at=dimension.created_at,
            )
            for dimension in dimensions
        ],
        transcripts=[
            TranscriptSegmentResponse(
                id=segment.id,
                interview_id=segment.interview_id,
                sequence=segment.sequence,
                speaker=segment.speaker,
                content=segment.content,
                created_at=segment.created_at,
                start_time_ms=None,
                end_time_ms=None,
            )
            for segment in transcripts
        ],
    )
