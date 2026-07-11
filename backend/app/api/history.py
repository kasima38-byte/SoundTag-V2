from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import require_user
from app.models.models import RecognitionHistory, User
from app.schemas.schemas import HistoryItem, HistoryListResponse

router = APIRouter(prefix="/history", tags=["history"])


@router.get("", response_model=HistoryListResponse)
async def get_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    matched_only: bool = Query(False, description="Only return successful recognitions"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_user),
):
    """
    Return the authenticated user's searchable recognition history,
    most recent first.
    """
    base_query = select(RecognitionHistory).where(
        RecognitionHistory.user_id == current_user.id
    )
    if matched_only:
        base_query = base_query.where(RecognitionHistory.matched.is_(True))

    count_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total = count_result.scalar_one()

    result = await db.execute(
        base_query.options(selectinload(RecognitionHistory.song))
        .order_by(RecognitionHistory.recognized_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = result.scalars().all()

    return HistoryListResponse(
        items=[HistoryItem.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )
