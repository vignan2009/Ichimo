from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

import requests
from dotenv import load_dotenv, set_key
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from ichimoku_framework.config.models import AppConfig


ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_PATH = ROOT_DIR / ".env"
CONFIG_PATH = ROOT_DIR / "config" / "example_strategy.yaml"
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
STATIC_DIR = Path(__file__).resolve().parent / "static"

load_dotenv(ENV_PATH if ENV_PATH.exists() else None)

app = FastAPI(title="Ichimoku Research Console")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class TokenPayload(BaseModel):
    access_token: str


def _reload_env() -> None:
    load_dotenv(ENV_PATH if ENV_PATH.exists() else None, override=True)


def _masked(value: str | None) -> str | None:
    if not value:
        return None
    if len(value) <= 10:
        return "*" * len(value)
    return f"{value[:5]}...{value[-4:]}"


def _upstox_creds() -> dict[str, str | None]:
    _reload_env()
    return {
        "api_key": os.getenv("UPSTOX_API_KEY") or os.getenv("UPSTOX_CLIENT_ID"),
        "api_secret": os.getenv("UPSTOX_API_SECRET"),
        "redirect_uri": os.getenv("REDIRECT_URI", "http://localhost:8000/callback"),
        "access_token": os.getenv("UPSTOX_ACCESS_TOKEN"),
    }


def _artifact_entry(path: Path) -> dict[str, str]:
    stats = path.stat()
    return {
        "name": path.name,
        "size": f"{stats.st_size / 1024:.1f} KB",
        "modified": datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M"),
        "url": f"/api/artifacts/{path.name}",
    }


@app.get("/")
def read_root() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
def status() -> dict[str, object]:
    creds = _upstox_creds()
    config = AppConfig.from_yaml(CONFIG_PATH)
    latest_report = None
    reports = sorted(ARTIFACTS_DIR.glob("ichimoku_backtest_*.xlsx"), key=lambda path: path.stat().st_mtime, reverse=True)
    if reports:
        latest_report = _artifact_entry(reports[0])
    return {
        "connected": bool(creds["access_token"]),
        "api_key_configured": bool(creds["api_key"]),
        "api_secret_configured": bool(creds["api_secret"]),
        "redirect_uri": creds["redirect_uri"],
        "masked_token": _masked(creds["access_token"]),
        "latest_report": latest_report,
        "config": {
            "instrument_key": config.data.instrument_key,
            "timeframe": config.data.timeframe,
            "from_date": config.data.from_date,
            "to_date": config.data.to_date,
            "options_enabled": config.options.enabled,
            "underlying": config.options.underlying,
            "allow_overnight": config.options.allow_overnight,
            "entry_classes": [item.value for item in config.strategy.enabled_entry_bullish_classes]
            + [item.value for item in config.strategy.enabled_entry_bearish_classes],
            "stop_loss_percent": config.strategy.stop_loss_percent,
            "take_profit_percent": config.strategy.take_profit_percent,
        },
    }


@app.get("/api/upstox-login")
def upstox_login() -> dict[str, str]:
    creds = _upstox_creds()
    if not creds["api_key"]:
        raise HTTPException(status_code=400, detail="UPSTOX_API_KEY is not configured")
    url = (
        "https://api.upstox.com/v2/login/authorization/dialog"
        f"?response_type=code&client_id={quote_plus(str(creds['api_key']))}"
        f"&redirect_uri={quote_plus(str(creds['redirect_uri']))}"
    )
    return {"url": url}


@app.get("/callback")
def upstox_callback(code: str) -> RedirectResponse | dict[str, str]:
    creds = _upstox_creds()
    missing = [key for key in ("api_key", "api_secret", "redirect_uri") if not creds[key]]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing Upstox credentials: {', '.join(missing)}")
    response = requests.post(
        "https://api.upstox.com/v2/login/authorization/token",
        headers={"accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"},
        data={
            "code": code,
            "client_id": creds["api_key"],
            "client_secret": creds["api_secret"],
            "redirect_uri": creds["redirect_uri"],
            "grant_type": "authorization_code",
        },
        timeout=20,
    )
    if response.status_code != 200:
        raise HTTPException(status_code=response.status_code, detail=response.text)
    access_token = response.json().get("access_token")
    if not access_token:
        raise HTTPException(status_code=502, detail="Upstox token response did not include access_token")
    ENV_PATH.touch(exist_ok=True)
    set_key(str(ENV_PATH), "UPSTOX_ACCESS_TOKEN", access_token)
    _reload_env()
    return RedirectResponse(url="/?upstox_auth=success")


@app.post("/api/token")
def save_token(payload: TokenPayload) -> dict[str, str]:
    token = payload.access_token.strip().strip("'").strip('"')
    if not token:
        raise HTTPException(status_code=400, detail="access_token is required")
    ENV_PATH.touch(exist_ok=True)
    set_key(str(ENV_PATH), "UPSTOX_ACCESS_TOKEN", token)
    _reload_env()
    return {"status": "saved"}


@app.post("/api/logout")
def logout() -> dict[str, str]:
    ENV_PATH.touch(exist_ok=True)
    set_key(str(ENV_PATH), "UPSTOX_ACCESS_TOKEN", "")
    _reload_env()
    return {"status": "disconnected"}


@app.get("/api/artifacts")
def list_artifacts() -> list[dict[str, str]]:
    if not ARTIFACTS_DIR.exists():
        return []
    files = [
        path
        for path in ARTIFACTS_DIR.iterdir()
        if path.is_file() and (path.suffix == ".xlsx" or path.name == "dashboard.html")
    ]
    return [_artifact_entry(path) for path in sorted(files, key=lambda item: item.stat().st_mtime, reverse=True)]


@app.get("/api/artifacts/{filename}")
def download_artifact(filename: str) -> FileResponse:
    root = ARTIFACTS_DIR.resolve()
    path = (ARTIFACTS_DIR / filename).resolve()
    if root not in path.parents and path != root:
        raise HTTPException(status_code=400, detail="Invalid artifact filename")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(path)
