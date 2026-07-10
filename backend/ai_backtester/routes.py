from __future__ import annotations

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException

import auth
from models import User

from .service import run_ai_backtest_for_fund


router = APIRouter(prefix="/api/ai-backtest", tags=["ai-backtest"])


class AiBacktestRequest(BaseModel):
    fund_code: str = Field(..., pattern=r"^\d{6}$")
    start_date: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    end_date: str | None = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    initial_cash: float = Field(100000.0, gt=0)
    trade_amount: float = Field(10000.0, gt=0)
    max_position_ratio: float = Field(0.8, gt=0, le=1)
    buy_fee_rate: float = Field(0.001, ge=0, lt=1)
    sell_fee_rate: float = Field(0.005, ge=0, lt=1)
    refresh: bool = False


@router.post("/run")
def run_ai_backtest(payload: AiBacktestRequest, current_user: User = Depends(auth.get_current_user)):
    """Run a simulated fund backtest.

    This endpoint is safe: it does not mutate the user's simulated account and
    never places real trades.
    """

    try:
        data = run_ai_backtest_for_fund(
            fund_code=payload.fund_code,
            start_date=payload.start_date,
            end_date=payload.end_date,
            initial_cash=payload.initial_cash,
            trade_amount=payload.trade_amount,
            max_position_ratio=payload.max_position_ratio,
            buy_fee_rate=payload.buy_fee_rate,
            sell_fee_rate=payload.sell_fee_rate,
            refresh=payload.refresh,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"success": True, "message": "AI 基金回测完成", "data": data}
