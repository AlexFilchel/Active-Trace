from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db


router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    database_status = "up"

    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        database_status = "down"

    return {"status": "ok", "database": database_status}
