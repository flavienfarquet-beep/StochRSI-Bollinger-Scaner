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

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

from data_source import fetch_history, validate_symbol
from email_service import build_alert_email, send_email
from indicators import bollinger_bands, detect_crossover, ma_position, moving_average, rsi, rsi_signal, stoch_rsi
from push_service import is_gone, send_push

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

mongo_url = "mongodb+srv://flavienfarquet:fk3h477e6wh3keldj3@stch-bollinger-cluster.bb46tkk.mongodb.net/?appName=Stch-bollinger-cluster"
client = AsyncIOMotorClient(mongo_url)
db = client["rsi_tracker"]


import resend
resend.api_key = "re_WpHPjiec_Fk7SR4TndDgFb7w1CYfAj4b4"


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
    # RSI
    rsi_period: int = 14
    rsi_lower: float = 30.0
    rsi_upper: float = 70.0
    # MA
    ma_short: int = 50
    ma_long: int = 200
    ma_type: str = "sma"  # "sma" or "ema"
    # Stochastic RSI
    stoch_rsi_period: int = 14
    stoch_period: int = 14
    stoch_k_smooth: int = 3
    stoch_d_smooth: int = 3
    stoch_lower: float = 20.0
    stoch_upper: float = 80.0
    # Bollinger Bands
    bb_period: int = 20
    bb_std: float = 2.0
    bb_proximity_pct: float = 1.0  # within X% of band counts as "touching"
    # Alert toggles
    alert_rsi_low: bool = True
    alert_rsi_high: bool = True
    alert_golden_cross: bool = True
    alert_death_cross: bool = True
    alert_stoch_low: bool = True
    alert_stoch_high: bool = True
    alert_bb_lower: bool = True
    alert_bb_upper: bool = True
    alert_combo: bool = True
    notification_email: str = ""
    push_enabled: bool = False


class TickerCreate(BaseModel):
    symbol: str


class TickerOverride(BaseModel):
    rsi_period: Optional[int] = None
    rsi_lower: Optional[float] = None
    rsi_upper: Optional[float] = None
    ma_short: Optional[int] = None
    ma_long: Optional[int] = None
    ma_type: Optional[str] = None
    stoch_rsi_period: Optional[int] = None
    stoch_period: Optional[int] = None
    stoch_k_smooth: Optional[int] = None
    stoch_d_smooth: Optional[int] = None
    stoch_lower: Optional[float] = None
    stoch_upper: Optional[float] = None
    bb_period: Optional[int] = None
    bb_std: Optional[float] = None
    bb_proximity_pct: Optional[float] = None
    alert_rsi_low: Optional[bool] = None
    alert_rsi_high: Optional[bool] = None
    alert_golden_cross: Optional[bool] = None
    alert_death_cross: Optional[bool] = None
    alert_stoch_low: Optional[bool] = None
    alert_stoch_high: Optional[bool] = None
    alert_bb_lower: Optional[bool] = None
    alert_bb_upper: Optional[bool] = None
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


class PushSubscription(BaseModel):
    endpoint: str
    keys: dict
    user_agent: Optional[str] = None


async def send_push_to_all(title: str, body: str, data: dict | None = None) -> int:
    """Send push to all stored subscriptions. Returns count of successful sends."""
    sent = 0
    subs = await db.push_subs.find({}, {"_id": 0}).to_list(1000)
    for sub in subs:
        sub_info = {"endpoint": sub["endpoint"], "keys": sub["keys"]}
        ok, msg = await asyncio.to_thread(send_push, sub_info, title, body, data)
        if ok:
            sent += 1
        elif is_gone(msg):
            await db.push_subs.delete_one({"endpoint": sub["endpoint"]})
            logger.info(f"Removed expired push subscription: {sub['endpoint'][:50]}...")
    return sent


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

    # Stochastic RSI
    k_arr, d_arr = stoch_rsi(
        closes, s["stoch_rsi_period"], s["stoch_period"], s["stoch_k_smooth"], s["stoch_d_smooth"]
    )
    stoch_k = k_arr[-1] if k_arr else None
    stoch_d = d_arr[-1] if d_arr else None
    stoch_sig = None
    if stoch_k is not None:
        if stoch_k <= s["stoch_lower"]:
            stoch_sig = "stoch_oversold"
        elif stoch_k >= s["stoch_upper"]:
            stoch_sig = "stoch_overbought"

    # Bollinger Bands
    bb_upper, bb_middle, bb_lower = bollinger_bands(closes, s["bb_period"], s["bb_std"])
    bb_u = bb_upper[-1]
    bb_m = bb_middle[-1]
    bb_l = bb_lower[-1]
    last_price = data["last_price"]
    bb_sig = None
    bb_pct = s["bb_proximity_pct"] / 100.0
    if bb_l is not None and last_price <= bb_l * (1 + bb_pct):
        bb_sig = "bb_lower"
    elif bb_u is not None and last_price >= bb_u * (1 - bb_pct):
        bb_sig = "bb_upper"

    spark = closes[-30:] if len(closes) >= 30 else closes
    return {
        "symbol": data["symbol"],
        "name": data["name"],
        "currency": data["currency"],
        "last_price": last_price,
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
        "stoch_k": stoch_k,
        "stoch_d": stoch_d,
        "stoch_signal": stoch_sig,
        "bb_upper": bb_u,
        "bb_middle": bb_m,
        "bb_lower": bb_l,
        "bb_signal": bb_sig,
        "spark": spark,
        "settings": s,
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
        # Stochastic RSI
        if state["stoch_signal"] == "stoch_oversold" and s.get("alert_stoch_low", True):
            per_ticker.append(Alert(symbol=symbol, type="stoch_oversold", value=state.get("stoch_k"), price=state["last_price"]))
        if state["stoch_signal"] == "stoch_overbought" and s.get("alert_stoch_high", True):
            per_ticker.append(Alert(symbol=symbol, type="stoch_overbought", value=state.get("stoch_k"), price=state["last_price"]))
        # Bollinger Bands
        if state["bb_signal"] == "bb_lower" and s.get("alert_bb_lower", True):
            per_ticker.append(Alert(symbol=symbol, type="bb_lower_touch", value=state.get("bb_lower"), price=state["last_price"]))
        if state["bb_signal"] == "bb_upper" and s.get("alert_bb_upper", True):
            per_ticker.append(Alert(symbol=symbol, type="bb_upper_touch", value=state.get("bb_upper"), price=state["last_price"]))

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

    # Persist alerts, then send ONE consolidated notification per ticker
    by_ticker: dict[str, List[Alert]] = {}
    for alert in triggered:
        by_ticker.setdefault(alert.symbol, []).append(alert)

    for symbol, group in by_ticker.items():
        # Email + Push: one consolidated message per symbol with all signals
        types = [a.type for a in group]
        is_combo = len(group) > 1
        # Check if combo bullish (stoch_oversold + bb_lower_touch)
        types_set = set(types)
        is_buy_combo = is_combo and "stoch_oversold" in types_set and "bb_lower_touch" in types_set
        # Friendly labels
        label_map = {
            "oversold": "RSI", "overbought": "RSI",
            "golden_cross": "Golden Cross", "death_cross": "Death Cross",
            "stoch_oversold": "Stochastic", "stoch_overbought": "Stochastic",
            "bb_lower_touch": "Bollinger", "bb_upper_touch": "Bollinger",
        }
        signals = []
        for tp in types:
            lbl = label_map.get(tp, tp)
            if lbl not in signals:
                signals.append(lbl)
        signals_str = " + ".join(signals)
        title_prefix = "Combo: " if is_combo else ""
        buy_tag = " 🟢 BUY" if is_buy_combo else ""
        notif_title = f"{symbol}{buy_tag} — {title_prefix}{signals_str}"

        # Body details
        last_alert = group[-1]
        details_lines = []
        for a in group:
            if a.value is not None:
                details_lines.append(f"{a.type}: {a.value:.2f}")
            else:
                details_lines.append(a.type)
        body_text = " · ".join(details_lines)
        if last_alert.price is not None:
            body_text = f"@ {last_alert.price:.2f} · " + body_text

        # Email
        email_sent = False
        if gs.notification_email:
            email_html = "<br/>".join(f"<code>{line}</code>" for line in details_lines)
            email_subject = f"[StochRSI-Bollinger Scaner] {notif_title}"
            buy_badge_html = '<span style="display:inline-block;background:#059669;color:#fff;padding:2px 8px;font-size:10px;font-family:monospace;font-weight:bold;letter-spacing:0.1em;text-transform:uppercase;margin-left:8px;">BUY</span>' if is_buy_combo else ""
            html = f"""
<div style="font-family:'IBM Plex Sans',Arial,sans-serif;max-width:560px;margin:0 auto;background:#F8F9FA;padding:24px;">
  <div style="background:#FFFFFF;border:1px solid #E5E7EB;padding:24px;">
    <p style="font-size:11px;letter-spacing:0.1em;text-transform:uppercase;color:#9CA3AF;margin:0 0 8px;">RSI &amp; MA Tracker — Signal</p>
    <h1 style="font-size:22px;margin:0 0 4px;color:#111827;font-weight:500;">{symbol}{buy_badge_html}</h1>
    <p style="margin:0 0 16px;color:#6B7280;font-size:14px;"><strong>{title_prefix}{signals_str}</strong></p>
    <div style="font-family:monospace;font-size:13px;color:#111827;">
      Price: {last_alert.price:.2f}<br/>
      {email_html}
    </div>
  </div>
</div>"""
            email_sent, _msg = await asyncio.to_thread(send_email, gs.notification_email, email_subject, html)

        # Push (one consolidated)
        await send_push_to_all(notif_title, body_text, {"symbol": symbol, "types": types})

        # Persist all alerts (with email_sent flag on consolidated)
        for a in group:
            a.email_sent = email_sent
            doc = a.model_dump()
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
    # Seed default ticker
    if await db.tickers.count_documents({}) == 0:
        seed = Ticker(symbol="VT", name="Vanguard Total World Stock")
        doc = seed.model_dump()
        doc["created_at"] = doc["created_at"].isoformat()
        await db.tickers.insert_one(doc)
    # Ensure global settings exist
    await get_global_settings()
    
    # Exécute le scan immédiatement au démarrage sur GitHub
    await run_scan()
    yield
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


@api.get("/push/vapid-public-key")
async def vapid_public_key():
    return {"key": os.environ.get("VAPID_PUBLIC_KEY", "")}


@api.post("/push/subscribe")
async def push_subscribe(sub: PushSubscription):
    doc = sub.model_dump()
    doc["created_at"] = datetime.now(timezone.utc).isoformat()
    # Upsert on endpoint
    await db.push_subs.update_one(
        {"endpoint": sub.endpoint},
        {"$set": doc},
        upsert=True,
    )
    return {"ok": True}


@api.post("/push/unsubscribe")
async def push_unsubscribe(payload: dict):
    endpoint = payload.get("endpoint")
    if not endpoint:
        raise HTTPException(400, "endpoint required")
    result = await db.push_subs.delete_one({"endpoint": endpoint})
    return {"deleted": result.deleted_count}


@api.post("/push/test")
async def push_test():
    count = await send_push_to_all(
        "RSI & MA Tracker — Test",
        "This is a test push notification.",
        {"type": "test"},
    )
    total = await db.push_subs.count_documents({})
    if total == 0:
        raise HTTPException(400, "No push subscriptions registered. Enable push notifications in Settings first.")
    return {"sent": count, "total_subscriptions": total}


app.include_router(api)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)
