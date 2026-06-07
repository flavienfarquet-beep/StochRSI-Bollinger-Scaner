# RSI & MA Tracker — PRD

## Problem Statement
Build a small basic web app that tracks RSI and moving-average crossovers (golden/death cross) on stock assets in near real-time. Daily scan of asset data, adjustable RSI/MA parameters on the UI, email + browser push notifications when thresholds are met.

## User choices
- Source: Yahoo Finance (yfinance + curl_cffi)
- Asset type: stocks/ETFs only (default ticker: VT)
- Notifications: Email (Resend) + Web Push (VAPID, background-capable)
- Auth: none (single-user)
- Daily scan: 20:00 UTC

## Implemented
- Backend (FastAPI)
  - yfinance with curl_cffi session + 3-retry fetch
  - Indicators: RSI (Wilder), SMA, EMA, MA position, crossover detection
  - Per-ticker overrides + global settings (RSI period/bounds, MA short/long/type, alert toggles)
  - APScheduler daily run at 20:00 UTC + manual /api/scan/run
  - Alerts: oversold, overbought, golden_cross, death_cross, combo_bullish, combo_bearish
  - Email via Resend (free, 100/day)
  - Web Push via VAPID + pywebpush, multi-device subscription store
- Frontend (React + Tailwind)
  - Swiss high-contrast design (IBM Plex Sans/Mono)
  - Dashboard rows with price, sparkline, RSI badge, MA values, MA-position indicator (↑/↓), crossover badge, combo highlight
  - Settings sheet (global) with MA type SMA/EMA, RSI/MA params, alert toggles incl. combo
  - Per-ticker settings sheet with inherit/override
  - Alert history feed
  - Service worker /sw.js + push subscription flow

## Backlog
- P1: First daily auto-scan UI showing scheduled next-run countdown
- P1: Chart drilldown per ticker (multi-day RSI/price overlay)
- P2: CSV import/export of watchlist
- P2: Multi-recipient email
- P2: Custom alert cooldown to prevent daily-repeat alerts
