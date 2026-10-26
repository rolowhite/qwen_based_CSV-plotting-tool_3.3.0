# CSV Plot Studio design system (2.0, Feature Lab in 3.0)

The look is calm and precise: an instrument for reading data. Controls are flat (2D) with soft rounded
corners, layered surfaces instead of shadows, one accent colour per look, and IBM Plex as the voice.
The charts follow the same rules: thin lines, quiet frames, a palette that stays readable for colour-blind
readers.

Everything here is code: colours and type in `plotstudio/theme.py`, the drawn controls in
`plotstudio/skin.py`, the chart style in `plotstudio/engine.py` (`studio_rc`) and the dark graph paper in
`plotstudio/paper.py`. `tests/test_design.py` checks the contrast rules below.

## Principles

1. **The data is the loudest thing.** Chrome is neutral and recedes; the accent is kept for the one action
   that matters on a screen (Plot, Copy code, the chosen filter).
2. **No sharp corners.** Every control, card and well is rounded: 8 px controls, 12 px cards, pills for
   chips, switches and scrollbar thumbs. Charts drop their box (no top/right spines) for the same reason.
3. **Space separates, lines are a last resort.** 12 px gutters between cards; hairlines only where a scrolling
   area starts or ends.
4. **Feedback for every action.** Hover tint, a pressed state that sinks 1 px, a short halo after a click,
   a ring for keyboard focus, and text that changes ("Copied").
5. **Accessible by default.** WCAG 2.1 AA contrast in both looks, keyboard access everywhere, focus rings
   only when the keyboard is used (they don't flash on mouse clicks).

## Colour tokens

| Token | Light | Dark | Use |
|---|---|---|---|
| `bg` | `#f1f3f8` | `#121214` | window, behind the cards |
| `panel` | `#ffffff` | `#1c1c1f` | cards; also the graph paper (light paper / dark paper) |
| `raised` | `#f7f8fb` | `#242428` | secondary buttons, wells (data chip) |
| `field` | `#fdfdfe` | `#161619` | inputs, lists, tables (inset in the dark look) |
| `hover` / `pressed` | `#eef0f6` / `#e3e6ef` | `#2a2a2f` / `#323238` | state tints |
| `border` / `border_strong` | `#e2e6ee` / `#cdd3df` | `#2b2b30` / `#3a3a41` | hairlines, secondary outlines |
| `input_border` | `#8a93a6` | `#6c6c76` | outline of inputs (3:1, WCAG 1.4.11) |
| `text` / `muted` / `faint` | `#1a2030` / `#535c70` / `#646c7f` | `#ededf0` / `#a6a6b0` / `#93939d` | three text levels, all ≥ 4.5:1 |
| `accent` | `#b8461f` coral | `#f2764b` coral | primary actions, selection (one accent for the app and the profile) |
| `on_accent` | `#ffffff` | `#1a0e04` | text on the accent (dark ink on orange: 6.8:1; white was 2.8:1) |
| `accent_soft` / `select` | `#eef0ff` / `#e3e6ff` | `#35220f` / `#3d2610` | chosen chip, list selection |
| `focus_ring` | `#b8461f` | `#f39a77` | keyboard focus ring |
| `danger` / `warn` / `ok` | `#b42318` / `#8a4b08` / `#067647` | `#ff6b61` / `#f6b04a` / `#4ade80` | status text, always with words |
| `sev_warn` / `sev_check` | `#c2410c` / `#a16207` | `#ff8f4d` / `#f3c94a` | severity dots of the data notes (leakage uses `danger`), always next to words |

Rules: every colour that plain Tk widgets use is unique within its look, so the live light/dark switch can
recolour them by role. The dark card colour equals the dark graph paper, so a plot sits seamlessly on its card.

Gradients: primary and secondary buttons are lit from the top (lighter at the top edge, a little deeper at the
bottom), cards carry a soft warm light at their top edge that fades into the card colour, and the profile
dashboard's tiles use the same light. Data marks in charts stay flat on purpose: a gradient inside a bar or an area
changes how big it looks.

## Type

IBM Plex Sans for the interface and the charts, IBM Plex Mono for code (bundled, SIL Open Font License,
registered for this process only). If Tk can't use the bundled fonts (a Tk without anti-aliased fonts),
the system UI font is used instead.

| Role | Face | Size (pt; macOS +3) |
|---|---|---|
| H1 (app name) | Plex Sans SemiBold | 20 |
| H2 (page / graph name) | Plex Sans SemiBold | 15 |
| H3 (card titles, groups) | Plex Sans SemiBold | 12 |
| Body, inputs | Plex Sans Regular | 10 |
| Labels, buttons | Plex Sans Medium (Windows) / Regular | 10 |
| Small, hints | Plex Sans Regular | 9 |
| Tiny (book references) | Plex Sans Regular | 8 |
| Code | Plex Mono Regular, SemiBold for keywords, Italic for comments | 10 |

Sentence case everywhere ("Recent files", not "RECENT FILES"); no all-caps labels.

## Space, radius, elevation

* Spacing scale (px at 100 %): 4 · 8 · 12 · 16 · 20 · 24 · 32. Gutter between cards: 12. Card padding: 16–24.
* Radius: 8 controls and wells, 12 cards, pills (chips, switches, scrollbar thumbs, badges).
* Elevation is expressed by surface colour (window → card → raised well), never by drop shadows.
  Primary buttons carry a 1 px inner highlight at the top and a 1 px shade at the bottom: a hint of body that
  stays 2D.
* Every interactive picture keeps a 3 px transparent margin for the focus ring and the click halo; that margin
  is also what keeps neighbouring controls from touching.

## Motion

| Moment | Behaviour |
|---|---|
| Hover | instant tint (fill and outline) |
| Press | the control sinks 1 px on every side and darkens |
| Release (click) | an accent halo around the control: strong for 90 ms, faint for 130 ms, gone |
| Wheel scrolling | eased: each frame covers 30 % of the remaining distance (about 60 frames a second); notches add up |
| Keyboard focus | a 2 px ring 1 px outside the control, only after Tab / Shift+Tab |

## Components

| Component | Style name(s) | States |
|---|---|---|
| Primary button | `Accent.TButton`, `Big.Accent.TButton` | normal, hover, pressed, disabled, focus, halo |
| Secondary button | `TButton`, `Small.TButton` | + selected (toggle) |
| Ghost / link / icon button | `Ghost.TButton`, `Link.TButton`, `Icon.TButton`, `Toggle.TButton`, `Section.TButton` | + selected for the Pan / Box zoom tools |
| Menu button | `TMenubutton`, `Ghost.TMenubutton` | chevron inside the padding |
| Text field | `TEntry`, `Search.TEntry` (search icon), `TSpinbox` (chevron arrows) | hover, focus (accent outline + soft glow), disabled, invalid |
| Select | `TCombobox` (read-only) | behaves like a button: hover tint, pressed, focus ring |
| Check box / radio / switch | `TCheckbutton`, `TRadiobutton`, `Switch.TCheckbutton` | on/off × normal, hover, focus, disabled |
| Chip | `Chip.TRadiobutton` | chosen = soft accent pill |
| Tab | `TNotebook.Tab` | a pill on the window background; the chosen tab takes the card colour |
| Card | `Card.TFrame` | structural (left panel, tab content, load card) |
| Tile | `Tile.TFrame`, `Panel.Tile.TFrame` (`widgets.Tile`) | clickable card: hover, pressed, focus; Enter / Space open it |
| Well | `Well.TFrame`, `Inset.TFrame`, `Code.TFrame`, `Danger.TFrame`, `Warn.TFrame` | rounded boxes inside a card |
| Badge | `Badge.TLabel`, `SoftBadge.TLabel`, `MutedBadge.TLabel` | step numbers |
| Scrollbar | `*.TScrollbar` (+ `Hidden.` while nothing scrolls) | slim pill, wider and darker under the mouse |
| Ball slider | `widgets.RangeSlider` | keyboard: arrows, Shift+arrows, Space (other ball), Home / End, Escape |
| Idea card | `ideas.IdeaCard` (gallery) | a tile: rank badge, title, plot name in the accent colour, the reason |
| Suggestions table | `ideas.IdeasView` | one grid: rank badge · columns (bold) · plot type (accent) · reason with its numbers (faint) · *Plot it* (`Small.TButton`); hairlines between rows; warnings above it, the minor ones folded |
| Column types dialog | `ideas.TypesDialog` | a table (column · detected · use as), one select for the chosen row, *Apply and run again* as the primary button; changed rows in the accent colour |
| Severity dot | `ideas.Dot` | red leakage, orange important, yellow worth checking, grey good to know; redrawn on the look switch |
| Feature suggestion row | `featurelab.FeatureLabView._row` | rank badge (filled for the best recommended one) · name (bold) and what it is made from (faint) · gain bar + *MI before → after (gain)* · reason (muted, wraps to the width the row really has) · *Accept* + *Skip*; see below |
| Gain bar | `featurelab.GainBar` | MI before (grey) and after on one scale for the whole list; green = adds information, accent = same information, red = leakage, grey = weaker or redundant; redrawn on the look switch |
| Accepted-feature chip | `featurelab.FlowFrame` + soft-accent frame | name (small bold) and an × icon button; wraps to new lines; double-click renames |

Surface variants: transparent corners show the style's `background`, so styles come in surface flavours,
e.g. `Raised.Small.TButton` for a button inside a raised well, `Bg.Section.TButton` on the window background.

### Feature Lab (3.0)

The tab follows principle 1: one primary action per row at most.

* Only suggestions that **add information** get the primary *Accept* (`Accent.TButton`); the others get the
  secondary button, so the eye goes to the useful ones first. Leakage rows have a red dot, a disabled *Accept* with
  a tooltip saying why, and a *Accept anyway…* link that asks first. The status is always a word too
  (*Adds information*, *Leakage?*, *Redundant*, *Same information, new shape*, *Less than its source*), never colour
  alone.
* Layout: the list (about 57 % of the width at first, a sash to change it) and the preview (first 10 rows, then
  the distribution and the link with the target as two small plots in the *paper* context). The plots take the
  preview's width and are drawn again when it changes clearly; they follow the light / dark paper. Each preview plot
  is drawn in its own step of the event loop, so the window keeps answering.
* The bottom strip is always visible: *Accepted features (n)*, the chips, *Undo* / *Redo* (secondary, with icons),
  *Evaluate with model* (primary) and *Export* (menu). The evaluation lines read *metric mean ± spread → mean ±
  spread (gain)*; a real gain is green, a real loss red, *not significant* stays muted, and an out-of-date
  evaluation says *press Evaluate again*.
* Long work (finding features, applying steps, evaluating, submissions) runs in the background with a progress bar
  and a short status; buttons that would start a second job are disabled meanwhile.

## Charts: the Studio style

Written into every script as `sns.set_theme(style='white', …, palette=studio_colors)` plus a short
`plt.rcParams.update({...})`:

* **Palette** (fixed order, colour-blind safe for neighbouring series): `#2a78d6` `#eb6834` `#1baf7a` `#eda100`
  `#e87ba4` `#008300` `#6250d6` `#e34948`. On dark paper each colour takes its dark step:
  `#3987e5` `#d95926` `#199e70` `#c98500` `#d55181` `#008300` `#9085e9` `#e66767` (all ≥ 3:1 on the paper).
  Checked with the data-viz palette validator: lightness band, chroma floor, CVD ΔE ≥ 8 for neighbours,
  normal-vision ΔE ≥ 15.
* **Marks**: 1.4 pt lines (scaled with the Text size setting), 5 pt markers, white 1 pt gaps between bars and
  stacked areas, round line caps.
* **Frame**: no top/right spines, light grey left/bottom axis lines, hairline grid behind the data (none on
  heatmaps, none along category axes).
* **Text**: left-aligned bold titles with air above the plot, neutral grey labels and ticks, Plex first with
  common fallbacks (`Segoe UI`, `Helvetica Neue`, `Arial`, `DejaVu Sans`), so exported code never warns about a
  missing font.
* **Legend**: a rounded frame with a hairline edge, so it stays readable when it has to sit over data.
* Reference lines (Q-Q, ROC diagonal) are neutral grey and dashed; a regression fit uses the second palette
  colour (`C1`).

## Accessibility notes (WCAG 2.1 AA)

* Contrast: all text pairs ≥ 4.5:1, input outlines and the focus ring ≥ 3:1, in both looks (tested).
* Keyboard: every control is reachable with Tab; gallery cards and recent files open with Enter / Space;
  sliders and sections work from the keyboard; tooltips also explain the icon-only tools.
* Focus is visible (2.4.7) and only shown for keyboard users, so mouse users aren't distracted.
* Status messages use words and colour together; chart series always have a legend.
* Known limits of Tk: native menus and the combobox list follow the system's look; Tk has no screen-reader
  support on most platforms.

## Implementation notes

* ttk image elements are 9-slice pictures. ttk *tiles* the middle of a picture, and each tile of a picture
  with soft edges is an alpha blend, so `skin.grow()` stretches the middle to 96–256 px: a large card then
  costs a handful of tiles instead of thousands. Each element sets a small minimum size so small buttons stay
  small.
* Pictures are drawn with Pillow at 4× and reduced, and redrawn in place when the look changes.
* The click halo and focus-visible logic live in a few lines of Tcl (`theme._TCL`) bound to the `TButton`
  class, so they cover every button without per-widget code.
