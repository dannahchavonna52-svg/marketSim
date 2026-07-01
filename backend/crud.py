from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from models import Account, Position, Trade, User, Watchlist


def normalize_symbol(symbol: str) -> str:
    return str(symbol).strip().upper()


def get_or_create_account(db: Session, user: User) -> Account:
    account = db.query(Account).filter(Account.user_id == user.id).order_by(Account.id.asc()).first()
    if account:
        return account
    account = Account(user_id=user.id, cash=100000.0, initial_cash=100000.0)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


def add_watchlist_item(db: Session, user: User, symbol: str, name: str, asset_type: str, note: str = "") -> Watchlist:
    symbol = normalize_symbol(symbol)
    asset_type = asset_type.lower()
    existing = (
        db.query(Watchlist)
        .filter(Watchlist.user_id == user.id, Watchlist.symbol == symbol, Watchlist.asset_type == asset_type)
        .first()
    )
    if existing:
        raise ValueError("该标的已在自选列表中")
    item = Watchlist(user_id=user.id, symbol=symbol, name=name.strip(), asset_type=asset_type, note=note or "")
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def list_watchlist(db: Session, user: User) -> List[Watchlist]:
    return db.query(Watchlist).filter(Watchlist.user_id == user.id).order_by(Watchlist.created_at.desc()).all()


def delete_watchlist_item(db: Session, user: User, item_id: int) -> bool:
    item = db.query(Watchlist).filter(Watchlist.id == item_id, Watchlist.user_id == user.id).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


def list_positions(db: Session, user: User) -> List[Position]:
    return db.query(Position).filter(Position.user_id == user.id).order_by(Position.market_value.desc()).all()


def list_trades(db: Session, user: User, limit: Optional[int] = None) -> List[Trade]:
    query = db.query(Trade).filter(Trade.user_id == user.id).order_by(Trade.created_at.desc(), Trade.id.desc())
    if limit:
        query = query.limit(limit)
    return query.all()


def serialize_account(account: Account, positions: List[Position]) -> Dict:
    holding_value = sum(p.market_value for p in positions)
    total_asset = account.cash + holding_value
    total_profit = total_asset - account.initial_cash
    total_profit_rate = (total_profit / account.initial_cash * 100) if account.initial_cash else 0
    return {
        "id": account.id,
        "cash": round(account.cash, 2),
        "initial_cash": round(account.initial_cash, 2),
        "holding_market_value": round(holding_value, 2),
        "total_asset": round(total_asset, 2),
        "total_profit": round(total_profit, 2),
        "total_profit_rate": round(total_profit_rate, 2),
        "created_at": account.created_at,
        "updated_at": account.updated_at,
    }


def serialize_position(position: Position) -> Dict:
    return {
        "id": position.id,
        "symbol": position.symbol,
        "name": position.name,
        "asset_type": position.asset_type,
        "quantity": round(position.quantity, 4),
        "avg_cost": round(position.avg_cost, 4),
        "current_price": round(position.current_price, 4),
        "market_value": round(position.market_value, 2),
        "profit": round(position.profit, 2),
        "profit_rate": round(position.profit_rate, 2),
        "updated_at": position.updated_at,
    }


def serialize_trade(trade: Trade) -> Dict:
    return {
        "id": trade.id,
        "symbol": trade.symbol,
        "name": trade.name,
        "asset_type": trade.asset_type,
        "side": trade.side,
        "price": round(trade.price, 4),
        "quantity": round(trade.quantity, 4),
        "amount": round(trade.amount, 2),
        "fee": round(trade.fee, 2),
        "profit": round(trade.profit, 2),
        "created_at": trade.created_at,
    }


def update_position_price(position: Position, price: float):
    position.current_price = price
    position.market_value = position.quantity * price
    position.profit = (price - position.avg_cost) * position.quantity
    position.profit_rate = ((price - position.avg_cost) / position.avg_cost * 100) if position.avg_cost else 0
    position.updated_at = datetime.utcnow()
