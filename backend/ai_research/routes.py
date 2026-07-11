from fastapi import APIRouter, Depends, HTTPException

import auth
from models import User

from .service import run_fund_research


router = APIRouter(prefix="/api/ai-research", tags=["ai-research"])


@router.get("/{fund_code}")
def analyze_fund(
    fund_code: str,
    refresh: bool = False,
    current_user: User = Depends(auth.get_current_user),
):
    try:
        result = run_fund_research(fund_code, refresh=refresh)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"success": True, "message": "多 Agent 基金分析完成", "data": result}

