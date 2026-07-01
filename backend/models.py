from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text, UniqueConstraint

from database import Base


def utc_now():
    return datetime.utcnow()


class Account(Base):
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    cash = Column(Float, nullable=False, default=100000.0)
    initial_cash = Column(Float, nullable=False, default=100000.0)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), nullable=False, unique=True, index=True)
    password_hash = Column(String(256), nullable=False)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    token = Column(String(128), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=utc_now)
    expires_at = Column(DateTime, nullable=False)


class Watchlist(Base):
    __tablename__ = "watchlist"
    __table_args__ = (UniqueConstraint("user_id", "symbol", "asset_type", name="uq_watch_user_symbol_type"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(32), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    asset_type = Column(String(16), nullable=False, index=True)
    note = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now)


class Position(Base):
    __tablename__ = "positions"
    __table_args__ = (UniqueConstraint("user_id", "symbol", "asset_type", name="uq_position_user_symbol_type"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(32), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    asset_type = Column(String(16), nullable=False, index=True)
    quantity = Column(Float, nullable=False)
    avg_cost = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    market_value = Column(Float, nullable=False)
    profit = Column(Float, nullable=False, default=0.0)
    profit_rate = Column(Float, nullable=False, default=0.0)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(32), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    asset_type = Column(String(16), nullable=False, index=True)
    side = Column(String(8), nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    fee = Column(Float, nullable=False, default=0.0)
    profit = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=utc_now, index=True)


class FundBasic(Base):
    __tablename__ = "fund_basic"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(32), nullable=False, unique=True, index=True)
    name = Column(String(120), nullable=False)
    fund_type = Column(String(64), default="")
    manager = Column(String(120), default="")
    company = Column(String(120), default="")
    latest_nav = Column(Float, default=0.0)
    estimated_nav = Column(Float, default=0.0)
    daily_change = Column(Float, default=0.0)
    week_return = Column(Float, default=0.0)
    month_return = Column(Float, default=0.0)
    three_month_return = Column(Float, default=0.0)
    six_month_return = Column(Float, default=0.0)
    year_return = Column(Float, default=0.0)
    three_year_return = Column(Float, default=0.0)
    max_drawdown = Column(Float, default=0.0)
    sharpe_ratio = Column(Float, default=0.0)
    fund_size = Column(Float, default=0.0)
    inception_date = Column(String(32), default="")
    industries = Column(Text, default="")
    top_stocks = Column(Text, default="")
    fee = Column(String(64), default="")
    risk_level = Column(String(32), default="")
    peer_rank = Column(String(64), default="")
    data_source = Column(String(64), default="")
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class FundNavHistory(Base):
    __tablename__ = "fund_nav_history"
    __table_args__ = (UniqueConstraint("symbol", "nav_date", name="uq_fund_nav_symbol_date"),)

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(32), nullable=False, index=True)
    nav_date = Column(String(32), nullable=False, index=True)
    nav = Column(Float, nullable=False)
    change_percent = Column(Float, default=0.0)


class FundScore(Base):
    __tablename__ = "fund_scores"
    __table_args__ = (UniqueConstraint("symbol", name="uq_fund_score_symbol"),)

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(32), nullable=False, index=True)
    total_score = Column(Float, nullable=False)
    grade = Column(String(32), nullable=False)
    suitability = Column(String(120), default="")
    action = Column(String(64), default="")
    buy_reason = Column(Text, default="")
    risk_note = Column(Text, default="")
    buy_range = Column(String(64), default="")
    take_profit_range = Column(String(64), default="")
    stop_loss_range = Column(String(64), default="")
    holding_period = Column(String(64), default="")
    detail_json = Column(Text, default="")
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(240), nullable=False)
    source = Column(String(120), default="")
    published_at = Column(String(64), default="")
    summary = Column(Text, default="")
    impact_direction = Column(String(64), default="")
    positive_types = Column(Text, default="")
    negative_types = Column(Text, default="")
    impact_level = Column(String(16), default="中")
    plain_explanation = Column(Text, default="")
    operation_reference = Column(Text, default="")
    raw_url = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now, index=True)


class NewsFundLink(Base):
    __tablename__ = "news_fund_links"

    id = Column(Integer, primary_key=True, index=True)
    news_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(32), nullable=False, index=True)
    reason = Column(Text, default="")
    effect = Column(String(32), default="观察")
    plain_explanation = Column(Text, default="")


class DailyOperationSetting(Base):
    __tablename__ = "daily_operation_settings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    enabled = Column(Integer, nullable=False, default=0)
    run_time = Column(String(8), nullable=False, default="02:55")
    email = Column(String(160), default="")
    last_run_date = Column(String(16), default="")
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class DailyOperationLog(Base):
    __tablename__ = "daily_operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    run_at = Column(DateTime, default=utc_now, index=True)
    run_date = Column(String(16), nullable=False, index=True)
    summary = Column(Text, default="")
    detail_json = Column(Text, default="")
    email = Column(String(160), default="")
    email_status = Column(String(32), default="")
    email_error = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now, index=True)


class AdvisorSimAccount(Base):
    __tablename__ = "advisor_sim_accounts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, unique=True, index=True)
    cash = Column(Float, nullable=False, default=100000.0)
    initial_cash = Column(Float, nullable=False, default=100000.0)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class AdvisorSimPosition(Base):
    __tablename__ = "advisor_sim_positions"
    __table_args__ = (UniqueConstraint("user_id", "symbol", name="uq_advisor_position_user_symbol"),)

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(32), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    quantity = Column(Float, nullable=False, default=0.0)
    avg_cost = Column(Float, nullable=False, default=0.0)
    current_nav = Column(Float, nullable=False, default=0.0)
    market_value = Column(Float, nullable=False, default=0.0)
    profit = Column(Float, nullable=False, default=0.0)
    profit_rate = Column(Float, nullable=False, default=0.0)
    last_action = Column(String(64), default="")
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)


class AdvisorSimTrade(Base):
    __tablename__ = "advisor_sim_trades"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(32), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    side = Column(String(16), nullable=False)
    price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    amount = Column(Float, nullable=False)
    profit = Column(Float, nullable=False, default=0.0)
    reason = Column(Text, default="")
    evidence_json = Column(Text, default="")
    signal_json = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now, index=True)


class AdvisorSimSnapshot(Base):
    __tablename__ = "advisor_sim_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    total_asset = Column(Float, nullable=False)
    cash = Column(Float, nullable=False)
    market_value = Column(Float, nullable=False)
    profit = Column(Float, nullable=False)
    profit_rate = Column(Float, nullable=False)
    summary = Column(Text, default="")
    created_at = Column(DateTime, default=utc_now, index=True)
