from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


AssetType = Literal["stock", "etf", "fund", "index"]


class WatchlistCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=120)
    asset_type: AssetType
    note: Optional[str] = ""


class AuthRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)


class WatchlistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    name: str
    asset_type: str
    note: str = ""
    created_at: datetime


class BuyRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    name: str = Field(..., min_length=1, max_length=120)
    asset_type: AssetType
    price: float = Field(..., gt=0)
    quantity: float = Field(..., gt=0)
    fee: float = Field(0.0, ge=0)


class SellRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    asset_type: AssetType
    price: float = Field(..., gt=0)
    quantity: float = Field(..., gt=0)
    fee: float = Field(0.0, ge=0)


class SimAccountRequest(BaseModel):
    initial_cash: float = Field(..., gt=0)


class DailyOperationSettingsRequest(BaseModel):
    enabled: bool = False
    run_time: str = Field("02:55", pattern=r"^\d{2}:\d{2}$")
    email: Optional[str] = Field("", max_length=160)
