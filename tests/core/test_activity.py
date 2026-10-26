from datetime import date, timedelta

import pytest

from plotstudio.core.activity import (plot_level, record_export, record_feature, record_file, record_plot,
                                      summarize_activity, summarize_dashboard)


@pytest.mark.parametrize("plots,level", [(0, 0), (1, 1), (2, 1), (3, 2), (5, 2), (6, 3), (10, 3), (11, 4)])
def test_plot_levels(plots, level):
    assert plot_level(plots) == level


def test_recorders_and_calendar_summary_across_streak():
    cfg = {"activity": {}}
    end = date(2025, 1, 10)
    for offset, graph in ((-3, "scatter"), (-2, "line"), (-1, "scatter"), (0, "scatter")):
        day = end + timedelta(days=offset)
        record_plot(cfg, graph, today=day)
        record_plot(cfg, graph, today=day)
        if offset in (-2, 0):
            record_plot(cfg, graph, today=day)
        record_file(cfg, today=day)
        if offset == -1:
            record_file(cfg, today=day)
            record_feature(cfg, today=day)
    summary = summarize_activity(cfg, end_date=end)
    assert summary.total_plots == 10
    assert summary.total_files == 5
    assert summary.total_features == 1
    assert summary.current_streak == 4
    assert summary.longest_streak == 4
    assert summary.active_days == 4
    assert summary.favorite_graph == "scatter"
    assert summary.max_daily_plots == 3
    assert len(summary.cells) == 52 * 7
    assert {cell.weekday for cell in summary.cells} == set(range(7))
    assert len({cell.date_iso for cell in summary.cells}) == 52 * 7
    assert summary.month_headers
    active = next(cell for cell in summary.cells if cell.date_iso == end.isoformat())
    assert active.level == plot_level(3)
    assert "3 plots" in active.tooltip_text
    assert active.graphs == {"scatter": 3}


def test_record_plot_ignores_empty_graph_id_but_counts_plot():
    cfg = {}
    record_plot(cfg, today=date(2025, 1, 1))
    assert cfg["activity"]["2025-01-01"] == {
        "plots": 1, "files": 0, "rows": 0, "features": 0, "graphs": {}, "xp": 10,
    }


def test_totals_are_all_time_while_calendar_stays_52_weeks():
    cfg = {"activity": {"2020-01-01": {"plots": 7, "files": 2, "features": 3,
                                        "graphs": {"bar": 7}}}}
    summary = summarize_activity(cfg, end_date=date(2025, 1, 1))
    assert summary.total_plots == 7
    assert summary.total_files == 2
    assert summary.total_features == 3
    assert summary.active_days == 1
    assert summary.favorite_graph == "bar"
    assert summary.max_daily_plots == 7
    assert all(cell.date_iso != "2020-01-01" for cell in summary.cells)


def test_an_empty_history_shows_zeros_not_made_up_numbers():
    cfg = {"activity": {}}
    s = summarize_dashboard(cfg, end_date=date(2025, 1, 1))
    assert s.is_empty and s.total_plots == 0 and s.current_streak == 0 and s.xp_total == 0
    assert s.recent_events == [] and s.badges_earned == 0 and s.quarter_plots == s.last_quarter_plots == 0
    assert len(s.cells) == 364 and all(c.plots == 0 for c in s.cells)
    assert cfg["activity"] == {}


def test_badges_and_level_follow_what_was_done():
    cfg = {}
    end = date(2025, 3, 10)
    for i in range(7):
        record_plot(cfg, ["bar", "line", "scatter", "box", "hist", "bar", "bar"][i], today=end - timedelta(days=6 - i))
    record_feature(cfg, "fare_per_person", 0.08, today=end)
    record_export(cfg, "clean.py", today=end)
    s = summarize_dashboard(cfg, end_date=end)
    earned = {b.title for b in s.badges if b.earned}
    assert earned == {"First plot", "Explorer", "Feature builder", "Code as truth", "On a roll"}
    chart = next(b for b in s.badges if b.title == "Chart starter")
    assert chart.progress == "7 of 10"
    assert s.xp_total == 7 * 10 + 50 + 15 and s.level == 1 and s.level_name == "Getting started"


def test_dashboard_range_toggle_and_real_activity_updates_live_metrics():
    cfg = {"activity": {}, "datasets_seen": {}}
    end = date(2025, 1, 10)
    record_file(cfg, today=end, rows=120, dataset_name="sales.csv", dataset_path="sales.csv")
    record_plot(cfg, "scatter", today=end, graph_name="Scatter / Bubble", dataset_name="sales.csv")
    record_plot(cfg, "scatter", today=end, graph_name="Scatter / Bubble", dataset_name="customers.csv")
    quarter = summarize_dashboard(cfg, range_mode="Quarter", end_date=end)
    month = summarize_dashboard(cfg, range_mode="Month", end_date=end)
    assert not quarter.is_empty
    assert len(quarter.cells) == 98
    assert len(month.cells) == 35
    assert quarter.total_plots == 2
    assert quarter.plots_range == 2
    assert quarter.datasets_explored == 1
    assert quarter.total_rows_explored == 120
    assert quarter.week_graph_id == "scatter"
    assert quarter.week_graph_uses == 2
    assert quarter.week_datasets == 2
    assert quarter.recent_events[0]["kind"] == "plot"
