"""FastAPI mock hardware server for AC control (port 8765 by default)."""

from __future__ import annotations

from fastapi import FastAPI
import uvicorn

app = FastAPI(title="Aegis AC Mock Server")

AC_STATE: dict[str, bool] = {"on": False}


@app.post("/ac/on")
def turn_on() -> dict:
    AC_STATE["on"] = True
    return {"status": "ok", "ac_on": True}


@app.post("/ac/off")
def turn_off() -> dict:
    AC_STATE["on"] = False
    return {"status": "ok", "ac_on": False}


@app.get("/ac/status")
def get_status() -> dict:
    return {"ac_on": AC_STATE["on"]}


def run_server() -> None:
    """Entry point for ``aegis-ac-server`` console script."""
    uvicorn.run("aegis.ac_control.server:app", host="127.0.0.1", port=8765, reload=False)
