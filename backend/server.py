"""Main FastAPI server for RSI & MA Tracker."""
from __future__ import annotations

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

from data_source import fetch_history, validate_symbol
from email_service import build_alert_email, send_email
from indicators import detect_crossover, ma_position, moving_average, rsi, rsi_signal

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

SCAN_HOUR = int(os.environ.get("DAILY_SCAN_HOUR_UTC", "20"))
SCAN_MINUTE = int(os.environ.get("DAILY_SCAN_MINUTE_UTC", "0"))

# ---------- Models ----------

DEFAULT_SETTINGS = {
    "rsi_period": 14,
    "rsi_lower": 30.0,
    "rsi_upper": 70.0,
    "ma_short": 50,
    "ma_long": 200,
    "alert_rsi_low": True,
    "alert_rsi_high": True,
    "alert_golden_cross": True,
    "alert_death_cross": True,
}


class GlobalSettings(BaseModel):
    model_config = ConfigDict(extra="ignore")
    rsi_period: int = 14
    rsi_lower: float = 30.0
    rsi_upper: float = 70.0
    ma_short: int = 50
    ma_long: int = 200
    ma_type: str = "sma"  # "sma" or "ema"
    alert_rsi_low: bool = True
    alert_rsi_high: bool = True
    alert_golden_cross: bool = True
    alert_death_cross: bool = True
    alert_combo: bool = True
    notification_email: str = ""
    push_enabled: bool = False


class TickerCreate(BaseModel):
    symbol: str


class TickerOverride(BaseModel):
    """Per-ticker settings; any None falls back to global."""
    rsi_period: Optional[int] = None
    rsi_lower: Optional[float] = None
    rsi_upper: Optional[float] = None
    ma_short: Optional[int] = None
    ma_long: Optional[int] = None
    ma_type: Optional[str] = None
    alert_rsi_low: Optional[bool] = None
    alert_rsi_high: Optional[bool] = None
    alert_golden_cross: Optional[bool] = None
    alert_death_cross: Optional[bool] = None
    alert_combo: Optional[bool] = None


class Ticker(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    name: str = ""
    overrides: TickerOverride = Field(default_factory=TickerOverride)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Alert(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    symbol: str
    type: str  # oversold | overbought | golden_cross | death_cross
    value: Optional[float] = None
    price: Optional[float] = None
    triggered_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    email_sent: bool = False


# ---------- Helpers ----------

async def get_global_settings() -> GlobalSettings:
    doc = await db.settings.find_one({"_id": "global"}, {"_id": 0})
    if not doc:
        gs = GlobalSettings()
        await db.settings.insert_one({"_id": "global", **gs.model_dump()})
        return gs
    return GlobalSettings(**doc)


def merge_settings(gs: GlobalSettings, override: TickerOverride) -> dict:
    base = gs.model_dump()
    for k, v in override.model_dump().items():
        if v is not None:
            base[k] = v
    return base


async def compute_ticker_state(symbol: str, overrides: TickerOverride, gs: GlobalSettings) -> Optional[dict]:
    s = merge_settings(gs, overrides)
    data = await asyncio.to_thread(fetch_history, symbol, "1y")
    if not data:
        return None
    closes = data["closes"]
    rsi_values = rsi(closes, s["rsi_period"])
    ma_type = s.get("ma_type", "sma")
    ma_short_arr = moving_average(closes, s["ma_short"], ma_type)
    ma_long_arr = moving_average(closes, s["ma_long"], ma_type)
    cross = detect_crossover(ma_short_arr, ma_long_arr)
    position = ma_position(ma_short_arr, ma_long_arr)
    rsi_last = rsi_values[-1] if rsi_values else None
    sig = rsi_signal(rsi_last, s["rsi_lower"], s["rsi_upper"])
    spark = closes[-30:] if len(closes) >= 30 else closes
    return {
        "symbol": data["symbol"],
        "name": data["name"],
        "currency": data["currency"],
        "last_price": data["last_price"],
        "prev_close": closes[-2] if len(closes) > 1 else closes[-1],
        "rsi": rsi_last,
        "rsi_signal": sig,
        "ma_short_value": ma_short_arr[-1],
        "ma_long_value": ma_long_arr[-1],
        "ma_short_period": s["ma_short"],
        "ma_long_period": s["ma_long"],
        "ma_type": ma_type,
        "ma_position": position,
        "crossover": cross,
        "spark": spark,
        "settings": {
            "rsi_period": s["rsi_period"],
            "rsi_lower": s["rsi_lower"],
            "rsi_upper": s["rsi_upper"],
            "ma_short": s["ma_short"],
            "ma_long": s["ma_long"],
            "ma_type": ma_type,
            "alert_rsi_low": s["alert_rsi_low"],
            "alert_rsi_high": s["alert_rsi_high"],
            "alert_golden_cross": s["alert_golden_cross"],
            "alert_death_cross": s["alert_death_cross"],
            "alert_combo": s.get("alert_combo", True),
        },
    }


async def run_scan() -> dict:
    """Scan all tickers, detect signals, store alerts, send email."""
    logger.info("Starting scan...")
    gs = await get_global_settings()
    tickers = await db.tickers.find({}, {"_id": 0}).to_list(1000)
    triggered: List[Alert] = []
    states: List[dict] = []
    for t in tickers:
        symbol = t["symbol"]
        overrides = TickerOverride(**t.get("overrides", {}))
        state = await compute_ticker_state(symbol, overrides, gs)
        if not state:
            continue
        states.append(state)
        s = state["settings"]
        per_ticker: List[Alert] = []
        rsi_kind = None  # "oversold" | "overbought"
        cross_kind = None  # "golden_cross" | "death_cross"
        if state["rsi_signal"] == "oversold" and s["alert_rsi_low"]:
            per_ticker.append(Alert(symbol=symbol, type="oversold", value=state["rsi"], price=state["last_price"]))
            rsi_kind = "oversold"
        if state["rsi_signal"] == "overbought" and s["alert_rsi_high"]:
            per_ticker.append(Alert(symbol=symbol, type="overbought", value=state["rsi"], price=state["last_price"]))
            rsi_kind = "overbought"
        if state["crossover"] == "golden_cross" and s["alert_golden_cross"]:
            per_ticker.append(Alert(symbol=symbol, type="golden_cross", value=state["rsi"], price=state["last_price"]))
            cross_kind = "golden_cross"
        if state["crossover"] == "death_cross" and s["alert_death_cross"]:
            per_ticker.append(Alert(symbol=symbol, type="death_cross", value=state["rsi"], price=state["last_price"]))
            cross_kind = "death_cross"

        # Combo detection
        if s.get("alert_combo", True) and rsi_kind and cross_kind:
            bullish = rsi_kind == "oversold" and cross_kind == "golden_cross"
            bearish = rsi_kind == "overbought" and cross_kind == "death_cross"
            # also catch mixed but powerful signals: oversold+death_cross (capitulation) or overbought+golden_cross (breakout-overbought)
            if bullish:
                combo_type = "combo_bullish"
            elif bearish:
                combo_type = "combo_bearish"
            else:
                combo_type = "combo_bullish" if cross_kind == "golden_cross" else "combo_bearish"
            per_ticker.append(Alert(symbol=symbol, type=combo_type, value=state["rsi"], price=state["last_price"]))

        triggered.extend(per_ticker)

    # Persist alerts and send emails
    for alert in triggered:
        details = {
            "Symbol": alert.symbol,
            "Type": alert.type.replace("_", " ").title(),
            "Price": f"{alert.price:.2f}" if alert.price is not None else "—",
            "RSI": f"{alert.value:.2f}" if alert.value is not None else "—",
            "Time (UTC)": alert.triggered_at.strftime("%Y-%m-%d %H:%M"),
        }
        sent = False
        if gs.notification_email:
            subject, html = build_alert_email(alert.type, alert.symbol, details)
            sent, _msg = await asyncio.to_thread(send_email, gs.notification_email, subject, html)
        alert.email_sent = sent
        doc = alert.model_dump()
        doc["triggered_at"] = doc["triggered_at"].isoformat()
        await db.alerts.insert_one(doc)

    last_run = datetime.now(timezone.utc).isoformat()
    await db.meta.update_one(
        {"_id": "scan"},
        {"$set": {"last_run": last_run, "tickers_scanned": len(states), "alerts_triggered": len(triggered)}},
        upsert=True,
    )
    logger.info(f"Scan complete. Tickers={len(states)} Alerts={len(triggered)}")
    return {"last_run": last_run, "tickers_scanned": len(states), "alerts_triggered": len(triggered)}


# ---------- App + Scheduler ----------

scheduler: Optional[AsyncIOScheduler] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler
    # Seed default ticker
    if await db.tickers.count_documents({}) == 0:
        seed = Ticker(symbol="VT", name="Vanguard Total World Stock ETF")
        doc = seed.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await db.tickers.insert_one(doc)
    # Ensure global settings exist
    await get_global_settings()

    scheduler = AsyncIOScheduler(timezone="UTC")
    scheduler.add_job(
        run_scan,
        trigger=CronTrigger(hour=SCAN_HOUR, minute=SCAN_MINUTE, timezone="UTC"),
        id="daily_scan",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started — daily scan at {SCAN_HOUR:02d}:{SCAN_MINUTE:02d} UTC")
    yield
    if scheduler:
        scheduler.shutdown(wait=False)
    client.close()


app = FastAPI(lifespan=lifespan)
api = APIRouter(prefix="/api")


# ---------- Routes ----------

@api.get("/")
async def root():
    return {"service": "rsi-ma-tracker", "status": "ok"}


@api.get("/tickers")
async def list_tickers():
    gs = await get_global_settings()
    tickers = await db.tickers.find({}, {"_id": 0}).sort("created_at", 1).to_list(1000)
    results = []
    for t in tickers:
        overrides = TickerOverride(**t.get("overrides", {}))
        state = await compute_ticker_state(t["symbol"], overrides, gs)
        if state:
            state["id"] = t["id"]
            state["overrides"] = t.get("overrides", {})
            # Update stored name if we have a better one
            if state.get("name") and state["name"] != t.get("name"):
                await db.tickers.update_one({"id": t["id"]}, {"$set": {"name": state["name"]}})
            results.append(state)
        else:
            results.append({
                "id": t["id"],
                "symbol": t["symbol"],
                "name": t.get("name", t["symbol"]),
                "error": "Failed to fetch data",
                "overrides": t.get("overrides", {}),
            })
    return results


@api.post("/tickers")
async def add_ticker(payload: TickerCreate):
    symbol = payload.symbol.strip().upper()
    if not symbol:
        raise HTTPException(400, "Symbol required")
    existing = await db.tickers.find_one({"symbol": symbol})
    if existing:
        raise HTTPException(409, f"{symbol} already tracked")
    valid = await asyncio.to_thread(validate_symbol, symbol)
    if not valid:
        raise HTTPException(404, f"Symbol {symbol} not found on Yahoo Finance")
    ticker = Ticker(symbol=symbol)
    doc = ticker.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    await db.tickers.insert_one(doc)
    return {"id": ticker.id, "symbol": symbol}


@api.delete("/tickers/{symbol}")
async def delete_ticker(symbol: str):
    result = await db.tickers.delete_one({"symbol": symbol.upper()})
    if result.deleted_count == 0:
        raise HTTPException(404, "Ticker not found")
    return {"deleted": symbol.upper()}


@api.put("/tickers/{symbol}/overrides")
async def update_ticker_overrides(symbol: str, payload: TickerOverride):
    result = await db.tickers.update_one(
        {"symbol": symbol.upper()},
        {"$set": {"overrides": payload.model_dump()}},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Ticker not found")
    return {"ok": True}


@api.get("/settings")
async def get_settings():
    return (await get_global_settings()).model_dump()


@api.put("/settings")
async def update_settings(payload: GlobalSettings):
    await db.settings.update_one(
        {"_id": "global"},
        {"$set": payload.model_dump()},
        upsert=True,
    )
    return payload.model_dump()


@api.get("/alerts")
async def get_alerts(limit: int = 50):
    alerts = await db.alerts.find({}, {"_id": 0}).sort("triggered_at", -1).to_list(limit)
    return alerts


@api.delete("/alerts")
async def clear_alerts():
    result = await db.alerts.delete_many({})
    return {"deleted": result.deleted_count}


@api.get("/scan/status")
async def scan_status():
    meta = await db.meta.find_one({"_id": "scan"}, {"_id": 0}) or {}
    next_run = None
    if scheduler:
        job = scheduler.get_job("daily_scan")
        if job and job.next_run_time:
            next_run = job.next_run_time.astimezone(timezone.utc).isoformat()
    return {
        "last_run": meta.get("last_run"),
        "next_run": next_run,
        "tickers_scanned": meta.get("tickers_scanned", 0),
        "alerts_triggered": meta.get("alerts_triggered", 0),
        "scan_hour_utc": SCAN_HOUR,
        "scan_minute_utc": SCAN_MINUTE,
    }


@api.post("/scan/run")
async def trigger_scan():
    result = await run_scan()
    return result


@api.post("/notifications/test")
async def test_notification():
    gs = await get_global_settings()
    if not gs.notification_email:
        raise HTTPException(400, "No notification email configured. Set one in Settings → Notification Email.")
    subject, html = build_alert_email(
        "oversold",
        "TEST",
        {"Symbol": "TEST", "Type": "Test Email", "Price": "100.00", "RSI": "28.50", "Time (UTC)": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")},
    )
    sent, msg = await asyncio.to_thread(send_email, gs.notification_email, subject, html)
    if not sent:
        raise HTTPException(500, msg)
    return {"ok": True, "message": msg}


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
