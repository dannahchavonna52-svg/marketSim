from datetime import datetime
from typing import Dict

from sqlalchemy.orm import Session

import crud
from models import Position, Trade, User


def buy(db: Session, user: User, symbol: str, name: str, asset_type: str, price: float, quantity: float, fee: float = 0.0) -> Dict:
    account = crud.get_or_create_account(db, user)
    symbol = crud.normalize_symbol(symbol)
    asset_type = asset_type.lower()
    amount = price * quantity
    total_cost = amount + fee
    if account.cash < total_cost:
        raise ValueError(f"现金不足：需要 {total_cost:.2f} 元，当前现金 {account.cash:.2f} 元")

    position = (
        db.query(Position)
        .filter(Position.user_id == user.id, Position.symbol == symbol, Position.asset_type == asset_type)
        .first()
    )
    if position:
        old_cost = position.avg_cost * position.quantity
        new_quantity = position.quantity + quantity
        position.avg_cost = (old_cost + amount + fee) / new_quantity
        position.quantity = new_quantity
        position.name = name
        position.current_price = price
    else:
        position = Position(
            user_id=user.id,
            symbol=symbol,
            name=name,
            asset_type=asset_type,
            quantity=quantity,
            avg_cost=(amount + fee) / quantity,
            current_price=price,
            market_value=amount,
            profit=0.0,
            profit_rate=0.0,
        )
        db.add(position)

    crud.update_position_price(position, price)
    account.cash -= total_cost
    account.updated_at = datetime.utcnow()

    trade = Trade(
        user_id=user.id,
        symbol=symbol,
        name=name,
        asset_type=asset_type,
        side="buy",
        price=price,
        quantity=quantity,
        amount=amount,
        fee=fee,
        profit=0.0,
    )
    db.add(trade)
    db.commit()
    db.refresh(position)
    db.refresh(trade)
    db.refresh(account)
    return {"account": account, "position": position, "trade": trade}


def sell(db: Session, user: User, symbol: str, asset_type: str, price: float, quantity: float, fee: float = 0.0) -> Dict:
    account = crud.get_or_create_account(db, user)
    symbol = crud.normalize_symbol(symbol)
    asset_type = asset_type.lower()
    position = (
        db.query(Position)
        .filter(Position.user_id == user.id, Position.symbol == symbol, Position.asset_type == asset_type)
        .first()
    )
    if not position:
        raise ValueError("没有该标的持仓，无法卖出")
    if quantity > position.quantity:
        raise ValueError(f"卖出数量超过持仓：当前持仓 {position.quantity:.4f}")

    amount = price * quantity
    profit = (price - position.avg_cost) * quantity - fee
    account.cash += amount - fee
    account.updated_at = datetime.utcnow()

    trade = Trade(
        user_id=user.id,
        symbol=symbol,
        name=position.name,
        asset_type=asset_type,
        side="sell",
        price=price,
        quantity=quantity,
        amount=amount,
        fee=fee,
        profit=profit,
    )
    db.add(trade)

    position.quantity -= quantity
    if position.quantity <= 1e-8:
        db.delete(position)
        position = None
    else:
        crud.update_position_price(position, price)

    db.commit()
    db.refresh(trade)
    db.refresh(account)
    return {"account": account, "position": position, "trade": trade}
