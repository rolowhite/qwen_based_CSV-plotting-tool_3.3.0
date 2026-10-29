"""Your profile: a dashboard of what you did in CSV Plot Studio (plots, files, features, exports).

The pictures (tiles with a soft light from the top, the calendar, the level ring) are drawn on one canvas in
the app's own colours and fonts; every control on it (back, theme, edit profile, the range chips, view all,
choose a graph) is a real ttk widget, so it works from the keyboard like the rest of the app. All numbers come
from core.activity: nothing is made up, and an empty history says how to start.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import tkinter as tk
from tkinter import font as tkfont
from tkinter import ttk

from . import settings
from .core.activity import LEVEL_XP, XP, summarize_dashboard
from .skin import draw_icon, mix, png_data
from .theme import C
from .widgets import SmoothScroller

AVATARS = (("engineer-rabbit", "Engineer rabbit"), ("data-crow", "Data scientist crow"),
           ("case-fox", "Case analyser fox"))
AVATAR_DIR = Path(__file__).resolve().parent / "assets" / "avatars"
MAX_WIDTH = 1180
GAP = 16


class ProfilePage(ttk.Frame):
    def __init__(self, master, app):
        super().__init__(master)
        self.app = app
        px = app.theme.px
        self.range_var = tk.StringVar(value="Year")
        self._images = {}
        self._sizes = {}                 # placed control -> (width, height)
        self._drawn = None               # what the canvas shows: (width, summary, profile)
        self._width = 0
        self._pending = None

        head = ttk.Frame(self, style="Card.TFrame", padding=(px(14), px(10)))
        head.pack(fill="x", padx=px(12), pady=(px(12), 0))
        bar = tk.Frame(head, background=C["panel"])
        bar.pack(fill="x")
        from .app import back_button, theme_button          # the same header controls as the other pages
        back_button(bar, app).pack(side="left")
        ttk.Label(bar, text="Your profile", style="Panel.H3.TLabel").pack(side="left", padx=(px(14), 0))
        theme_button(bar, app).pack(side="right")
        self.workspace_btn = ttk.Button(bar, text="Back to the workspace", style="Panel.Ghost.TButton",
                                        command=lambda: app.show("work"))

        self.canvas = tk.Canvas(self, highlightthickness=0, bd=0, yscrollincrement=1, background=C["bg"])
        self.canvas.pack(fill="both", expand=True)
        self.canvas.scroll_target = True                    # the app's smooth mouse-wheel scrolling
        self.canvas.smooth = SmoothScroller(self.canvas)
        self.canvas.bind("<Configure>", self._resized)

        # real controls placed on the canvas
        self.edit_btn = ttk.Button(self.canvas, text="Edit profile", command=self._edit_profile)
        self.chips = tk.Frame(self.canvas, background=C["panel"])
        self.chip_buttons = [ttk.Radiobutton(self.chips, text=mode, value=mode, variable=self.range_var,
                                             command=self.refresh) for mode in ("Month", "Quarter", "Year")]
        for chip in self.chip_buttons:
            chip.pack(side="left")
        self.all_btn = ttk.Button(self.canvas, text="View all", command=self._view_all)
        self.go_btn = ttk.Button(self.canvas, text="Choose a graph", command=lambda: app.show("gallery"))

    # ------------------------------------------------------------------ drawing helpers --
    def _font(self, role):
        return self.app.theme.pf.get(role) or self.app.theme.f[role]

    def _line(self, role):
        return tkfont.Font(root=self, font=self._font(role)).metrics("linespace")

    def _measure(self, role, text):
        return tkfont.Font(root=self, font=self._font(role)).measure(str(text))

    def _photo(self, key, make):
        if key not in self._images:
            self._images[key] = tk.PhotoImage(master=self.app, data=png_data(make()))
        return self._images[key]

    def _tile(self, x, y, w, h, *, radius=14, top=None, bottom=None, border=None):
        """A rounded tile with a vertical gradient (top -> bottom colour) and a hairline edge."""
        from PIL import Image, ImageDraw

        px = self.app.theme.px
        top, bottom, border = top or C["panel"], bottom or C["panel"], border or C["border"]
        w, h = max(2, int(w)), max(2, int(h))

        def make():
            s = 3
            img = Image.new("RGBA", (w * s, h * s), (0, 0, 0, 0))
            grad = Image.new("RGBA", (1, h * s))
            a, b = (int(top[i:i + 2], 16) for i in (1, 3, 5)), (int(bottom[i:i + 2], 16) for i in (1, 3, 5))
            a, b = list(a), list(b)
            for yy in range(h * s):
                k = yy / max(1, h * s - 1)
                grad.putpixel((0, yy), tuple(round(a[i] + (b[i] - a[i]) * k) for i in range(3)) + (255,))
            r = px(radius) * s
            mask = Image.new("L", img.size, 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius=r, fill=255)
            img.paste(grad.resize(img.size), (0, 0), mask)
            ImageDraw.Draw(img).rounded_rectangle((0, 0, w * s - 1, h * s - 1), radius=r, outline=border,
                                                  width=max(1, s))
            return img.resize((w, h), Image.LANCZOS)

        self.canvas.create_image(x, y, image=self._photo(("tile", w, h, radius, top, bottom, border), make),
                                 anchor="nw")

    def _card(self, x, y, w, h, highlight=False):
        """The dashboard's card: a soft warm light at the top fading into the card colour. Returns what
        `_place` needs to give a control on it the right background."""
        dark = self.app.theme.dark
        top = mix(C["panel"], C["accent"], (0.12 if dark else 0.07) if highlight else (0.045 if dark else 0.025))
        self._tile(x, y, w, h, top=top, bottom=C["panel"], border=C["accent_line"] if highlight else C["border"])
        return (y, h, top, C["panel"])

    def _place(self, widget, base, x, y, card, anchor="nw"):
        """Put a real ttk control on the canvas, its transparent corners in the card colour at that height."""
        h = self._size(widget)[1]
        middle = y + (h // 2 if anchor.startswith("n") else 0 if anchor in ("e", "w", "center") else -h // 2)
        cy, ch, top, bottom = card
        colour = mix(top, bottom, min(1.0, max(0.0, (middle - cy) / max(1, ch))))
        style = f"P{colour[1:]}.{base}"
        ttk.Style(self).configure(style, background=colour)
        targets = widget.winfo_children() if isinstance(widget, tk.Frame) else [widget]
        if isinstance(widget, tk.Frame):
            widget.configure(background=colour)
        for w in targets:
            w.configure(style=style)
        return self._window(widget, x, y, anchor)

    def _icon(self, name, x, y, size, color, box=None):
        """An icon centred on (x, y), optionally on a soft rounded square of side `box`."""
        px = self.app.theme.px
        if box:
            self._tile(x - px(box) // 2, y - px(box) // 2, px(box), px(box), radius=10,
                       top=box_fill(color, 0.20), bottom=box_fill(color, 0.12), border=box_fill(color, 0.22))
        img = self._photo(("icon", name, size, color), lambda: draw_icon(name, px(size), color, stroke=1.8))
        self.canvas.create_image(x, y, image=img, anchor="center")

    def _text(self, x, y, text, role="body", color=None, anchor="nw", width=None):
        opts = dict(text=str(text), anchor=anchor, fill=color or C["text"], font=self._font(role),
                    justify="center" if anchor in ("n", "s", "center") else "left")
        if width:
            opts["width"] = max(10, int(width))
        item = self.canvas.create_text(x, y, **opts)
        box = self.canvas.bbox(item)
        return box[3] - box[1] if box else 0

    def _window(self, widget, x, y, anchor="nw"):
        self.canvas.create_window(x, y, window=widget, anchor=anchor)
        return self._size(widget)

    def _size(self, widget):
        """The control's size, measured once per look: update_idletasks redraws the whole window, which is slow."""
        if widget not in self._sizes:
            widget.update_idletasks()
            self._sizes[widget] = widget.winfo_reqwidth(), widget.winfo_reqheight()
        return self._sizes[widget]

    # ------------------------------------------------------------------------ pages --
    def on_show(self):
        if self.app.dataset is not None:
            self.workspace_btn.pack(side="right", padx=(0, self.app.theme.px(8)))
        else:
            self.workspace_btn.pack_forget()
        self.refresh()

    def on_theme(self):
        self._images.clear()
        self._sizes.clear()
        self._drawn = None
        refresh_profile_buttons(self.app)
        self.chips.configure(background=C["panel"])
        if self.app.current == "profile":           # hidden: on_show draws it in the new look
            self.refresh()

    def _resized(self, event):
        if event.width > 1 and abs(event.width - self._width) >= 8:
            self._width = event.width
            if self._pending:
                self.after_cancel(self._pending)
            self._pending = self.after(60, self.refresh)

    def refresh(self):
        self._pending = None
        width = self.canvas.winfo_width()
        if width <= 1:
            return
        summary = summarize_dashboard(self.app.cfg, range_mode=self.range_var.get())
        drawn = (width, summary, repr(self._profile()))
        if drawn == self._drawn:
            return                      # nothing on it changed since it was drawn: redrawing takes ~0.3 s
        self._drawn = drawn
        top = self.canvas.yview()[0]
        self.canvas.delete("all")
        self.canvas.configure(background=C["bg"])
        self.summary = summary
        height = self._render(width)
        self.canvas.configure(scrollregion=(0, 0, width, height))
        self.canvas.yview_moveto(top)
        self.canvas.update_idletasks()

    def _render(self, width):
        px, s, p = self.app.theme.px, self.summary, self._profile()
        gap = px(GAP)
        shell = min(width - 2 * px(24), px(MAX_WIDTH))
        x0 = (width - shell) // 2
        narrow = shell < px(900)
        y = px(28)

        # ---- greeting and identity -----------------------------------------------------------
        ident_w = shell if narrow else px(400)
        ident_h = px(132)
        left_w = shell if narrow else shell - ident_w - gap
        hy = y + px(10)
        greeting = "Welcome" if self.summary.is_empty else "Welcome back"
        hy += self._text(x0, hy, f"{greeting}, {p['first_name']}.", "hero_h1", width=left_w)
        hy += px(6)
        hy += self._text(x0, hy, self._subtitle(), "body_lg", C["muted"], width=min(left_w, px(560)))
        ix, iy = (x0, hy + gap) if narrow else (x0 + shell - ident_w, y)
        ident_card = self._card(ix, iy, ident_w, ident_h, highlight=True)
        avatar = self._avatar(64)
        cy = iy + ident_h // 2
        self.canvas.create_image(ix + px(20), cy, image=avatar, anchor="w")
        tx = ix + px(20) + avatar.width() + px(16)
        name_h, sub_h = self._line("identity_name"), self._line("body_sm")
        block = name_h + px(2) + sub_h + px(10) + sub_h
        ty = cy - block // 2
        self._text(tx, ty, p["name"], "identity_name", width=ident_w - (tx - ix) - px(120))
        self._text(tx, ty + name_h + px(2), f"{p['knownAs']}, joined {p['joined']}", "body_sm", C["muted"])
        status_y = ty + name_h + px(2) + sub_h + px(10) + sub_h // 2
        today = s.cells and any(c.day_date == datetime.now().date() and (c.plots or c.files) for c in s.cells)
        dot = C["ok"] if today else C["faint"]
        r = px(4)
        self.canvas.create_oval(tx, status_y - r, tx + 2 * r, status_y + r, fill=dot, outline="")
        label = "Active today" if today else "Not active yet today"
        self._text(tx + 2 * r + px(6), status_y, label, "body_sm", C["muted"], anchor="w")
        sx = tx + 2 * r + px(6) + self._measure("body_sm", label) + px(16)
        self._icon("flame", sx + px(7), status_y, 14, C["accent"])
        streak = s.current_streak
        streak_text = ("Start a streak today" if not streak else
                       f"{streak} day streak" if streak != 1 else "1 day streak")
        self._text(sx + px(18), status_y, streak_text, "body_sm", C["muted"], anchor="w")
        self._place(self.edit_btn, "TButton", ix + ident_w - px(16), iy + px(16), ident_card, anchor="ne")
        y = max(hy, iy + ident_h) + px(24) if not narrow else iy + ident_h + px(24)

        # ---- four numbers ------------------------------------------------------------------
        cols = 2 if narrow else 4
        card_w = (shell - (cols - 1) * gap) // cols
        card_h = px(104)
        stats = [
            ("Plots drawn", f"{s.total_plots:,}", f"{s.plots_this_month:,} this month", "chart_bars"),
            ("Current streak", f"{s.current_streak} day{'s' if s.current_streak != 1 else ''}",
             f"Best: {s.longest_streak} day{'s' if s.longest_streak != 1 else ''}", "flame"),
            ("Active days", f"{s.active_days_90d:,}", "in the last 90 days", "calendar"),
            ("Files explored", f"{s.datasets_explored:,}", f"{s.total_rows_explored:,} rows in all", "data"),
        ]
        for i, (label, value, detail, icon) in enumerate(stats):
            cx = x0 + (i % cols) * (card_w + gap)
            cyy = y + (i // cols) * (card_h + gap)
            self._card(cx, cyy, card_w, card_h, highlight=i == 0)
            self._icon(icon, cx + px(20) + px(20), cyy + card_h // 2, 20, C["accent"] if i == 0 else C["muted"],
                       box=40)
            tx = cx + px(76)
            lh, vh, dh = self._line("label"), self._line("stat_value"), self._line("body_sm")
            ty = cyy + (card_h - (lh + vh + dh)) // 2
            self._text(tx, ty, label, "label", C["muted"])
            self._text(tx, ty + lh, value, "stat_value")
            self._text(tx, ty + lh + vh, detail, "body_sm", C["accent"] if i == 0 else C["muted"])
        y += (card_h + gap) * ((len(stats) + cols - 1) // cols) - gap + px(24)

        # ---- calendar + level -----------------------------------------------------------------
        cal_w = shell if narrow else int((shell - gap) * 0.68)
        lvl_w = shell if narrow else shell - cal_w - gap
        weeks = max((c.week_index for c in s.cells), default=0) + 1
        cell = max(px(6), min(px(16), (cal_w - px(48) - px(30)) // weeks - px(3)))
        cal_h = max(px(300), px(86) + self._line("summary_num") + self._line("label") + px(30)
                    + 7 * (cell + px(3)) + px(48))
        cal_card = self._card(x0, y, cal_w, cal_h)
        self._heading(x0 + px(24), y + px(22), "Plotting activity", "How often you drew plots")
        self._place(self.chips, "Chip.TRadiobutton", x0 + cal_w - px(22), y + px(22), cal_card, anchor="ne")
        self._calendar(x0 + px(24), y + px(86), cal_w - px(48), cal_h - px(110))
        if narrow:
            y += cal_h + gap
            self._level(x0, y, lvl_w, px(330))
            y += px(330) + px(24)
        else:
            self._level(x0 + cal_w + gap, y, lvl_w, cal_h)
            y += cal_h + px(24)

        # ---- recent work + badges -----------------------------------------------------------
        rec_w = shell if narrow else int((shell - gap) * 0.54)
        bad_w = shell if narrow else shell - rec_w - gap
        row_h = px(272)
        rec_card = self._card(x0, y, rec_w, row_h)
        self._heading(x0 + px(24), y + px(22), "Recent activity", "What you did last")
        self._recent(x0, y, rec_w)
        if s.recent_events:
            self._place(self.all_btn, "Link.TButton", x0 + rec_w - px(18), y + px(20), rec_card, anchor="ne")
        bx, by = (x0, y + row_h + gap) if narrow else (x0 + rec_w + gap, y)
        self._card(bx, by, bad_w, row_h)
        self._heading(bx + px(24), by + px(22), "Badges", f"{s.badges_earned} of {len(s.badges)} earned")
        self._badges(bx, by, bad_w)
        y = (by if narrow else y) + row_h + px(24)

        # ---- this week ---------------------------------------------------------------------------
        band_h = px(104)
        band_card = self._card(x0, y, shell, band_h, highlight=True)
        self._icon("chart_bars", x0 + px(24) + px(22), y + band_h // 2, 22, C["accent"], box=44)
        tx = x0 + px(88)
        if s.week_graph_uses:
            title = f"{s.week_graph_name} was your go-to graph this week"
            detail = (f"You drew it {s.week_graph_uses} time{'s' if s.week_graph_uses != 1 else ''} "
                      f"with {s.week_datasets} file{'s' if s.week_datasets != 1 else ''}.")
        else:
            title = "No plots this week yet"
            detail = "Pick a graph, load a file, and your week shows up here."
        th, dh = self._line("insight_h2"), self._line("body_sm")
        ty = y + (band_h - th - px(4) - dh) // 2
        self._text(tx, ty, title, "insight_h2", width=shell - px(300))
        self._text(tx, ty + th + px(4), detail, "body_sm", C["muted"], width=shell - px(300))
        self._place(self.go_btn, "Accent.TButton", x0 + shell - px(24), y + band_h // 2, band_card, anchor="e")
        return y + band_h + px(40)

    def _subtitle(self) -> str:
        s = self.summary
        if s.is_empty:
            return "This is where your plotting history will grow. Load a file and draw your first plot."
        files = s.datasets_explored
        return (f"{s.plots_this_month:,} plot{'s' if s.plots_this_month != 1 else ''} this month, "
                f"{files:,} file{'s' if files != 1 else ''} explored so far. Keep going.")

    def _heading(self, x, y, title, sub):
        h = self._text(x, y, title, "panel_h2")
        self._text(x, y + h + self.app.theme.px(2), sub, "body_sm", C["muted"])

    def _levels(self):
        """Five steps from 'no plots' to 'many', in the app's accent."""
        empty = mix(C["panel"], C["text"], 0.07 if self.app.theme.dark else 0.06)
        return [empty] + [mix(C["panel"], C["accent"], k) for k in (0.3, 0.52, 0.76, 1.0)]

    def _calendar(self, x, y, w, h):
        px, s = self.app.theme.px, self.summary
        lh = self._line("label")
        self._text(x, y, f"{s.active_days_range:,}", "summary_num")
        nh = self._line("summary_num")
        self._text(x, y + nh, "active days", "body_sm", C["muted"])
        mx = x + max(self._measure("summary_num", f"{s.active_days_range:,}"),
                     self._measure("body_sm", "active days")) + px(28)
        self.canvas.create_line(mx - px(14), y + px(4), mx - px(14), y + nh + lh, fill=C["border"])
        self._text(mx, y, f"{s.plots_range:,}", "summary_num")
        self._text(mx, y + nh, "plots", "body_sm", C["muted"])
        if s.quarter_plots or s.last_quarter_plots:
            self._text(x + w, y + px(6), f"{s.quarter_plots:,} plots this quarter, {s.last_quarter_plots:,} last "
                                         "quarter", "body_sm", C["muted"], anchor="ne")

        weeks = max((c.week_index for c in s.cells), default=0) + 1
        label_w = px(30)
        gy = y + nh + lh + px(30)
        avail_h = h - (gy - y) - px(26)
        cell = max(px(6), min(px(16), (w - label_w) // weeks - px(3), avail_h // 7 - px(3)))
        step = cell + px(3)
        gx = x + label_w
        for week, name in s.month_headers:
            self._text(gx + week * step, gy - px(6), name, "tiny", C["faint"], anchor="sw")
        for day, name in ((0, "Mon"), (2, "Wed"), (4, "Fri")):
            self._text(gx - px(8), gy + day * step + cell // 2, name, "tiny", C["faint"], anchor="e")
        colours = self._levels()
        for c in s.cells:
            cx, cy = gx + c.week_index * step, gy + c.weekday * step
            tag = "day_" + c.date_iso
            self.canvas.create_rectangle(cx, cy, cx + cell, cy + cell, fill=colours[c.level], outline="",
                                         tags=(tag,))
            self.canvas.tag_bind(tag, "<Enter>", lambda e, c=c: self._tip(e, c.tooltip_text))
            self.canvas.tag_bind(tag, "<Leave>", lambda _e: self.canvas.delete("tip"))
        ly = gy + 7 * step + px(8)
        lx = gx + weeks * step - px(3)
        self._text(lx, ly, "More", "tiny", C["faint"], anchor="ne")
        lx -= self._measure("tiny", "More") + px(6)
        for colour in reversed(colours):
            self.canvas.create_rectangle(lx - px(10), ly + px(2), lx, ly + px(12), fill=colour, outline="")
            lx -= px(13)
        self._text(lx - px(3), ly, "Less", "tiny", C["faint"], anchor="ne")

    def _tip(self, event, text):
        px = self.app.theme.px
        self.canvas.delete("tip")
        x, y = self.canvas.canvasx(event.x) + px(12), self.canvas.canvasy(event.y) - px(30)
        item = self.canvas.create_text(x + px(8), y + px(6), text=text, anchor="nw", fill=C["tip_fg"],
                                       font=self._font("body_sm"), tags=("tip",))
        x0, y0, x1, y1 = self.canvas.bbox(item)
        if x1 + px(8) > self.canvas.winfo_width():
            self.canvas.move(item, self.canvas.winfo_width() - x1 - px(16), 0)
            x0, y0, x1, y1 = self.canvas.bbox(item)
        self.canvas.create_rectangle(x0 - px(8), y0 - px(5), x1 + px(8), y1 + px(5), fill=C["tip_bg"],
                                     outline="", tags=("tip",))
        self.canvas.tag_raise(item)

    def _level(self, x, y, w, h):
        from PIL import Image, ImageDraw

        px, s = self.app.theme.px, self.summary
        self._card(x, y, w, h)
        self._heading(x + px(24), y + px(22), f"Level {s.level}", s.level_name)
        d = min(px(128), w - px(80))
        ring_y = y + px(90)

        def make():
            k = 4
            big = d * k
            img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            stroke = px(10) * k
            box = (stroke // 2, stroke // 2, big - stroke // 2 - 1, big - stroke // 2 - 1)
            draw.arc(box, 0, 360, fill=mix(C["panel"], C["text"], 0.10), width=stroke)
            share = s.xp_progress / LEVEL_XP
            if share > 0:
                draw.arc(box, -90, -90 + 360 * share, fill=C["accent"], width=stroke)
            return img.resize((d, d), Image.LANCZOS)

        ring = self._photo(("ring", d, s.xp_progress, C["accent"], C["panel"]), make)
        cx = x + w // 2
        self.canvas.create_image(cx, ring_y, image=ring, anchor="n")
        self._text(cx, ring_y + d // 2 - px(2), f"{s.xp_progress * 100 // LEVEL_XP}%", "ring_value", anchor="s")
        self._text(cx, ring_y + d // 2 + px(2), f"to level {s.level + 1}", "body_sm", C["muted"], anchor="n")
        ty = ring_y + d + px(18)
        left = LEVEL_XP - s.xp_progress
        ty += self._text(cx, ty, f"{left:,} XP to go", "card_title", anchor="n")
        self._text(cx, ty + px(4), f"Each plot gives {XP['plot']} XP, a file {XP['file']}, an export "
                                   f"{XP['export']} and a new feature {XP['feature']}.", "body_sm", C["muted"],
                   anchor="n", width=w - px(48))

    def _recent(self, x, y, w):
        px, events = self.app.theme.px, self.summary.recent_events[:3]
        top = y + px(84)
        if not events:
            self._text(x + px(24), top, "Nothing yet. Your plots, features and exports will be listed here.",
                       "body_sm", C["muted"], width=w - px(48))
            return
        kinds = {"feature": ("spark", C["warn"]), "code": ("code_slash", C["ok"])}
        row = px(58)
        for i, event in enumerate(events):
            ry = top + i * row
            if i:
                self.canvas.create_line(x + px(24), ry - px(9), x + w - px(24), ry - px(9), fill=C["border"])
            icon, colour = kinds.get(event.get("kind"), ("chart_bars", C["accent"]))
            mid = ry + px(18)
            self._icon(icon, x + px(24) + px(18), mid, 18, colour, box=36)
            tx = x + px(78)
            when = _when(event.get("time"))
            when_w = self._measure("body_sm", when)
            th = self._line("card_title")
            self._text(tx, mid - th, _clip(event.get("title", ""), 60), "card_title", width=w - (tx - x) - when_w - px(40))
            self._text(tx, mid + px(1), _clip(event.get("detail", ""), 70), "body_sm", C["muted"],
                       width=w - (tx - x) - when_w - px(40))
            self._text(x + w - px(24), mid - th // 2, when, "body_sm", C["faint"], anchor="ne")

    def _badges(self, x, y, w):
        px, badges = self.app.theme.px, self.summary.badges
        top = y + px(84)
        cols = 2
        bw = (w - px(48) - px(10)) // cols
        bh = px(50)
        for i, b in enumerate(badges):
            bx = x + px(24) + (i % cols) * (bw + px(10))
            by = top + (i // cols) * (bh + px(8))
            fill = mix(C["panel"], C["accent"], 0.10 if self.app.theme.dark else 0.06) if b.earned else None
            self._tile(bx, by, bw, bh, radius=10, top=fill or mix(C["panel"], C["text"], 0.03),
                       bottom=fill or mix(C["panel"], C["text"], 0.03),
                       border=C["accent_line"] if b.earned else C["border"])
            self._icon("check" if b.earned else b.icon, bx + px(22), by + bh // 2, 16,
                       C["accent"] if b.earned else C["faint"])
            th = self._line("card_title")
            ty = by + (bh - th - self._line("tiny")) // 2
            self._text(bx + px(42), ty, b.title, "card_title", C["text"] if b.earned else C["muted"],
                       width=bw - px(110))
            self._text(bx + px(42), ty + th, b.detail, "tiny", C["faint"], width=bw - px(110))
            self._text(bx + bw - px(12), by + bh // 2, b.progress, "tiny",
                       C["accent"] if b.earned else C["faint"], anchor="e")

    # -------------------------------------------------------------------- profile --
    def _profile(self):
        p = self.app.cfg.get("profile")
        if not isinstance(p, dict) or "first_name" not in p:
            p = settings._profile(p)
            self.app.cfg["profile"] = p
        return p

    def _avatar(self, size, avatar_id=None):
        return avatar_image(self.app, avatar_id or self._profile().get("selectedAvatar", AVATARS[0][0]), size)

    def _edit_profile(self):
        t, px = self.app.theme, self.app.theme.px
        p = self._profile()
        win = tk.Toplevel(self.app)
        win.title("Edit profile")
        win.transient(self.app)
        win.resizable(False, False)
        win.configure(background=C["bg"])
        t.dark_title_bar(win)
        card = ttk.Frame(win, style="Card.TFrame", padding=(px(24), px(20)))
        card.pack(fill="both", expand=True, padx=px(12), pady=px(12))
        body = tk.Frame(card, background=C["panel"])
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Edit profile", style="Panel.H2.TLabel").grid(row=0, column=0, columnspan=3, sticky="w")
        ttk.Label(body, text="Pick the character that works like you do.", style="Panel.Muted.TLabel").grid(
            row=1, column=0, columnspan=3, sticky="w", pady=(px(2), px(14)))
        chosen = tk.StringVar(value=p["selectedAvatar"])
        win._pictures = []
        for col, (avatar_id, label) in enumerate(AVATARS):
            pic = self._avatar(64, avatar_id)
            win._pictures.append(pic)
            ttk.Radiobutton(body, text=label, image=pic, compound="top", value=avatar_id, variable=chosen,
                            style="Chip.TRadiobutton").grid(row=2, column=col, sticky="nsew", padx=px(4))
            body.columnconfigure(col, weight=1, uniform="avatar")
        fields = {}
        for col, (label, key) in enumerate((("Name", "name"), ("Known as", "knownAs"))):
            box = tk.Frame(body, background=C["panel"])
            box.grid(row=3, column=0 if col == 0 else 1, columnspan=1 if col == 0 else 2, sticky="ew",
                     padx=px(4), pady=(px(18), 0))
            ttk.Label(box, text=label, style="Panel.Medium.TLabel").pack(anchor="w", pady=(0, px(4)))
            var = tk.StringVar(value=p[key])
            entry = ttk.Entry(box, textvariable=var)
            entry.pack(fill="x")
            fields[key] = var
            if col == 0:
                entry.focus_set()

        def save():
            name = fields["name"].get().strip()
            p.update(name=name, knownAs=fields["knownAs"].get().strip(), selectedAvatar=chosen.get())
            self.app.cfg["profile"] = settings._profile(p)
            settings.save(self.app.cfg)
            refresh_profile_buttons(self.app)
            self._images.clear()
            win.destroy()
            self.refresh()

        buttons = tk.Frame(body, background=C["panel"])
        buttons.grid(row=4, column=0, columnspan=3, sticky="e", pady=(px(22), 0))
        ttk.Button(buttons, text="Cancel", style="TButton", command=win.destroy).pack(side="left", padx=(0, px(8)))
        ttk.Button(buttons, text="Save profile", style="Panel.Accent.TButton", command=save).pack(side="left")
        win.bind("<Return>", lambda _e: save())
        win.bind("<Escape>", lambda _e: win.destroy())
        _center(win, self.app)
        win.grab_set()

    def _view_all(self):
        t, px = self.app.theme, self.app.theme.px
        win = tk.Toplevel(self.app)
        win.title("Recent activity")
        win.transient(self.app)
        win.configure(background=C["bg"])
        t.dark_title_bar(win)
        card = ttk.Frame(win, style="Card.TFrame", padding=(px(22), px(18)))
        card.pack(fill="both", expand=True, padx=px(12), pady=px(12))
        body = tk.Frame(card, background=C["panel"])
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Recent activity", style="Panel.H2.TLabel").grid(row=0, column=0, columnspan=2,
                                                                            sticky="w", pady=(0, px(10)))
        for i, event in enumerate(self.summary.recent_events[:30], start=1):
            ttk.Label(body, text=event.get("title", ""), style="Panel.Bold.TLabel").grid(row=2 * i - 1, column=0,
                                                                                       sticky="w", pady=(px(6), 0))
            ttk.Label(body, text=_when(event.get("time")), style="Panel.Faint.TLabel").grid(
                row=2 * i - 1, column=1, sticky="e", padx=(px(24), 0), pady=(px(6), 0))
            ttk.Label(body, text=event.get("detail", ""), style="Panel.Muted.TLabel").grid(row=2 * i, column=0,
                                                                                         columnspan=2, sticky="w")
        ttk.Button(body, text="Close", style="TButton", command=win.destroy).grid(row=99, column=1, sticky="e",
                                                                                pady=(px(16), 0))
        win.bind("<Escape>", lambda _e: win.destroy())
        _center(win, self.app)


def avatar_image(app, avatar_id, size):
    """The chosen character in a circle with an accent ring (pixel-art edges kept), cached per look."""
    from PIL import Image, ImageDraw

    d = max(1, app.theme.px(size))
    cache = app.__dict__.setdefault("_avatar_cache", {})
    key = (avatar_id, d, C["accent"])
    if key not in cache:
        k = 4
        src = Image.open(AVATAR_DIR / f"{avatar_id}.png").convert("RGBA").resize((d * k, d * k), Image.NEAREST)
        mask = Image.new("L", src.size, 0)
        ImageDraw.Draw(mask).ellipse((0, 0, d * k - 1, d * k - 1), fill=255)
        out = Image.new("RGBA", src.size, (0, 0, 0, 0))
        out.paste(src, (0, 0), mask)
        ImageDraw.Draw(out).ellipse((k, k, d * k - 1 - k, d * k - 1 - k), outline=C["accent"], width=2 * k)
        cache[key] = tk.PhotoImage(master=app, data=png_data(out.resize((d, d), Image.LANCZOS)))
    return cache[key]


def refresh_profile_buttons(app):
    """The profile buttons in the page headers show the chosen character and first name."""
    p = settings._profile(app.cfg.get("profile"))
    for button in getattr(app, "_profile_buttons", []):
        try:
            button.configure(text=p["first_name"], image=avatar_image(app, p["selectedAvatar"], 22))
        except tk.TclError:
            pass


def box_fill(color, k):
    """A soft square behind an icon: the icon's colour mixed into the card."""
    return mix(C["panel"], color, k)


def _clip(text, n):
    text = str(text or "")
    return text if len(text) <= n else text[: n - 1] + "…"


def _when(value):
    text = str(value or "")
    try:
        stamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return text or "recently"
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    seconds = max(0, int((datetime.now().astimezone() - stamp.astimezone()).total_seconds()))
    if seconds < 3600:
        return f"{max(1, seconds // 60)} min ago"
    if seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    if seconds < 172800:
        return "Yesterday"
    return stamp.astimezone().strftime("%b %d")


def _center(win, parent):
    win.update_idletasks()
    w, h = win.winfo_reqwidth(), win.winfo_reqheight()
    x = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
    y = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
    win.geometry(f"+{x}+{y}")
