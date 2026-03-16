"""Analytics dashboard panel for the LLM Buddy Qt GUI.

PySide6 port of the tkinter ``AnalyticsMixin``.  Provides date-range
filtering, summary statistics, and a 2x2 chart grid (bar, pie, line,
timeline) powered by QtCharts.
"""

import logging
from datetime import datetime, timedelta

from PySide6.QtCore import Qt, Slot, QDateTime
from PySide6.QtGui import QColor, QFont, QPainter
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QDateEdit,
)

from llm_buddy.qt.theme import (
    CHART_PALETTE, EVENT_COLOURS,
    StatCard, current_theme_name,
)

# Analytics data service --------------------------------------------------
try:
    from llm_buddy.services.analytics_service import (
        compute_analytics_data,
        parse_date,
        fmt_tokens,
    )
except ImportError:  # pragma: no cover – inline fallback
    from collections import Counter
    from typing import Any, Dict, List, Optional

    def _count_tokens_fb(text: str) -> int:
        return len(text) // 4 if text else 0

    def compute_analytics_data(
        prompts, start_date=None, end_date=None,
    ) -> Dict[str, Any]:
        filtered = list(prompts)
        if start_date:
            filtered = [p for p in filtered if p.timestamp >= start_date]
        if end_date:
            filtered = [p for p in filtered if p.timestamp <= end_date]
        date_ctr: Counter = Counter()
        for p in filtered:
            date_ctr[p.timestamp.strftime("%Y-%m-%d")] += 1
        sorted_dates = sorted(date_ctr.keys())
        prompts_by_date = [(d, date_ctr[d]) for d in sorted_dates]
        llm_ctr: Counter = Counter()
        for p in filtered:
            llm_ctr[p.llm_used] += 1
        llm_distribution = list(llm_ctr.most_common())
        token_day: Counter = Counter()
        total_tokens = 0
        for p in filtered:
            tok = _count_tokens_fb(p.prompt_text)
            tok += _count_tokens_fb(getattr(p, "response_text", "") or "")
            total_tokens += tok
            token_day[p.timestamp.strftime("%Y-%m-%d")] += tok
        sorted_tok = sorted(token_day.keys())
        tokens_by_date = [(d, token_day[d]) for d in sorted_tok]
        timeline_events: List[Dict[str, Any]] = []
        for p in filtered:
            label = p.description or p.llm_used or "Prompt"
            if len(label) > 50:
                label = label[:47] + "\u2026"
            timeline_events.append(
                {"time": p.timestamp, "type": "prompt", "label": label}
            )
        timeline_events.sort(key=lambda e: e["time"])
        unique_dates = set(p.timestamp.date() for p in filtered)
        unique_llms = len(set(p.llm_used for p in filtered))
        return {
            "prompts_by_date": prompts_by_date,
            "llm_distribution": llm_distribution,
            "tokens_by_date": tokens_by_date,
            "timeline_events": timeline_events,
            "total_prompts": len(filtered),
            "total_tokens": total_tokens,
            "unique_llms": unique_llms,
            "active_days": len(unique_dates),
            "start_date": start_date,
            "end_date": end_date,
        }

    def parse_date(s: str):
        if not s:
            return None
        try:
            return datetime.strptime(s, "%Y-%m-%d")
        except ValueError:
            return None

    def fmt_tokens(n: int) -> str:
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n:,.0f}"
        return str(n)

# QtCharts – optional dependency -----------------------------------------
_CHARTS_AVAILABLE = False
try:
    from PySide6.QtCharts import (
        QChart,
        QChartView,
        QBarSeries,
        QBarSet,
        QBarCategoryAxis,
        QValueAxis,
        QPieSeries,
        QLineSeries,
        QDateTimeAxis,
        QScatterSeries,
    )

    _CHARTS_AVAILABLE = True
except ImportError:
    pass

logger = logging.getLogger(__name__)



class AnalyticsPanel(QWidget):
    """Analytics dashboard with date filters, summary stats, and charts.

    Parameters
    ----------
    main_window : MainWindow
        Back-reference used to access ``prompt_database`` and ``log()``.
    parent : QWidget | None
        Parent widget.
    """

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window
        self._cache = None
        self._use_all_time = True

        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        filter_group = QGroupBox("Date Range")
        filter_layout = QHBoxLayout(filter_group)

        filter_layout.addWidget(QLabel("From:"))
        self._from_edit = QDateEdit()
        self._from_edit.setCalendarPopup(True)
        self._from_edit.setDisplayFormat("yyyy-MM-dd")
        self._from_edit.setDate(QDateTime.currentDateTime().addDays(-30).date())
        self._from_edit.setMaximumWidth(140)
        filter_layout.addWidget(self._from_edit)

        filter_layout.addWidget(QLabel("To:"))
        self._to_edit = QDateEdit()
        self._to_edit.setCalendarPopup(True)
        self._to_edit.setDisplayFormat("yyyy-MM-dd")
        self._to_edit.setDate(QDateTime.currentDateTime().date())
        self._to_edit.setMaximumWidth(140)
        filter_layout.addWidget(self._to_edit)

        btn_all = QPushButton("All Time")
        btn_all.clicked.connect(self._all_time)
        filter_layout.addWidget(btn_all)

        btn_7 = QPushButton("Last 7 Days")
        btn_7.clicked.connect(self._last_7)
        filter_layout.addWidget(btn_7)

        btn_30 = QPushButton("Last 30 Days")
        btn_30.clicked.connect(self._last_30)
        filter_layout.addWidget(btn_30)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setProperty("class", "primary")
        btn_refresh.clicked.connect(self.refresh)
        filter_layout.addWidget(btn_refresh)

        filter_layout.addStretch()
        root.addWidget(filter_group)

        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)

        self._card_total = StatCard("Total Prompts", "#1976d2")
        stats_layout.addWidget(self._card_total)

        self._card_tokens = StatCard("Total Tokens", "#e15759")
        stats_layout.addWidget(self._card_tokens)

        self._card_llms = StatCard("Unique LLMs", "#59a14f")
        stats_layout.addWidget(self._card_llms)

        self._card_days = StatCard("Active Days", "#f28e2b")
        stats_layout.addWidget(self._card_days)

        root.addLayout(stats_layout)

        if _CHARTS_AVAILABLE:
            chart_grid = QGridLayout()
            chart_grid.setContentsMargins(0, 0, 0, 0)

            self._cv_bar = self._make_chart_view("Prompts per Day")
            chart_grid.addWidget(self._cv_bar, 0, 0)

            self._cv_pie = self._make_chart_view("LLM Distribution")
            chart_grid.addWidget(self._cv_pie, 0, 1)

            self._cv_line = self._make_chart_view("Token Usage Over Time")
            chart_grid.addWidget(self._cv_line, 1, 0)

            self._cv_timeline = self._make_chart_view("Activity Timeline")
            chart_grid.addWidget(self._cv_timeline, 1, 1)

            root.addLayout(chart_grid, stretch=1)
        else:
            fallback = QLabel(
                "Charts unavailable \u2014 install PySide6-QtCharts to "
                "enable the analytics charts."
            )
            fallback.setAlignment(Qt.AlignCenter)
            root.addWidget(fallback, stretch=1)

    @staticmethod
    def _make_chart_view(title: str) -> "QChartView":
        """Create a QChartView with an empty titled chart."""
        chart = QChart()
        chart.setTitle(title)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.legend().setVisible(True)
        chart.legend().setAlignment(Qt.AlignBottom)
        view = QChartView(chart)
        view.setRenderHint(QPainter.Antialiasing)
        return view

    @staticmethod
    def _style_chart(chart: "QChart") -> None:
        """Apply current-theme styling to a chart."""
        theme_name = current_theme_name()
        if theme_name == "Dark":
            chart.setTheme(QChart.ChartThemeDark)
            chart.setBackgroundBrush(QColor("#1e1e1e"))
            chart.setTitleBrush(QColor("#ddd"))
        elif theme_name == "Blue Accent":
            chart.setTheme(QChart.ChartThemeBlueIcy)
            chart.setBackgroundBrush(QColor("#f0f4fa"))
            chart.setTitleBrush(QColor("#333"))
        else:
            chart.setTheme(QChart.ChartThemeLight)
            chart.setBackgroundBrush(QColor("#ffffff"))
            chart.setTitleBrush(QColor("#333"))
        chart.setBackgroundRoundness(8)

    def _log(self, msg: str) -> None:
        if hasattr(self._mw, "log"):
            self._mw.log(msg)

    @Slot()
    def _all_time(self) -> None:
        self._use_all_time = True
        self.refresh()

    @Slot()
    def _last_7(self) -> None:
        self._use_all_time = False
        self._set_range(7)

    @Slot()
    def _last_30(self) -> None:
        self._use_all_time = False
        self._set_range(30)

    def _set_range(self, days: int) -> None:
        from PySide6.QtCore import QDate
        end = QDate.currentDate()
        start = end.addDays(-days)
        self._from_edit.setDate(start)
        self._to_edit.setDate(end)
        self.refresh()

    @Slot()
    def refresh(self) -> None:
        """Recompute analytics data and repaint all charts."""
        if getattr(self, "_use_all_time", False):
            start_date = None
            end_date = None
        else:
            start_date = parse_date(
                self._from_edit.date().toString("yyyy-MM-dd"))
            end_date = parse_date(
                self._to_edit.date().toString("yyyy-MM-dd"))

        prompts = []
        try:
            prompts = list(self._mw.prompt_database.prompts)
        except Exception:
            self._log("Analytics: could not read prompt database.")

        self._cache = compute_analytics_data(
            prompts, start_date, end_date,
            db=getattr(self._mw, "prompt_database", None))
        self._update_stats()
        if _CHARTS_AVAILABLE:
            self._draw_bar_chart()
            self._draw_pie_chart()
            self._draw_line_chart()
            self._draw_timeline()

    def _update_stats(self) -> None:
        d = self._cache
        if d is None:
            return
        self._card_total.set_value(d["total_prompts"])
        self._card_tokens.set_value(fmt_tokens(d["total_tokens"]))
        self._card_llms.set_value(d["unique_llms"])
        self._card_days.set_value(d["active_days"])

    def _draw_bar_chart(self) -> None:
        data = self._cache["prompts_by_date"]  # [(date_str, count), ...]
        chart = QChart()
        chart.setTitle("Prompts per Day")
        chart.setAnimationOptions(QChart.SeriesAnimations)

        bar_set = QBarSet("Prompts")
        bar_set.setColor(QColor(CHART_PALETTE[0]))
        categories = []
        for date_str, count in data:
            bar_set.append(count)
            categories.append(date_str)

        series = QBarSeries()
        series.append(bar_set)
        chart.addSeries(series)

        # Category axis (X)
        axis_x = QBarCategoryAxis()
        axis_x.append(categories)
        if len(categories) > 15:
            axis_x.setLabelsAngle(-45)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        # Value axis (Y)
        axis_y = QValueAxis()
        axis_y.setTitleText("Count")
        axis_y.setLabelFormat("%d")
        max_val = max((c for _, c in data), default=1)
        axis_y.setRange(0, max_val + 1)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        chart.legend().setVisible(False)
        self._style_chart(chart)
        self._cv_bar.setChart(chart)

    def _draw_pie_chart(self) -> None:
        data = self._cache["llm_distribution"]  # [(name, count), ...]
        chart = QChart()
        chart.setTitle("LLM Distribution")
        chart.setAnimationOptions(QChart.SeriesAnimations)

        series = QPieSeries()
        for i, (name, count) in enumerate(data):
            sl = series.append(name, count)
            colour = QColor(CHART_PALETTE[i % len(CHART_PALETTE)])
            sl.setColor(colour)
            sl.setBorderColor(colour.darker(120))
            # Explode the largest slice slightly
            if i == 0 and len(data) > 1:
                sl.setExploded(True)
                sl.setExplodeDistanceFactor(0.04)
            sl.setLabelVisible(True)
            pct = count / max(sum(c for _, c in data), 1) * 100
            sl.setLabel(f"{name} ({pct:.0f}%)")

        chart.addSeries(series)
        chart.legend().setAlignment(Qt.AlignRight)
        self._style_chart(chart)
        self._cv_pie.setChart(chart)

    def _draw_line_chart(self) -> None:
        data = self._cache["tokens_by_date"]  # [(date_str, tokens), ...]
        chart = QChart()
        chart.setTitle("Token Usage Over Time")
        chart.setAnimationOptions(QChart.SeriesAnimations)

        series = QLineSeries()
        series.setName("Tokens")
        series.setColor(QColor(CHART_PALETTE[2]))

        min_ms = None
        max_ms = None
        max_tokens = 0
        for date_str, tokens in data:
            dt = QDateTime.fromString(date_str, "yyyy-MM-dd")
            ms = dt.toMSecsSinceEpoch()
            series.append(ms, tokens)
            if min_ms is None or ms < min_ms:
                min_ms = ms
            if max_ms is None or ms > max_ms:
                max_ms = ms
            if tokens > max_tokens:
                max_tokens = tokens

        chart.addSeries(series)

        # Date axis (X)
        axis_x = QDateTimeAxis()
        axis_x.setFormat("yyyy-MM-dd")
        axis_x.setTitleText("Date")
        if min_ms is not None and max_ms is not None:
            axis_x.setRange(
                QDateTime.fromMSecsSinceEpoch(min_ms),
                QDateTime.fromMSecsSinceEpoch(max_ms),
            )
        if len(data) > 15:
            axis_x.setLabelsAngle(-45)
        chart.addAxis(axis_x, Qt.AlignBottom)
        series.attachAxis(axis_x)

        # Value axis (Y)
        axis_y = QValueAxis()
        axis_y.setTitleText("Tokens")
        axis_y.setLabelFormat("%d")
        axis_y.setRange(0, max_tokens * 1.1 if max_tokens else 1)
        chart.addAxis(axis_y, Qt.AlignLeft)
        series.attachAxis(axis_y)

        chart.legend().setVisible(False)
        self._style_chart(chart)
        self._cv_line.setChart(chart)

    def _draw_timeline(self) -> None:
        events = self._cache["timeline_events"]
        chart = QChart()
        chart.setTitle("Activity Timeline")
        chart.setAnimationOptions(QChart.NoAnimation)

        # Group events by type so each gets its own coloured series
        type_events: dict[str, list] = {}
        for ev in events:
            t = ev["type"]
            type_events.setdefault(t, []).append(ev)

        min_ms = None
        max_ms = None

        # Y position: stack events per type for visual separation
        type_y = {t: idx + 1 for idx, t in enumerate(sorted(type_events))}
        max_y = len(type_y) + 1

        for event_type, evts in type_events.items():
            colour_hex = EVENT_COLOURS.get(
                event_type, CHART_PALETTE[0]
            )
            colour = QColor(colour_hex)
            y = type_y[event_type]

            scatter = QScatterSeries()
            scatter.setName(event_type.replace("_", " ").title())
            scatter.setColor(colour)
            scatter.setMarkerSize(10)
            scatter.setBorderColor(colour.darker(120))

            for ev in evts:
                dt = QDateTime(
                    ev["time"].year,
                    ev["time"].month,
                    ev["time"].day,
                    ev["time"].hour,
                    ev["time"].minute,
                    ev["time"].second,
                )
                ms = dt.toMSecsSinceEpoch()
                scatter.append(ms, y)
                if min_ms is None or ms < min_ms:
                    min_ms = ms
                if max_ms is None or ms > max_ms:
                    max_ms = ms

            chart.addSeries(scatter)

        # Date axis (X)
        axis_x = QDateTimeAxis()
        axis_x.setFormat("yyyy-MM-dd")
        axis_x.setTitleText("Date")
        if min_ms is not None and max_ms is not None:
            # Add a small padding so edge points aren't clipped
            pad = max((max_ms - min_ms) * 0.02, 3_600_000)
            axis_x.setRange(
                QDateTime.fromMSecsSinceEpoch(int(min_ms - pad)),
                QDateTime.fromMSecsSinceEpoch(int(max_ms + pad)),
            )
        if len(events) > 30:
            axis_x.setLabelsAngle(-45)
        chart.addAxis(axis_x, Qt.AlignBottom)

        # Value axis (Y) – one tick per event type
        axis_y = QValueAxis()
        axis_y.setTitleText("Event Type")
        axis_y.setRange(0, max_y)
        axis_y.setTickCount(max_y + 1)
        axis_y.setLabelFormat("%d")
        chart.addAxis(axis_y, Qt.AlignLeft)

        # Attach axes to all series
        for s in chart.series():
            s.attachAxis(axis_x)
            s.attachAxis(axis_y)

        chart.legend().setAlignment(Qt.AlignBottom)
        self._style_chart(chart)
        self._cv_timeline.setChart(chart)
