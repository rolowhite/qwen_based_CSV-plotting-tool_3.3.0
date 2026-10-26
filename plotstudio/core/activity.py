"""The user's local activity history (plots, files, features, exports) and the numbers the profile shows.

Everything here is counted from what the user really did; nothing is made up. An empty history gives zeros
and the dashboard says how to start. Counters live in the settings file, one entry per day.
"""
from __future__ import annotations

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta, timezone

XP = {"plot": 10, "file": 20, "export": 15, "feature": 50}
LEVEL_XP = 1000
LEVEL_NAMES = ("Getting started", "Explorer", "Insight builder", "Analyst", "Pattern finder", "Data storyteller")
RANGES = {"Month": 5, "Quarter": 14, "Year": 52}          # weeks shown on the calendar


def plot_level(plots: int) -> int:
    """Map a daily plot count to one of five heatmap levels."""
    count = max(0, int(plots))
    if count == 0:
        return 0
    if count <= 2:
        return 1
    if count <= 5:
        return 2
    if count <= 10:
        return 3
    return 4


def _date_value(today=None) -> date:
    if today is None:
        return date.today()
    return date.fromisoformat(today) if isinstance(today, str) else today


def _day(cfg: dict, today=None) -> dict:
    activity = cfg.setdefault("activity", {})
    entry = activity.setdefault(_date_value(today).isoformat(), {})
    for key in ("plots", "files", "rows", "features"):
        entry.setdefault(key, 0)
    entry.setdefault("graphs", {})
    return entry


def _timestamp(today=None) -> str:
    if today is None:
        return datetime.now().astimezone().isoformat(timespec="seconds")
    return datetime.combine(_date_value(today), time(12), tzinfo=timezone.utc).isoformat(timespec="seconds")


def _add_event(cfg: dict, event: dict) -> None:
    events = cfg.setdefault("recent_events", [])
    events.insert(0, event)
    del events[30:]


def record_plot(cfg, graph_id="", *, today=None, graph_name="", dataset_name="", variables=0):
    """A plot the user asked for (the Plot button), not an automatic redraw."""
    entry = _day(cfg, today)
    entry["plots"] += 1
    entry["xp"] = int(entry.get("xp", 0)) + XP["plot"]
    if graph_id:
        entry["graphs"][str(graph_id)] = int(entry["graphs"].get(str(graph_id), 0)) + 1
        names = cfg.setdefault("graph_names", {})
        names[str(graph_id)] = str(graph_name or graph_id.replace("_", " ").title())
        if dataset_name:
            entry.setdefault("graph_datasets", {}).setdefault(str(graph_id), {})[str(dataset_name)] = True
    graph_name = graph_name or (cfg.get("graph_names", {}).get(str(graph_id)) if graph_id else "") or "Plot"
    detail = dataset_name or "Workspace plot"
    if variables:
        detail += f", {int(variables)} columns"
    _add_event(cfg, {"kind": "plot", "title": graph_name, "detail": detail, "time": _timestamp(today),
                     "graph_id": str(graph_id), "graph_name": graph_name, "dataset": dataset_name})


def record_file(cfg, *, today=None, rows=0, dataset_name="", dataset_path=""):
    entry = _day(cfg, today)
    entry["files"] += 1
    entry["rows"] += max(0, int(rows or 0))
    entry["xp"] = int(entry.get("xp", 0)) + XP["file"]
    if dataset_name or dataset_path:
        path_key = str(dataset_path or dataset_name)
        cfg.setdefault("datasets_seen", {})[path_key] = {"name": str(dataset_name or path_key),
                                                         "rows": max(0, int(rows or 0))}


def record_feature(cfg, name="", mi_gain=None, *, today=None, dataset_name=""):
    entry = _day(cfg, today)
    entry["features"] += 1
    entry["xp"] = int(entry.get("xp", 0)) + XP["feature"]
    gain = f"{float(mi_gain):+.3f} mutual information gain" if mi_gain is not None else "Added to the feature steps"
    if dataset_name:
        gain += f", {dataset_name}"
    _add_event(cfg, {"kind": "feature", "title": f"Engineered “{name or 'new feature'}”", "detail": gain,
                     "time": _timestamp(today)})


def record_export(cfg, filename, *, today=None):
    entry = _day(cfg, today)
    entry["exports"] = int(entry.get("exports", 0)) + 1
    entry["xp"] = int(entry.get("xp", 0)) + XP["export"]
    notebook = str(filename).lower().endswith(".ipynb")
    _add_event(cfg, {"kind": "code", "title": "Exported a notebook" if notebook else "Exported a Python script",
                     "detail": str(filename), "time": _timestamp(today), "filename": str(filename)})


@dataclass(frozen=True)
class DayCell:
    date_iso: str
    day_date: date
    weekday: int
    week_index: int
    plots: int
    files: int
    features: int
    graphs: dict

    @property
    def level(self) -> int:
        return plot_level(self.plots)

    @property
    def tooltip_text(self) -> str:
        top = max(self.graphs, key=self.graphs.get) if self.graphs else "none"
        plots = "plot" if self.plots == 1 else "plots"
        files = "file" if self.files == 1 else "files"
        features = "feature" if self.features == 1 else "features"
        return (f"{self.day_date.strftime('%a %b')} {self.day_date.day}, {self.day_date.year}: "
                f"{self.plots} {plots}, {self.files} {files} loaded, {self.features} {features} built "
                f"(top: {top})")


@dataclass(frozen=True)
class ActivitySummary:
    total_plots: int
    total_files: int
    total_features: int
    active_days: int
    current_streak: int
    longest_streak: int
    favorite_graph: str
    max_daily_plots: int
    cells: list
    month_headers: list


def _int(raw, key) -> int:
    try:
        return max(0, int(raw.get(key, 0) or 0))
    except (TypeError, ValueError):
        return 0


def _days(cfg) -> dict:
    """{date: raw entry} for the valid days in the history."""
    activity = cfg.get("activity") if isinstance(cfg.get("activity"), dict) else {}
    out = {}
    for key, raw in activity.items():
        if not isinstance(raw, dict):
            continue
        try:
            out[date.fromisoformat(str(key))] = raw
        except ValueError:
            continue
    return out


def _calendar(days: dict, end: date, weeks: int):
    """Monday-first cells for complete weeks ending with the week of `end`, and month labels by week."""
    last_day = end + timedelta(days=6 - end.weekday())
    first_day = last_day - timedelta(days=weeks * 7 - 1)
    cells, headers, seen = [], [], set()
    for offset in range(weeks * 7):
        day = first_day + timedelta(days=offset)
        raw = days.get(day, {})
        graphs = raw.get("graphs", {}) if isinstance(raw.get("graphs", {}), dict) else {}
        week = offset // 7
        month = day.strftime("%Y-%m")
        if month not in seen and (day.day <= 7 or offset == 0):
            seen.add(month)
            if not headers or week - headers[-1][0] >= 3:        # labels never run into each other
                headers.append((week, day.strftime("%b")))
        cells.append(DayCell(day.isoformat(), day, day.weekday(), week, _int(raw, "plots"), _int(raw, "files"),
                             _int(raw, "features"), {str(k): _int(graphs, k) for k in graphs}))
    return cells, headers


def _streaks(active: set, end: date):
    longest = streak = 0
    previous = None
    for day in sorted(active):
        streak = streak + 1 if previous and day == previous + timedelta(days=1) else 1
        longest = max(longest, streak)
        previous = day
    current, cursor = 0, end if end in active else end - timedelta(days=1)
    while cursor in active:
        current += 1
        cursor -= timedelta(days=1)
    return current, longest


def summarize_activity(cfg, *, end_date=None, weeks=52) -> ActivitySummary:
    """All-time totals, streaks and a Monday-first calendar of the last `weeks` weeks."""
    end = _date_value(end_date)
    days = _days(cfg)
    graph_totals = Counter()
    for raw in days.values():
        graphs = raw.get("graphs", {}) if isinstance(raw.get("graphs", {}), dict) else {}
        graph_totals.update({str(k): _int(graphs, k) for k in graphs})
    active = {d for d, raw in days.items() if d <= end and any(_int(raw, k) for k in ("plots", "files", "features"))}
    current, longest = _streaks(active, end)
    cells, headers = _calendar(days, end, max(1, int(weeks)))
    return ActivitySummary(sum(_int(r, "plots") for r in days.values()), sum(_int(r, "files") for r in days.values()),
                           sum(_int(r, "features") for r in days.values()), len(active), current, longest,
                           graph_totals.most_common(1)[0][0] if graph_totals else "—",
                           max((_int(r, "plots") for r in days.values()), default=0), cells, headers)


@dataclass(frozen=True)
class Badge:
    title: str
    detail: str
    icon: str
    have: int
    need: int

    @property
    def earned(self) -> bool:
        return self.have >= self.need

    @property
    def progress(self) -> str:
        return "Earned" if self.earned else f"{self.have} of {self.need}"


@dataclass(frozen=True)
class DashboardSummary:
    total_plots: int
    plots_this_month: int
    current_streak: int
    longest_streak: int
    active_days_90d: int
    datasets_explored: int
    total_rows_explored: int
    active_days_range: int
    plots_range: int
    quarter_plots: int
    last_quarter_plots: int
    xp_total: int
    level: int
    level_name: str
    xp_progress: int
    cells: list
    month_headers: list
    recent_events: list
    week_graph_id: str
    week_graph_name: str
    week_graph_uses: int
    week_datasets: int
    badges: list = field(default_factory=list)
    is_empty: bool = False

    @property
    def badges_earned(self) -> int:
        return sum(b.earned for b in self.badges)


def summarize_dashboard(cfg, *, range_mode="Year", end_date=None) -> DashboardSummary:
    """Every number on the profile, from the recorded history only."""
    end = _date_value(end_date)
    days = {d: raw for d, raw in _days(cfg).items() if d <= end}
    real = {d: raw for d, raw in days.items() if any(_int(raw, k) for k in ("plots", "files", "features", "rows"))}
    all_time = summarize_activity({"activity": {d.isoformat(): r for d, r in real.items()}}, end_date=end)
    cells, headers = _calendar(real, end, RANGES.get(range_mode, 52))

    datasets = cfg.get("datasets_seen") if isinstance(cfg.get("datasets_seen"), dict) else {}
    month_start = end.replace(day=1)
    quarter_start = date(end.year, (end.month - 1) // 3 * 3 + 1, 1)
    prev_end = quarter_start - timedelta(days=1)
    prev_start = date(prev_end.year, (prev_end.month - 1) // 3 * 3 + 1, 1)
    this_q = sum(_int(r, "plots") for d, r in real.items() if d >= quarter_start)
    prev_q = sum(_int(r, "plots") for d, r in real.items() if prev_start <= d <= prev_end)
    xp_total = sum(_int(r, "xp") for r in real.values())
    level = xp_total // LEVEL_XP + 1

    week_start = end - timedelta(days=6)
    graph_counts, used = Counter(), set()
    for d, raw in real.items():
        if d >= week_start and isinstance(raw.get("graphs"), dict):
            graph_counts.update({str(g): _int(raw["graphs"], g) for g in raw["graphs"]})
    week_id, week_uses = graph_counts.most_common(1)[0] if graph_counts else ("", 0)
    for d, raw in real.items():
        by_graph = raw.get("graph_datasets", {})
        if d >= week_start and isinstance(by_graph, dict) and isinstance(by_graph.get(week_id), dict):
            used.update(by_graph[week_id])
    names = cfg.get("graph_names", {}) if isinstance(cfg.get("graph_names"), dict) else {}
    kinds = {g for r in real.values() if isinstance(r.get("graphs"), dict) for g, n in r["graphs"].items() if n}
    exports = sum(_int(r, "exports") for r in real.values())
    badges = [
        Badge("First plot", "Draw your first plot", "chart_bars", min(all_time.total_plots, 1), 1),
        Badge("Chart starter", "Draw 10 plots", "chart_bars", min(all_time.total_plots, 10), 10),
        Badge("Explorer", "Use 5 graph types", "spark", min(len(kinds), 5), 5),
        Badge("Feature builder", "Engineer one feature", "spark",
              min(all_time.total_features, 1), 1),
        Badge("Code as truth", "Export your code", "code_slash", min(exports, 1), 1),
        Badge("On a roll", "Plot 7 days in a row", "flame", min(all_time.longest_streak, 7), 7),
    ]
    recent = sorted((dict(e) for e in cfg.get("recent_events", []) if isinstance(e, dict)),
                    key=lambda e: str(e.get("time", "")), reverse=True)[:30]
    return DashboardSummary(
        total_plots=all_time.total_plots,
        plots_this_month=sum(_int(r, "plots") for d, r in real.items() if d >= month_start),
        current_streak=all_time.current_streak, longest_streak=all_time.longest_streak,
        active_days_90d=sum(1 for d, r in real.items() if d >= end - timedelta(days=89) and _int(r, "plots")),
        datasets_explored=len(datasets),
        total_rows_explored=sum(_int(v, "rows") for v in datasets.values() if isinstance(v, dict)),
        active_days_range=sum(1 for c in cells if c.day_date <= end and c.plots),
        plots_range=sum(c.plots for c in cells if c.day_date <= end),
        quarter_plots=this_q, last_quarter_plots=prev_q,
        xp_total=xp_total, level=level, level_name=LEVEL_NAMES[min(level - 1, len(LEVEL_NAMES) - 1)],
        xp_progress=xp_total % LEVEL_XP, cells=cells, month_headers=headers, recent_events=recent,
        week_graph_id=week_id, week_graph_name=names.get(week_id, week_id.replace("_", " ").title()) if week_id else "",
        week_graph_uses=week_uses, week_datasets=len(used), badges=badges, is_empty=not real)
