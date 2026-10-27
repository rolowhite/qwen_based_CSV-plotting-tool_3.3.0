"""Remembering recent files and preferences between runs (~/.csv_plot_studio.json)."""
from __future__ import annotations

import json
from pathlib import Path

PATH = Path.home() / ".csv_plot_studio.json"
DEFAULTS = {
    "recent": [],
    "style": {"theme": "studio", "palette": "default", "context": "notebook"},
    "style_version": 1,          # 2 from CSV Plot Studio 2.0 (the Studio chart style became the default)
    "auto_update": True,
    "geometry": "",
    "last_dir": "",
    "save_dir": "",
    "dpi": "150 dpi",
    "style_open": False,
    "ui_theme": "dark",          # light | dark
    "show_values": True,         # ball + value under the mouse
    "range_sliders": True,       # X/Y range sliders around the plot
    "mouse_nav": True,           # drag to move, wheel to zoom
    "fit_window": True,          # stretch the plot to the window
    "activity": {},                 # local daily plot, file and feature counters
    "profile": {},                  # name, initials, knownAs, selectedAvatar, joined (filled in by _profile)
    "recent_events": [],
    "datasets_seen": {},
    "graph_names": {},
    "notebook_ollama_url": "http://localhost:11434",   # the local Ollama that reads pictures
    "notebook_reader_model": "",    # the Ollama model that reads pictures ("" = the first that can)
    "notebook_gemini_key": "",      # the user's own free Gemini key (optional; kept only in this file)
    "notebook_gemini_model": "",    # "" = the best free Gemini model the key may use
}


AVATARS = ("engineer-rabbit", "data-crow", "case-fox")
_PLACEHOLDER = ("Alex Carter", "Oct 2024")      # the made-up profile 3.2.0 shipped with


def _computer_user() -> str:
    import getpass
    try:
        return getpass.getuser().replace(".", " ").replace("_", " ").strip().title() or "You"
    except Exception:  # noqa: BLE001 - no user name on this system: a neutral one
        return "You"


def _profile(saved) -> dict:
    """The local profile with every field present: the computer's user name until the user sets one."""
    import datetime

    p = dict(saved) if isinstance(saved, dict) else {}
    if (p.get("name"), p.get("joined")) == _PLACEHOLDER:
        p = {k: v for k, v in p.items() if k not in ("name", "first_name", "initials", "joined")}
    name = str(p.get("name") or "").strip() or _computer_user()
    p["name"] = name
    p["first_name"] = name.split()[0]
    p["initials"] = ("".join(w[0] for w in name.split()[:2]) or "?").upper()
    p["knownAs"] = str(p.get("knownAs") or p.get("role") or "Data explorer")
    if p.get("selectedAvatar") not in AVATARS:
        p["selectedAvatar"] = AVATARS[0]
    p["joined"] = str(p.get("joined") or datetime.date.today().strftime("%b %Y"))
    return p


def load() -> dict:
    data = json.loads(json.dumps(DEFAULTS))
    try:
        saved = json.loads(PATH.read_text(encoding="utf-8"))
        if isinstance(saved, dict):
            data.update({k: v for k, v in saved.items() if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    data["profile"] = _profile(data.get("profile"))
    for key in ("activity", "datasets_seen", "graph_names"):
        if not isinstance(data.get(key), dict):
            data[key] = {}
    if not isinstance(data.get("recent_events"), list):
        data["recent_events"] = []
    return data


def save(data: dict):
    try:
        PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except OSError:
        pass


def add_recent(data: dict, path, limit=10):
    path = str(Path(path).resolve())
    recent = [p for p in data.get("recent", []) if p != path]
    data["recent"] = [path] + recent[: limit - 1]


