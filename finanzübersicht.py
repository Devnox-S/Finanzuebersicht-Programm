"""
Finanzübersicht – Desktop App
Benötigte Pakete: pip install matplotlib
Starten: python3 finanzuebersicht.py
"""

import tkinter as tk
import tkinter.messagebox
import tkinter.filedialog as fd
import json, math, os, re, shutil, sys
from datetime import datetime
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import colorsys

# ── Basispfad (funktioniert sowohl als .py als auch als PyInstaller-.exe) ──────
def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

BASE_DIR = _get_base_dir()

# ── Feste Kategorie-Farben ────────────────────────────────────────────────────
INCOME_CLR    = "#3B82F6"   # Blau  (NICHT im Fixkosten-Farbwähler)
ESSENZ_CLR    = "#EF4444"   # Rot
FREIZEIT_CLR  = "#F59E0B"   # Amber
SAVINGS_CLR   = "#10B981"   # Grün
DEFICIT_CLR   = "#EF4444"
FIXKOSTEN_CLR = "#4B5563"   # Dunkelgrau / Standard Fixkosten
AUTO_CLR      = "#EC4899"   # Rosa
VERSICH_CLR   = "#7C3AED"   # Violett
NEUTRAL       = "#9099B5"   # Badges

# Fixkosten-Farbwähler: Farbe → Zielkategorie (KEIN Blau/INCOME)
FIX_COLOR_OPTIONS = [
    (FIXKOSTEN_CLR, "Fixkosten"),
    (ESSENZ_CLR,    "Essenziell"),
    (FREIZEIT_CLR,  "Freizeit"),
    (AUTO_CLR,      "Auto"),
    (VERSICH_CLR,   "Versicherung"),
]
FIX_COLOR_TO_CAT = {
    FIXKOSTEN_CLR: "fixkosten",
    ESSENZ_CLR:    "essenz",
    FREIZEIT_CLR:  "freizeit",
    AUTO_CLR:      "auto",
    VERSICH_CLR:   "versicherung",
}

DEFAULT_CAT_SETTINGS = {
    "savings":      {"name": "Ersparnis",    "color": "#10B981", "text_color": "#FFFFFF"},
    "income":       {"name": "Einkommen",    "color": "#3B82F6", "text_color": "#FFFFFF"},
    "essenz":       {"name": "Essenziell",   "color": "#EF4444", "text_color": "#FFFFFF"},
    "freizeit":     {"name": "Freizeit",     "color": "#F59E0B", "text_color": "#FFFFFF"},
    "fixkosten":    {"name": "Fixkosten",    "color": "#4B5563", "text_color": "#FFFFFF"},
    "auto":         {"name": "Auto",         "color": "#EC4899", "text_color": "#FFFFFF"},
    "versicherung": {"name": "Versicherung", "color": "#7C3AED", "text_color": "#FFFFFF"},
}

# ── Themes ────────────────────────────────────────────────────────────────────
LIGHT = dict(
    BG_APP       = "#F4F6FA",
    BG_CARD      = "#FFFFFF",
    BG_INPUT     = "#F0F2F8",
    BG_HOVER     = "#E8EAEF",
    BG_HEADER    = "#FFFFFF",
    BORDER       = "#DDE1EC",
    BORDER_LIGHT = "#ECEEF5",
    TEXT_PRIMARY = "#1A1D2E",
    TEXT_MUTED   = "#8890AA",
    TEXT_LABEL   = "#4A5068",
)
DARK = dict(
    BG_APP       = "#0F1117",
    BG_CARD      = "#1A1D27",
    BG_INPUT     = "#252836",
    BG_HOVER     = "#2E3245",
    BG_HEADER    = "#1A1D27",
    BORDER       = "#2D3250",
    BORDER_LIGHT = "#1E2035",
    TEXT_PRIMARY = "#F0F2FF",
    TEXT_MUTED   = "#7B82A0",
    TEXT_LABEL   = "#B0B8D8",
)

DATA_FILE        = os.path.join(BASE_DIR, "finanz_daten.json")
SETTINGS_FILE    = os.path.join(BASE_DIR, "finanz_einstellungen.json")
BACKUP_DIR       = os.path.join(BASE_DIR, "backups")
MAX_AUTO_BACKUPS = 10

MONTHS_DE = ["Januar","Februar","März","April","Mai","Juni",
             "Juli","August","September","Oktober","November","Dezember"]


def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as exc:
        tkinter.messagebox.showerror(
            "Speicherfehler",
            f"Daten konnten nicht gespeichert werden:\n{exc}\n\n"
            "Bitte Speicherplatz und Schreibrechte prüfen."
        )


def load_settings():
    if os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            s = json.load(f)
    else:
        s = {}
    s.setdefault("dark_mode", False)
    s.setdefault("last_year", None)
    s.setdefault("last_month", None)
    s.setdefault("overview_chart", "bar")
    # Merge per-category defaults (don't overwrite user values)
    cs = s.setdefault("cat_settings", {})
    for key, defaults in DEFAULT_CAT_SETTINGS.items():
        cat = cs.setdefault(key, {})
        for field, val in defaults.items():
            cat.setdefault(field, val)
    s.setdefault("custom_cat_order", [])
    s.setdefault("savings_goal_pct", 0)
    s.setdefault("drilldown_geometry", None)
    s.setdefault("search_geometry", None)
    s.setdefault("search_exact_amount", False)
    s.setdefault("search_hide_empty",   False)
    return s


def save_settings(s):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)


# ── Comprehensive Hex Color Picker ────────────────────────────────────────────
class HexColorPicker(tk.Toplevel):
    """Full-featured color picker: spectrum + presets + hex/RGB input."""

    PRESETS = [
        "#EF4444","#F97316","#F59E0B","#EAB308","#84CC16","#22C55E",
        "#10B981","#14B8A6","#06B6D4","#3B82F6","#6366F1","#8B5CF6",
        "#A855F7","#EC4899","#F43F5E","#DC2626","#EA580C","#D97706",
        "#65A30D","#16A34A","#0D9488","#0284C7","#4F46E5","#7C3AED",
        "#DB2777","#9F1239","#FFFFFF","#F4F6FA","#D1D5DB","#9CA3AF",
        "#6B7280","#4B5563","#374151","#1F2937","#111827","#000000",
    ]

    def __init__(self, parent, T, initial="#FFFFFF", title="Farbe w\u00e4hlen", callback=None):
        super().__init__(parent)
        self._T        = T
        self._callback = callback
        self._dragging = False
        self._hue_drag = False

        r, g, b = self._hex_to_rgb(initial)
        h, s, v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        self._h = h
        self._s = s
        self._v = v

        self.title(title)
        self.resizable(False, False)
        self.configure(bg=T["BG_CARD"])
        self.attributes("-topmost", True)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self._build(T, initial)

        self.update_idletasks()
        pw = parent.winfo_width();  ph = parent.winfo_height()
        px = parent.winfo_rootx(); py = parent.winfo_rooty()
        w  = self.winfo_width();   h2 = self.winfo_height()
        self.geometry(f"+{px + pw//2 - w//2}+{py + ph//2 - h2//2}")

    # ── Helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _hex_to_rgb(hex_str):
        h = hex_str.lstrip("#")
        if len(h) != 6:
            return 255, 255, 255
        try:
            return int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)
        except ValueError:
            return 255, 255, 255

    @staticmethod
    def _rgb_to_hex(r, g, b):
        return f"#{int(r):02X}{int(g):02X}{int(b):02X}"

    def _hsv_to_hex(self):
        r, g, b = colorsys.hsv_to_rgb(self._h, self._s, self._v)
        return self._rgb_to_hex(r*255, g*255, b*255)

    # ── Build UI ──────────────────────────────────────────────────────────────
    def _build(self, T, initial):
        SW = 220   # spectrum width
        SH = 160   # spectrum height
        HW = 20    # hue bar width
        PAD = 14

        outer = tk.Frame(self, bg=T["BORDER"], padx=1, pady=1)
        outer.pack(fill="both", expand=True)
        main = tk.Frame(outer, bg=T["BG_CARD"], padx=PAD, pady=PAD)
        main.pack(fill="both", expand=True)

        tk.Label(main, text=self.title(), font=("Helvetica Neue", 11, "bold"),
                 bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(anchor="w", pady=(0, 10))

        # ── Top row: spectrum + hue bar ───────────────────────────────────────
        top = tk.Frame(main, bg=T["BG_CARD"])
        top.pack(anchor="w")

        self._spec_canvas = tk.Canvas(top, width=SW, height=SH,
                                      highlightthickness=1,
                                      highlightbackground=T["BORDER"],
                                      cursor="crosshair")
        self._spec_canvas.pack(side="left", padx=(0, 8))

        self._hue_canvas = tk.Canvas(top, width=HW, height=SH,
                                     highlightthickness=1,
                                     highlightbackground=T["BORDER"],
                                     cursor="sb_v_double_arrow")
        self._hue_canvas.pack(side="left")

        # Draw spectrum + hue bar (canvas rectangles – zuverlässiger als PhotoImage)
        self._draw_hue_bar(SH, HW)
        self._draw_spectrum(SW, SH)

        # Crosshair marker on spectrum (über Spektrum gezeichnet)
        self._marker = self._spec_canvas.create_oval(0,0,10,10,
                                                      outline="#FFFFFF", width=2)
        self._hue_marker = self._hue_canvas.create_line(0,0,HW,0,
                                                         fill="#FFFFFF", width=2)
        self._update_markers(SW, SH)

        # Spectrum mouse bindings
        self._spec_canvas.bind("<ButtonPress-1>",   lambda e: self._spec_press(e, SW, SH))
        self._spec_canvas.bind("<B1-Motion>",        lambda e: self._spec_drag(e, SW, SH))
        self._spec_canvas.bind("<ButtonRelease-1>",  lambda e: self._spec_release())
        # Hue bar mouse bindings
        self._hue_canvas.bind("<ButtonPress-1>",    lambda e: self._hue_press(e, SH, SW))
        self._hue_canvas.bind("<B1-Motion>",         lambda e: self._hue_drag_ev(e, SH, SW))
        self._hue_canvas.bind("<ButtonRelease-1>",   lambda e: self._hue_release())

        # ── Preset swatches ───────────────────────────────────────────────────
        tk.Frame(main, bg=T["BORDER_LIGHT"], height=1).pack(fill="x", pady=(10, 6))
        preset_frame = tk.Frame(main, bg=T["BG_CARD"])
        preset_frame.pack(anchor="w")
        for i, clr in enumerate(self.PRESETS):
            col = i % 12
            row_idx = i // 12
            sw = tk.Frame(preset_frame, bg=clr, width=20, height=20,
                          cursor="hand2",
                          highlightthickness=1,
                          highlightbackground=T["BORDER"])
            sw.grid(row=row_idx, column=col, padx=1, pady=1)
            sw.bind("<Button-1>", lambda e, c=clr: self._pick_preset(c, SW, SH))

        # ── Hex + RGB input ───────────────────────────────────────────────────
        tk.Frame(main, bg=T["BORDER_LIGHT"], height=1).pack(fill="x", pady=(8, 6))
        inp_row = tk.Frame(main, bg=T["BG_CARD"])
        inp_row.pack(anchor="w", fill="x")

        # Preview swatch (before | after)
        prev_frame = tk.Frame(inp_row, bg=T["BG_CARD"])
        prev_frame.pack(side="right", padx=(10, 0))
        tk.Label(prev_frame, text="Vorher", font=("Helvetica Neue", 7),
                 bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack()
        prev_box = tk.Frame(prev_frame, bg=initial, width=36, height=22,
                            highlightthickness=1, highlightbackground=T["BORDER"])
        prev_box.pack()
        tk.Label(prev_frame, text="Nachher", font=("Helvetica Neue", 7),
                 bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack()
        self._after_box = tk.Frame(prev_frame, bg=self._hsv_to_hex(), width=36, height=22,
                                   highlightthickness=1, highlightbackground=T["BORDER"])
        self._after_box.pack()

        # Hex field
        left_inp = tk.Frame(inp_row, bg=T["BG_CARD"])
        left_inp.pack(side="left")
        tk.Label(left_inp, text="Hex:", font=("Helvetica Neue", 8),
                 bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).grid(row=0, column=0, sticky="w")
        self._hex_var = tk.StringVar(value=self._hsv_to_hex())
        hex_e = tk.Entry(left_inp, textvariable=self._hex_var, width=9,
                         font=("Helvetica Neue", 10, "bold"),
                         bg=T["BG_INPUT"], fg=T["TEXT_PRIMARY"],
                         insertbackground=T["TEXT_PRIMARY"],
                         relief="flat", bd=0,
                         highlightthickness=1, highlightbackground=T["BORDER"])
        hex_e.grid(row=0, column=1, padx=(4,0), ipady=3)
        hex_e.bind("<Return>",   lambda e: self._hex_entered(SW, SH))
        hex_e.bind("<FocusOut>", lambda e: self._hex_entered(SW, SH))

        # RGB fields
        self._r_var = tk.IntVar(); self._g_var = tk.IntVar(); self._b_var = tk.IntVar()
        self._update_rgb_from_hsv()
        for label, var, col_idx in [("R", self._r_var, 0), ("G", self._g_var, 1), ("B", self._b_var, 2)]:
            fr = tk.Frame(left_inp, bg=T["BG_CARD"])
            fr.grid(row=1, column=col_idx, padx=(0 if col_idx == 0 else 4, 0), pady=(4,0))
            tk.Label(fr, text=label+":", font=("Helvetica Neue", 8),
                     bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(side="left")
            e = tk.Entry(fr, textvariable=var, width=4,
                         font=("Helvetica Neue", 9),
                         bg=T["BG_INPUT"], fg=T["TEXT_PRIMARY"],
                         insertbackground=T["TEXT_PRIMARY"],
                         relief="flat", bd=0,
                         highlightthickness=1, highlightbackground=T["BORDER"])
            e.pack(side="left", padx=(2,0), ipady=2)
            e.bind("<Return>",   lambda ev: self._rgb_entered(SW, SH))
            e.bind("<FocusOut>", lambda ev: self._rgb_entered(SW, SH))

        # ── Buttons ───────────────────────────────────────────────────────────
        tk.Frame(main, bg=T["BORDER_LIGHT"], height=1).pack(fill="x", pady=(10, 8))
        btn_row = tk.Frame(main, bg=T["BG_CARD"])
        btn_row.pack(fill="x")
        tk.Button(btn_row, text="Abbrechen",
                  font=("Helvetica Neue", 9),
                  bg=T["BG_INPUT"], fg=T["TEXT_MUTED"],
                  relief="flat", bd=0, cursor="hand2", padx=12, pady=4,
                  command=self._cancel).pack(side="left")
        tk.Button(btn_row, text="OK",
                  font=("Helvetica Neue", 9, "bold"),
                  bg="#3B82F6", fg="#FFFFFF",
                  relief="flat", bd=0, cursor="hand2", padx=18, pady=4,
                  command=self._ok).pack(side="right")

    # ── Drawing ───────────────────────────────────────────────────────────────
    def _draw_spectrum(self, SW, SH):
        """Zeichnet HSV-Spektrum als Canvas-Rechtecke (Sättigung x → Helligkeit y↑)."""
        self._spec_canvas.delete("spectrum")
        STEP = 4
        for y in range(0, SH, STEP):
            v = 1.0 - y / SH
            for x in range(0, SW, STEP):
                s = x / SW
                r, g, b = colorsys.hsv_to_rgb(self._h, s, v)
                clr = f"#{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}"
                self._spec_canvas.create_rectangle(
                    x, y, x + STEP, y + STEP,
                    fill=clr, outline="", tags="spectrum")
        # Marker immer über Spektrum
        if hasattr(self, "_marker"):
            self._spec_canvas.tag_raise(self._marker)

    def _draw_hue_bar(self, SH, HW=22):
        """Zeichnet Farbton-Balken als horizontale Linien."""
        self._hue_canvas.delete("huebar")
        for y in range(SH):
            h = y / SH
            r, g, b = colorsys.hsv_to_rgb(h, 1.0, 1.0)
            clr = f"#{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}"
            self._hue_canvas.create_line(0, y, HW, y, fill=clr, tags="huebar")
        if hasattr(self, "_hue_marker"):
            self._hue_canvas.tag_raise(self._hue_marker)

    def _update_markers(self, SW, SH):
        MR = 6
        sx = int(self._s * SW)
        sy = int((1.0 - self._v) * SH)
        self._spec_canvas.coords(self._marker, sx-MR, sy-MR, sx+MR, sy+MR)
        hy = int(self._h * SH)
        HW = self._hue_canvas.winfo_reqwidth() - 2
        self._hue_canvas.coords(self._hue_marker, 0, hy, HW, hy)

    def _update_all(self, SW, SH):
        self._draw_spectrum(SW, SH)   # zeichnet Spektrum + hebt Marker
        self._update_markers(SW, SH)
        hex_val = self._hsv_to_hex()
        self._hex_var.set(hex_val)
        self._update_rgb_from_hsv()
        if hasattr(self, "_after_box"):
            try:
                self._after_box.config(bg=hex_val)
            except Exception:
                pass

    def _update_rgb_from_hsv(self):
        r, g, b = colorsys.hsv_to_rgb(self._h, self._s, self._v)
        self._r_var.set(int(r*255))
        self._g_var.set(int(g*255))
        self._b_var.set(int(b*255))

    # ── Event handlers ────────────────────────────────────────────────────────
    def _spec_press(self, e, SW, SH):
        self._dragging = True
        self._spec_pick(e.x, e.y, SW, SH)

    def _spec_drag(self, e, SW, SH):
        if self._dragging:
            self._spec_pick(e.x, e.y, SW, SH)

    def _spec_release(self):
        self._dragging = False

    def _spec_pick(self, x, y, SW, SH):
        self._s = max(0.0, min(1.0, x / SW))
        self._v = max(0.0, min(1.0, 1.0 - y / SH))
        self._update_all(SW, SH)

    def _hue_press(self, e, SH, SW):
        self._hue_drag = True
        self._hue_pick(e.y, SH, SW)

    def _hue_drag_ev(self, e, SH, SW):
        if self._hue_drag:
            self._hue_pick(e.y, SH, SW)

    def _hue_release(self):
        self._hue_drag = False

    def _hue_pick(self, y, SH, SW):
        self._h = max(0.0, min(1.0, y / SH))
        self._update_all(SW, SH)
        HW = self._hue_canvas.winfo_reqwidth() - 2
        self._hue_canvas.coords(self._hue_marker, 0, int(self._h*SH), HW, int(self._h*SH))

    def _pick_preset(self, hex_color, SW, SH):
        r, g, b = self._hex_to_rgb(hex_color)
        self._h, self._s, self._v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
        self._update_all(SW, SH)
        HW = self._hue_canvas.winfo_reqwidth() - 2
        hy = int(self._h * SH)
        self._hue_canvas.coords(self._hue_marker, 0, hy, HW, hy)

    def _hex_entered(self, SW, SH):
        val = self._hex_var.get().strip()
        if not val.startswith("#"):
            val = "#" + val
        if len(val) == 7:
            try:
                r, g, b = self._hex_to_rgb(val)
                self._h, self._s, self._v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
                self._update_all(SW, SH)
                HW = self._hue_canvas.winfo_reqwidth() - 2
                hy = int(self._h * SH)
                self._hue_canvas.coords(self._hue_marker, 0, hy, HW, hy)
            except Exception:
                pass

    def _rgb_entered(self, SW, SH):
        try:
            r = max(0, min(255, self._r_var.get()))
            g = max(0, min(255, self._g_var.get()))
            b = max(0, min(255, self._b_var.get()))
            self._h, self._s, self._v = colorsys.rgb_to_hsv(r/255, g/255, b/255)
            self._update_all(SW, SH)
            HW = self._hue_canvas.winfo_reqwidth() - 2
            hy = int(self._h * SH)
            self._hue_canvas.coords(self._hue_marker, 0, hy, HW, hy)
        except Exception:
            pass

    def _ok(self):
        hex_val = self._hsv_to_hex()
        if self._callback:
            self._callback(hex_val)
        self.grab_release()
        self.destroy()

    def _cancel(self):
        self.grab_release()
        self.destroy()


class FinanzApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Finanzübersicht")
        self.minsize(1400, 820)

        settings            = load_settings()
        self.dark_mode      = settings.get("dark_mode", False)
        self.overview_chart = settings.get("overview_chart", "bar")
        self.data           = load_data()
        self._cat_settings = settings.get("cat_settings", {})
        for key, defaults in DEFAULT_CAT_SETTINGS.items():
            cat = self._cat_settings.setdefault(key, {})
            for field, val in defaults.items():
                cat.setdefault(field, val)
        self._custom_cat_order = settings.get("custom_cat_order", [])
        # Clean up: remove keys no longer in _cat_settings
        self._custom_cat_order = [k for k in self._custom_cat_order if k in self._cat_settings]
        self._custom_cards = {}
        now                 = datetime.now()
        ly, lm              = settings.get("last_year"), settings.get("last_month")
        if ly is not None and lm is not None:
            self.current_year  = tk.IntVar(value=int(ly))
            self.current_month = tk.IntVar(value=int(lm))
        else:
            self.current_year  = tk.IntVar(value=now.year)
            self.current_month = tk.IntVar(value=now.month - 1)

        self._savings_goal_var    = tk.StringVar(value=str(int(settings.get("savings_goal_pct", 0))))
        self._drilldown_geometry  = settings.get("drilldown_geometry", None)
        self._overview_geometry   = settings.get("overview_geometry", None)
        self._main_geometry       = settings.get("main_geometry", None)
        self._search_geometry     = settings.get("search_geometry", None)
        self._search_exact_amount = settings.get("search_exact_amount", False)
        self._search_hide_empty   = settings.get("search_hide_empty",   False)
        self._undo_stack = []  # list of (month_key, data_dict_deepcopy)
        self._redo_stack = []  # list of (month_key, data_dict_deepcopy)
        self._cal_dropdown        = None
        self._hover_watch_id      = None
        self._fixkosten_snapshot  = None
        self._fix_dlg_open        = False
        self._fix_row_tip         = None   # Hover-Tooltip für Fixkosten-Zeilen
        self._fix_row_tip_job     = None   # after()-Handle für verzögertes Verstecken
        self._refresh_pending = None
        self.month_chart      = "pie"

        # Fenstergeometrie wiederherstellen oder Standard setzen
        try:
            self.geometry(self._main_geometry or "1620x980")
        except Exception:
            self._main_geometry = None
            self.geometry("1620x980")

        def _track_main_geometry(e=None):
            try:
                if e is not None and e.widget is not self:
                    return
                geom = self.geometry()
                # Nur speichern wenn Fenstergröße plausibel ist
                if geom and "x" in geom:
                    w = int(geom.split("x")[0])
                    h = int(geom.split("x")[1].split("+")[0].split("-")[0])
                    if w >= 800 and h >= 600:
                        self._main_geometry = geom
            except Exception:
                pass
        # Verzögert starten damit initiale Configure-Events ignoriert werden
        self.after(500, lambda: self.bind("<Configure>", _track_main_geometry))

        self._build_ui()
        self._load_month()

    # ── Theme ─────────────────────────────────────────────────────────────────
    def _T(self):
        return DARK if self.dark_mode else LIGHT

    def _cc(self, key):
        """Category accent color."""
        return self._cat_settings.get(key, {}).get("color", DEFAULT_CAT_SETTINGS.get(key, {}).get("color", "#888"))

    @staticmethod
    def _lighten_color(hex_color, factor=0.55):
        """Gibt eine aufgehellte Variante der Hex-Farbe zurück."""
        h = hex_color.lstrip("#")
        if len(h) != 6:
            return "#AAAAAA"
        try:
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        except ValueError:
            return "#AAAAAA"
        hh, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        s2 = s * (1 - factor)
        v2 = v + (1 - v) * factor
        r2, g2, b2 = colorsys.hsv_to_rgb(hh, s2, v2)
        return f"#{int(r2 * 255):02X}{int(g2 * 255):02X}{int(b2 * 255):02X}"

    def _ctc(self, key):
        """Category text/letter color."""
        return self._cat_settings.get(key, {}).get("text_color", "#FFFFFF")

    def _cn(self, key):
        """Category display name."""
        return self._cat_settings.get(key, {}).get("name", DEFAULT_CAT_SETTINGS.get(key, {}).get("name", key))

    def _toggle_theme(self):
        self._save_month()
        self.dark_mode = not self.dark_mode
        try:
            _goal_pct_save = float(self._savings_goal_var.get())
        except (ValueError, TypeError):
            _goal_pct_save = 0
        save_settings({"dark_mode": self.dark_mode,
                       "last_year": self.current_year.get(),
                       "last_month": self.current_month.get(),
                       "overview_chart": self.overview_chart,
                       "cat_settings": self._cat_settings,
                       "custom_cat_order": self._custom_cat_order,
                       "savings_goal_pct": _goal_pct_save,
                       "drilldown_geometry": self._drilldown_geometry,
                       "overview_geometry":   self._overview_geometry,
                       "main_geometry":       self._main_geometry,
                       "search_geometry":     self._search_geometry,
                       "search_exact_amount": self._search_exact_amount,
                       "search_hide_empty":   self._search_hide_empty})
        plt.close("all")
        for w in self.winfo_children():
            w.destroy()
        self._build_ui()
        self._load_month()

    # ── UI-Aufbau ─────────────────────────────────────────────────────────────
    def _build_ui(self):
        T = self._T()
        self.configure(bg=T["BG_APP"])

        header = tk.Frame(self, bg=T["BG_HEADER"], height=62)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Frame(self, bg=T["BORDER"], height=1).pack(fill="x")

        left = tk.Frame(header, bg=T["BG_HEADER"])
        left.pack(side="left", padx=22)
        tk.Label(left, textvariable=self.current_year,
                 font=("Helvetica Neue", 20, "bold"),
                 bg=T["BG_HEADER"], fg=T["TEXT_MUTED"]).pack(side="left", padx=(0,10), pady=18)
        tk.Button(left, text="\u25c4", font=("Helvetica Neue", 12, "bold"),
                  bg=T["BG_HEADER"], fg=T["TEXT_MUTED"], bd=0, cursor="hand2",
                  activebackground=T["BG_HOVER"], activeforeground=T["TEXT_PRIMARY"],
                  command=self._prev_month).pack(side="left", padx=(0,10), pady=18)
        self.month_lbl = tk.Label(left, text=MONTHS_DE[self.current_month.get()],
                                  font=("Helvetica Neue", 18, "bold"),
                                  bg=T["BG_HEADER"], fg=T["TEXT_PRIMARY"], width=11,
                                  cursor="hand2")
        self.month_lbl.pack(side="left", pady=18)
        self.month_lbl.bind("<Enter>", lambda e: self._on_month_lbl_enter())
        self.month_lbl.bind("<Leave>", lambda e: self._on_month_lbl_leave())
        tk.Button(left, text="\u25ba", font=("Helvetica Neue", 12, "bold"),
                  bg=T["BG_HEADER"], fg=T["TEXT_MUTED"], bd=0, cursor="hand2",
                  activebackground=T["BG_HOVER"], activeforeground=T["TEXT_PRIMARY"],
                  command=self._next_month).pack(side="left", padx=(0, 10), pady=18)
        tk.Button(left, text="\u24d8",
                  font=("Helvetica Neue", 15, "bold"),
                  bg=T["BG_HEADER"], fg=T["TEXT_MUTED"], bd=0, cursor="hand2",
                  activebackground=T["BG_HOVER"], activeforeground=INCOME_CLR,
                  command=self._open_info).pack(side="left", padx=(10, 0), pady=14)
        # Suchbutton direkt neben ⓘ, gleicher Stil
        self._search_btn = tk.Button(left, text="\U0001F50E",
                  font=("Helvetica Neue", 15, "bold"),
                  bg=T["BG_HEADER"], fg=T["TEXT_MUTED"], bd=0, cursor="hand2",
                  activebackground=T["BG_HOVER"], activeforeground=INCOME_CLR,
                  command=self._open_search)
        self._search_btn.pack(side="left", padx=(4, 0), pady=14)

        self._cat_btn = tk.Button(header, text="\u2699 Einstellungen",
                  font=("Helvetica Neue", 10, "bold"),
                  bg=T["BG_INPUT"], fg=T["TEXT_LABEL"],
                  relief="flat", bd=0, cursor="hand2", padx=14, pady=6,
                  activebackground=T["BORDER"], activeforeground=T["TEXT_PRIMARY"],
                  command=self._open_cat_settings)
        self._cat_btn.pack(side="left", padx=(0, 8), pady=14)
        self._cat_settings_popup = None

        tk.Button(header, text="\U0001f4ca  Gesamtübersicht",
                  font=("Helvetica Neue", 10, "bold"),
                  bg=T["BG_INPUT"], fg=T["TEXT_LABEL"],
                  relief="flat", bd=0, cursor="hand2", padx=14, pady=6,
                  activebackground=T["BORDER"], activeforeground=T["TEXT_PRIMARY"],
                  command=self._open_overview).pack(side="left", padx=(0, 8), pady=14)

        tk.Button(header, text="\U0001f4be  Backup",
                  font=("Helvetica Neue", 10),
                  bg=T["BG_INPUT"], fg=T["TEXT_MUTED"],
                  relief="flat", bd=0, cursor="hand2", padx=14, pady=6,
                  activebackground=T["BORDER"], activeforeground=T["TEXT_PRIMARY"],
                  command=self._open_backup_manager).pack(side="left", padx=(0, 8), pady=14)

        dark_lbl = "\u2600" if self.dark_mode else "\u263d"
        tk.Button(header, text=dark_lbl,
                  font=("Helvetica Neue", 10),
                  bg=T["BG_INPUT"], fg=T["TEXT_MUTED"],
                  relief="flat", bd=0, cursor="hand2", padx=12, pady=6,
                  activebackground=T["BORDER"], activeforeground=T["TEXT_PRIMARY"],
                  command=self._toggle_theme).pack(side="left", padx=(0,8), pady=14)

        tk.Button(header, text="\U0001f9ee  Rechner",
                  font=("Helvetica Neue", 10),
                  bg=T["BG_INPUT"], fg=T["TEXT_MUTED"],
                  relief="flat", bd=0, cursor="hand2", padx=12, pady=6,
                  activebackground=T["BORDER"], activeforeground=T["TEXT_PRIMARY"],
                  command=self._open_calculator).pack(side="left", padx=(0,12), pady=14)

        # Sparquoten-Ziel Eingabe
        _goal_outer = tk.Frame(header, bg=T["BG_HEADER"])
        _goal_outer.pack(side="left", padx=(0, 12), pady=14)
        tk.Label(_goal_outer, text="Sparziel:",
                 font=("Helvetica Neue", 9),
                 bg=T["BG_HEADER"], fg=T["TEXT_MUTED"]).pack(side="left", padx=(0,4))
        _goal_entry = tk.Entry(_goal_outer, textvariable=self._savings_goal_var, width=3,
                               font=("Helvetica Neue", 10, "bold"),
                               bg=T["BG_INPUT"], fg=T["TEXT_PRIMARY"],
                               insertbackground=T["TEXT_PRIMARY"],
                               relief="flat", bd=0,
                               highlightthickness=1, highlightbackground=T["BORDER"])
        _goal_entry.pack(side="left", ipady=3)
        tk.Label(_goal_outer, text="%",
                 font=("Helvetica Neue", 9),
                 bg=T["BG_HEADER"], fg=T["TEXT_MUTED"]).pack(side="left", padx=(2,6))
        self._goal_badge_lbl = tk.Label(_goal_outer, text="",
                                         font=("Helvetica Neue", 9, "bold"),
                                         bg=T["BG_HEADER"], fg=T["TEXT_MUTED"])
        self._goal_badge_lbl.pack(side="left")
        _goal_entry.bind("<FocusOut>", lambda e: self._on_goal_changed())
        _goal_entry.bind("<Return>",   lambda e: self._on_goal_changed())
        self.bind_all("<Control-f>", lambda e: self._open_search())
        self.bind_all("<Control-F>", lambda e: self._open_search())
        self.bind_all("<Left>",  lambda e: self._on_arrow_nav("prev"))
        self.bind_all("<Right>", lambda e: self._on_arrow_nav("next"))

        right = tk.Frame(header, bg=T["BG_HEADER"])
        right.pack(side="right", padx=24)
        self.savings_lbl = tk.Label(right, text=f"{self._cn('savings')}: \u2013",
                                    font=("Helvetica Neue", 12, "bold"),
                                    bg=T["BG_HEADER"], fg=self._cc("savings"))
        self.savings_lbl.pack(pady=20)

        self.main_frame = tk.Frame(self, bg=T["BG_APP"])
        self.main_frame.pack(fill="both", expand=True, padx=16, pady=14)
        # Grid: Kategorien (weight=2) : Chart (weight=1) → selbe Proportionen wie vorher
        self.main_frame.columnconfigure(0, weight=16)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(0, weight=1)

        # ── Scrollbare Kategorien-Spalten (links) ─────────────────────────────
        _left_host = tk.Frame(self.main_frame, bg=T["BG_APP"])
        _left_host.grid(row=0, column=0, sticky="nsew", padx=(0,7))

        self._cats_vsb = tk.Scrollbar(_left_host, orient="vertical", bg=T["BG_APP"])
        # Pack scrollbar first so it appears on the right; canvas fills remaining space.
        # _check_cats_scroll will pack_forget() / pack() as needed.
        self._cats_vsb.pack(side="right", fill="y")
        self._cats_vsb.pack_forget()   # hidden by default until content overflows
        self._cats_canvas = tk.Canvas(_left_host, bg=T["BG_APP"], highlightthickness=0,
                                      yscrollcommand=self._update_cats_scroll)
        self._cats_canvas.pack(side="left", fill="both", expand=True)
        self._cats_vsb.configure(command=self._cats_canvas.yview)

        self._cats_inner = tk.Frame(self._cats_canvas, bg=T["BG_APP"])
        self._cats_win   = self._cats_canvas.create_window(
            (0, 0), window=self._cats_inner, anchor="nw")

        self._cats_inner.bind("<Configure>", self._on_cats_configure)
        self._cats_canvas.bind("<Configure>",
            lambda e: self._cats_canvas.itemconfig(self._cats_win, width=e.width))
        # Mousewheel will be handled by a single bind_all dispatcher installed
        # after both canvases are created (see below, after legend_canvas setup).

        # 3 Spalten innerhalb des scrollbaren Bereichs
        # 3 Kategorien-Spalten nebeneinander (oben) – grid mit uniform für exakt gleiche Breite
        _top_area = tk.Frame(self._cats_inner, bg=T["BG_APP"])
        _top_area.pack(fill="x", anchor="n")
        _top_area.grid_columnconfigure(0, weight=1, uniform="col")
        _top_area.grid_columnconfigure(1, weight=1, uniform="col")
        _top_area.grid_columnconfigure(2, weight=1, uniform="col")
        _top_area.grid_rowconfigure(0, weight=1)

        self.col_income   = tk.Frame(_top_area, bg=T["BG_APP"])
        self.col_income.grid(row=0, column=0, sticky="nsew")

        self.col_essenz   = tk.Frame(_top_area, bg=T["BG_APP"])
        self.col_essenz.grid(row=0, column=1, sticky="nsew", padx=7)

        self.col_freizeit = tk.Frame(_top_area, bg=T["BG_APP"])
        self.col_freizeit.grid(row=0, column=2, sticky="nsew")

        # Notizfeld-Bereich (volle Breite = alle 3 Spalten)
        _notes_host = tk.Frame(self._cats_inner, bg=T["BG_APP"])
        _notes_host.pack(fill="x", pady=(10, 0))

        self.col_chart    = tk.Frame(self.main_frame, bg=T["BG_APP"])
        self.col_chart.grid(row=0, column=1, sticky="nsew", padx=(7,0))

        self._cats_scroll_after_id = None
        def _schedule_cats_scroll(e=None):
            if getattr(self, '_app_closing', False):
                return
            if self._cats_scroll_after_id:
                try:
                    self.after_cancel(self._cats_scroll_after_id)
                except Exception:
                    pass
            self._cats_scroll_after_id = self.after(50, self._check_cats_scroll)
        self.bind("<Configure>", _schedule_cats_scroll)

        self.income_card    = self._make_card(self.col_income,   self._cn("income"),
                                              self._cc("income"),   "income",   3)
        self.essenz_card    = self._make_card(self.col_essenz,   self._cn("essenz"),
                                              self._cc("essenz"),   "essenz",   4)
        self.freizeit_card  = self._make_card(self.col_freizeit, self._cn("freizeit"),
                                              self._cc("freizeit"), "freizeit", 4)
        self.fixkosten_card = self._make_card(self.col_income,   self._cn("fixkosten") + " Jahr",
                                              self._cc("fixkosten"), "fixkosten", 2, top_pad=10)
        self.auto_card      = self._make_card(self.col_essenz,   self._cn("auto"),
                                              self._cc("auto"),      "auto",       2, top_pad=10)
        self.versich_card   = self._make_card(self.col_freizeit, self._cn("versicherung"),
                                              self._cc("versicherung"), "versicherung", 2, top_pad=10)

        # Notizen-Karte (volle Breite – alle 3 Kategorien-Spalten)
        self._make_notes_card(_notes_host)

        # ── Benutzerdefinierte Kategorien ─────────────────────────────────────
        self._custom_cards = {}
        _cols = [self.col_income, self.col_essenz, self.col_freizeit]
        for i, key in enumerate(self._custom_cat_order):
            if key in self._cat_settings:
                col = _cols[i % 3]
                card = self._make_card(col, self._cn(key), self._cc(key), key, 2, top_pad=10)
                self._custom_cards[key] = card

        # Chart-Karte
        self.chart_card = tk.Frame(self.col_chart, bg=T["BG_CARD"],
                                   highlightthickness=1, highlightbackground=T["BORDER"])
        self.chart_card.pack(fill="both", expand=True)
        tk.Frame(self.chart_card, bg=NEUTRAL, height=3).pack(fill="x")
        chart_title_row = tk.Frame(self.chart_card, bg=T["BG_CARD"])
        chart_title_row.pack(fill="x", padx=14, pady=(10, 0))
        tk.Label(chart_title_row, text="Monatsübersicht",
                 font=("Helvetica Neue", 13, "bold"),
                 bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(side="left")
        self._month_chart_btn_bar  = tk.Button(
            chart_title_row, text="\u258c\u2590 Balken",
            font=("Helvetica Neue", 9, "bold"),
            bg=INCOME_CLR if self.month_chart == "bar" else T["BG_INPUT"],
            fg="#FFFFFF"   if self.month_chart == "bar" else T["TEXT_LABEL"],
            relief="flat", bd=0, cursor="hand2", padx=10, pady=3,
            activebackground=INCOME_CLR, activeforeground="#FFFFFF",
            command=lambda: self._set_month_chart("bar"))
        self._month_chart_btn_bar.pack(side="right", padx=(4, 0))
        self._month_chart_btn_pie  = tk.Button(
            chart_title_row, text="\u25cf Torte",
            font=("Helvetica Neue", 9, "bold"),
            bg=INCOME_CLR if self.month_chart == "pie" else T["BG_INPUT"],
            fg="#FFFFFF"   if self.month_chart == "pie" else T["TEXT_LABEL"],
            relief="flat", bd=0, cursor="hand2", padx=10, pady=3,
            activebackground=INCOME_CLR, activeforeground="#FFFFFF",
            command=lambda: self._set_month_chart("pie"))
        self._month_chart_btn_pie.pack(side="right", padx=(0, 4))
        tk.Frame(self.chart_card, bg=T["BORDER_LIGHT"], height=1).pack(
            fill="x", padx=14, pady=(4, 0))

        pie_frame = tk.Frame(self.chart_card, bg=T["BG_CARD"], height=430)
        pie_frame.pack(fill="x")
        pie_frame.pack_propagate(False)
        self.fig, self.ax = plt.subplots(figsize=(4.6, 4.3), facecolor=T["BG_CARD"])
        self.ax.set_facecolor(T["BG_CARD"])
        self.fig.subplots_adjust(top=0.90, bottom=0.05, left=0.05, right=0.95)
        self.mpl_canvas = FigureCanvasTkAgg(self.fig, master=pie_frame)
        self.mpl_canvas.get_tk_widget().pack(fill="both", expand=True)

        self._bar_canvas = tk.Canvas(pie_frame, bg=T["BG_CARD"], highlightthickness=0)
        self._bar_canvas.bind("<Configure>", lambda e: self._on_bar_canvas_resize())

        self._chart_legend_sep = tk.Frame(self.chart_card, bg=T["BORDER_LIGHT"], height=1)
        self._chart_legend_sep.pack(fill="x", padx=14, pady=(4,0))

        legend_outer = tk.Frame(self.chart_card, bg=T["BG_CARD"])
        legend_outer.pack(fill="both", expand=True)
        self._legend_outer = legend_outer
        self.legend_canvas = tk.Canvas(legend_outer, bg=T["BG_CARD"],
                                       highlightthickness=0)
        self.legend_canvas.pack(side="left", fill="both", expand=True)
        legend_vsb = tk.Scrollbar(legend_outer, orient="vertical",
                                   command=self.legend_canvas.yview, bg=T["BG_APP"])
        legend_vsb.pack(side="right", fill="y")
        self.legend_canvas.configure(yscrollcommand=legend_vsb.set)
        self.legend_frame = tk.Frame(self.legend_canvas, bg=T["BG_CARD"])
        self._legend_win  = self.legend_canvas.create_window(
            (0,0), window=self.legend_frame, anchor="nw")
        self.legend_frame.bind("<Configure>",
            lambda e: self.legend_canvas.configure(
                scrollregion=self.legend_canvas.bbox("all")))
        self.legend_canvas.bind("<Configure>",
            lambda e: self.legend_canvas.itemconfig(self._legend_win, width=e.width))
        # Single bind_all dispatcher routes mousewheel to the correct canvas based
        # on pointer position.  (Two separate bind_all calls would silently replace
        # each other, so a combined dispatcher is required.)
        def _global_mousewheel(e):
            delta = int(-1 * (e.delta / 120))
            # Don't steal scroll from the notes Text widget
            try:
                nx = self.notes_text.winfo_rootx()
                ny = self.notes_text.winfo_rooty()
                nw = self.notes_text.winfo_width()
                nh = self.notes_text.winfo_height()
                if nx <= e.x_root <= nx + nw and ny <= e.y_root <= ny + nh:
                    return  # let Text widget handle its own scrolling
            except Exception:
                pass
            try:
                cx = self._cats_canvas.winfo_rootx()
                cy = self._cats_canvas.winfo_rooty()
                cw = self._cats_canvas.winfo_width()
                ch = self._cats_canvas.winfo_height()
                if cx <= e.x_root <= cx + cw and cy <= e.y_root <= cy + ch:
                    self._cats_canvas.yview_scroll(delta, "units")
                    return
            except Exception:
                pass
            try:
                lx = self.legend_canvas.winfo_rootx()
                ly = self.legend_canvas.winfo_rooty()
                lw = self.legend_canvas.winfo_width()
                lh = self.legend_canvas.winfo_height()
                if lx <= e.x_root <= lx + lw and ly <= e.y_root <= ly + lh:
                    self.legend_canvas.yview_scroll(delta, "units")
            except Exception:
                pass
        self._global_mousewheel_fn = _global_mousewheel
        self.bind_all("<MouseWheel>", _global_mousewheel)

        # Click anywhere in main window → refresh (debounced = no flicker)
        self.bind_all("<Button-1>", lambda e: self._schedule_refresh())

        # ── Rechtsklick-Kontextmenü (modernes Custom-Popup) ────────────────────
        self._ctx_popup = None

        def _show_ctx(e):
            # Ziel-Widget für Kopieren/Einfügen merken
            self._ctx_target = e.widget
            # Eventuell offenes Popup schließen
            try:
                if self._ctx_popup and self._ctx_popup.winfo_exists():
                    self._ctx_popup.destroy()
            except Exception:
                pass

            _T = self._T()
            pop = tk.Toplevel(self)
            self._ctx_popup = pop
            pop.overrideredirect(True)
            pop.attributes("-topmost", True)
            pop.configure(bg=_T["BORDER"])

            outer = tk.Frame(pop, bg=_T["BORDER"], padx=1, pady=1)
            outer.pack(fill="both", expand=True)
            inner = tk.Frame(outer, bg=_T["BG_CARD"], padx=4, pady=4)
            inner.pack(fill="both", expand=True)

            ACCENT = self._cc("income")

            def _add_item(icon, label, shortcut, cmd):
                frm = tk.Frame(inner, bg=_T["BG_CARD"], cursor="hand2")
                frm.pack(fill="x", pady=1)

                icon_lbl = tk.Label(frm, text=icon, width=2,
                                    font=("Segoe UI Emoji", 10),
                                    bg=_T["BG_CARD"], fg=_T["TEXT_MUTED"],
                                    padx=2)
                icon_lbl.pack(side="left", padx=(6, 4), pady=5)

                txt_lbl = tk.Label(frm, text=label,
                                   font=("Helvetica Neue", 10),
                                   bg=_T["BG_CARD"], fg=_T["TEXT_PRIMARY"],
                                   anchor="w")
                txt_lbl.pack(side="left", padx=(0, 20))

                if shortcut:
                    sc_lbl = tk.Label(frm, text=shortcut,
                                      font=("Helvetica Neue", 9),
                                      bg=_T["BG_CARD"], fg=_T["TEXT_MUTED"])
                    sc_lbl.pack(side="right", padx=(0, 10))
                else:
                    sc_lbl = None

                all_w = [frm, icon_lbl, txt_lbl] + ([sc_lbl] if sc_lbl else [])

                def _enter(ev, ws=all_w):
                    for w in ws:
                        try:
                            w.config(bg=_T["BG_HOVER"])
                        except Exception:
                            pass

                def _leave(ev, ws=all_w, bg=_T["BG_CARD"]):
                    for w in ws:
                        try:
                            w.config(bg=bg)
                        except Exception:
                            pass

                def _click(ev, c=cmd):
                    try:
                        pop.destroy()
                    except Exception:
                        pass
                    c()

                for w in all_w:
                    w.bind("<Enter>",    _enter)
                    w.bind("<Leave>",    _leave)
                    w.bind("<Button-1>", _click)

            def _add_sep():
                tk.Frame(inner, bg=_T["BORDER_LIGHT"], height=1).pack(
                    fill="x", padx=6, pady=3)

            _add_item("↩", "Rückgängig",         "Strg+Z",       self._do_undo)
            _add_item("↪", "Wiederherstellen",   "Strg+Shift+Z", self._do_redo)
            _add_sep()
            _add_item("⎘", "Kopieren",           "Strg+C",       self._do_copy)
            _add_item("✂", "Ausschneiden",       "Strg+X",       self._do_cut)
            _add_item("⎗", "Einfügen",           "Strg+V",       self._do_paste)
            _add_item("☰", "Alles auswählen",    "Strg+A",       self._do_select_all)
            _add_sep()
            _add_item("\U0001F50E", "Suche",     "Strg+F",       self._open_search)
            _add_sep()
            _add_item("◄", "Vormonat übertragen", "",             self._copy_from_prev_month)
            _add_sep()
            _add_item("🗑", "Einträge löschen",   "",             self._clear_month_entries)

            pop.update_idletasks()
            # Popup ans Cursor-Position setzen; bei Überlauf nach links/oben korrigieren
            px, py = e.x_root, e.y_root
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            pw = pop.winfo_width()
            ph = pop.winfo_height()
            if px + pw > sw:
                px = sw - pw - 4
            if py + ph > sh:
                py = sh - ph - 4
            pop.geometry(f"+{px}+{py}")

            # Außerhalb klicken → schließen
            def _outside(ev):
                try:
                    if not pop.winfo_exists():
                        return
                    wx, wy = pop.winfo_rootx(), pop.winfo_rooty()
                    ww, wh = pop.winfo_width(), pop.winfo_height()
                    if not (wx <= ev.x_root <= wx + ww and wy <= ev.y_root <= wy + wh):
                        pop.destroy()
                except Exception:
                    pass

            pop._oc_b1 = self.bind_all("<Button-1>",
                                        lambda ev: self.after(10, lambda: _outside(ev)))
            pop.bind("<Escape>", lambda ev: pop.destroy())

            def _restore(ev=None):
                try:
                    self.bind_all("<Button-1>", lambda ev2: self._schedule_refresh())
                except Exception:
                    pass
            pop.bind("<Destroy>", _restore)

        self.bind_all("<Button-3>", _show_ctx)
        self.bind_all("<Control-z>",       self._do_undo)
        self.bind_all("<Control-Z>",       self._do_redo)   # Strg+Shift+Z
        self.bind_all("<Control-Shift-z>", self._do_redo)   # Fallback

    # ── Kategorie-Karte ───────────────────────────────────────────────────────
    def _make_card(self, parent, title, color, key, default_rows, top_pad=0):
        T = self._T()
        outer = tk.Frame(parent, bg=T["BG_APP"])
        outer.pack(fill="x", pady=(top_pad, 0))
        card = tk.Frame(outer, bg=T["BG_CARD"],
                        highlightthickness=1, highlightbackground=T["BORDER"])
        card.pack(fill="x")
        card._rows  = []
        card._key   = key
        card._color = color

        tk.Frame(card, bg=color, height=3).pack(fill="x")
        title_row = tk.Frame(card, bg=T["BG_CARD"])
        title_row.pack(fill="x", padx=14, pady=(10,6))
        tk.Label(title_row, text=title,
                 font=("Helvetica Neue", 13, "bold"),
                 bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(side="left")
        total_var = tk.StringVar(value="0,00 \u20ac")
        card._total_var = total_var
        tk.Label(title_row, textvariable=total_var,
                 font=("Helvetica Neue", 11, "bold"),
                 bg=T["BG_CARD"], fg=color).pack(side="right")
        tk.Label(title_row, text="Gesamt:",
                 font=("Helvetica Neue", 9),
                 bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(side="right", padx=(0,4))
        tk.Frame(card, bg=T["BORDER_LIGHT"], height=1).pack(fill="x", padx=14)

        # Budget progress bar (dynamically visible based on budget setting)
        _bbar_track = tk.Frame(card, bg=T["BG_CARD"], height=5)
        _bbar_track.pack(fill="x", padx=14, pady=(3, 0))
        _bbar_track.pack_propagate(False)
        _bbar_fill = tk.Frame(_bbar_track, bg=T["BG_CARD"], height=5)
        _bbar_fill.place(x=0, y=0, relheight=1.0, relwidth=0.0)
        card._budget_track = _bbar_track
        card._budget_fill  = _bbar_fill

        rows_frame = tk.Frame(card, bg=T["BG_CARD"])
        rows_frame.pack(fill="x", padx=8, pady=4)
        card._rows_frame = rows_frame

        for i in range(default_rows):
            self._add_row(card, i+1)

        add_bar = tk.Frame(card, bg=T["BG_CARD"])
        add_bar.pack(fill="x", padx=12, pady=(2,12))
        tk.Button(add_bar, text="\uff0b  Zeile hinzufügen",
                  font=("Helvetica Neue", 9),
                  bg=T["BG_APP"], fg=NEUTRAL, relief="flat", bd=0, cursor="hand2",
                  activebackground=T["BORDER"], activeforeground=T["TEXT_LABEL"],
                  command=lambda c=card: self._add_row_action(c)).pack(anchor="w")
        return card

    # ── Notizen-Karte ─────────────────────────────────────────────────────────
    def _make_notes_card(self, parent):
        T     = self._T()
        outer = tk.Frame(parent, bg=T["BG_APP"])
        outer.pack(fill="x")

        card = tk.Frame(outer, bg=T["BG_CARD"],
                        highlightthickness=1, highlightbackground=T["BORDER"])
        card.pack(fill="x")

        # Akzentbalken (neutral grau wie Chart-Karte)
        tk.Frame(card, bg=NEUTRAL, height=3).pack(fill="x")

        # Titelzeile
        title_row = tk.Frame(card, bg=T["BG_CARD"])
        title_row.pack(fill="x", padx=14, pady=(10, 6))
        tk.Label(title_row, text="\U0001f4dd  Notizen",
                 font=("Helvetica Neue", 13, "bold"),
                 bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(side="left")
        self._notes_date_var = tk.StringVar(
            value=f"{MONTHS_DE[self.current_month.get()]} {self.current_year.get()}")
        tk.Label(title_row, textvariable=self._notes_date_var,
                 font=("Helvetica Neue", 9),
                 bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(side="right")

        tk.Frame(card, bg=T["BORDER_LIGHT"], height=1).pack(fill="x", padx=14)

        # Text-Widget
        txt_frame = tk.Frame(card, bg=T["BG_CARD"])
        txt_frame.pack(fill="both", expand=True, padx=10, pady=8)

        notes_bg = T["BG_INPUT"] if self.dark_mode else T["BG_CARD"]

        self.notes_text = tk.Text(
            txt_frame,
            font=("Helvetica Neue", 10),
            bg=notes_bg,
            fg=T["TEXT_PRIMARY"],
            insertbackground=T["TEXT_PRIMARY"],
            selectbackground=NEUTRAL,
            selectforeground="#FFFFFF",
            relief="flat",
            bd=0,
            wrap="word",
            height=13,
            padx=10, pady=8,
        )
        self.notes_text.pack(fill="x")

        # Kein Refresh beim Tippen nötig – nur beim FocusOut speichern
        self.notes_text.bind("<FocusOut>", lambda e: self._save_month())

    # ── Info-Fenster ──────────────────────────────────────────────────────────
    def _open_info(self):
        T = self._T()
        win = tk.Toplevel(self)
        win.title("Programmübersicht – Finanzübersicht")
        win.configure(bg=T["BG_APP"])
        win.resizable(True, True)
        win.geometry("800x660")
        win.attributes("-topmost", True)
        win.grab_set()
        pw = self.winfo_width();  ph = self.winfo_height()
        px = self.winfo_rootx(); py = self.winfo_rooty()
        win.geometry(f"800x660+{px + pw//2 - 400}+{py + ph//2 - 330}")

        # ── Scrollbarer Inhalt ────────────────────────────────────────────────
        outer = tk.Frame(win, bg=T["BG_APP"])
        outer.pack(fill="both", expand=True)
        canvas = tk.Canvas(outer, bg=T["BG_APP"], highlightthickness=0)
        vsb = tk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        canvas.configure(yscrollcommand=vsb.set)
        content = tk.Frame(canvas, bg=T["BG_APP"])
        cwin = canvas.create_window((0, 0), window=content, anchor="nw")
        content.bind("<Configure>",
                     lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(cwin, width=e.width))
        def _info_scroll(e):
            try:
                canvas.yview_scroll(int(-1*(e.delta/120)), "units")
            except Exception:
                pass
        canvas.bind_all("<MouseWheel>", _info_scroll)

        def _restore_main_mwheel(e=None):
            if e is not None and e.widget is not win:
                return
            try:
                if hasattr(self, "_global_mousewheel_fn"):
                    self.bind_all("<MouseWheel>", self._global_mousewheel_fn)
            except Exception:
                pass
        win.bind("<Destroy>", _restore_main_mwheel)

        FONT_H1   = ("Helvetica Neue", 15, "bold")
        FONT_H2   = ("Helvetica Neue", 11, "bold")
        FONT_BODY = ("Helvetica Neue", 10)
        FONT_MONO = ("Courier New", 9)
        PAD = 24

        def section(parent, title, color, icon=""):
            """Farbiger Abschnitts-Header."""
            row = tk.Frame(parent, bg=color, pady=6)
            row.pack(fill="x", pady=(18, 0))
            tk.Label(row, text=f"  {icon}  {title}" if icon else f"  {title}",
                     font=FONT_H1, bg=color, fg="#FFFFFF").pack(side="left", padx=8)
            return tk.Frame(parent, bg=T["BG_CARD"],
                            highlightthickness=1, highlightbackground=T["BORDER"])

        def body(card, text):
            tk.Label(card, text=text, font=FONT_BODY,
                     bg=T["BG_CARD"], fg=T["TEXT_LABEL"],
                     justify="left", wraplength=720, anchor="w"
                     ).pack(anchor="w", padx=PAD, pady=(8, 4))

        def hint(card, text):
            tk.Label(card, text=f"  {text}",
                     font=("Helvetica Neue", 9, "italic"),
                     bg=T["BG_CARD"], fg=T["TEXT_MUTED"],
                     justify="left", wraplength=720, anchor="w"
                     ).pack(anchor="w", padx=PAD, pady=(0, 6))

        def swatch_row(card, color, label, detail=""):
            row = tk.Frame(card, bg=T["BG_CARD"])
            row.pack(anchor="w", padx=PAD, pady=3)
            tk.Frame(row, bg=color, width=22, height=22,
                     highlightthickness=1, highlightbackground=T["BORDER"]
                     ).pack(side="left", padx=(0, 10))
            tk.Label(row, text=label, font=FONT_H2,
                     bg=T["BG_CARD"], fg=color).pack(side="left")
            if detail:
                tk.Label(row, text=f"  –  {detail}", font=FONT_BODY,
                         bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(side="left")

        def mock_row(card, name, amount, color=None):
            """Simulierte Eingabezeile als visuelles Beispiel."""
            row = tk.Frame(card, bg=T["BG_INPUT"],
                           highlightthickness=1, highlightbackground=T["BORDER"])
            row.pack(anchor="w", padx=PAD, pady=2, fill="x")
            tk.Label(row, text="①", font=("Helvetica Neue", 8, "bold"),
                     bg=NEUTRAL, fg="#FFFFFF", padx=4).pack(side="left", padx=(4,6), pady=4)
            tk.Label(row, text=name, font=("Helvetica Neue", 10, "bold"),
                     bg=T["BG_INPUT"], fg=T["TEXT_LABEL"]).pack(side="left")
            if color:
                tk.Frame(row, bg=color, width=14, height=14).pack(side="left", padx=6)
            amt_f = tk.Frame(row, bg=T["BG_CARD"],
                             highlightthickness=1, highlightbackground=T["BORDER"])
            amt_f.pack(side="right", padx=6, pady=4)
            tk.Label(amt_f, text=f"€  {amount}", font=("Helvetica Neue", 10),
                     bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"], padx=6).pack()

        # ══════════════════════════════════════════════════════════════════════
        # 1. WILLKOMMEN
        # ══════════════════════════════════════════════════════════════════════
        card = section(content, "Willkommen bei Finanzübersicht", INCOME_CLR, "🏦")
        card.pack(fill="x", padx=0, pady=0)
        body(card, "Finanzübersicht ist eine Desktop-App zur persönlichen Finanzverwaltung. "
                   "Du erfasst monatlich Einnahmen und Ausgaben in übersichtlichen Kategorien "
                   "und behältst so stets den Überblick über deine finanzielle Lage.")
        hint(card, "Alle Daten werden lokal auf deinem Computer gespeichert – keine Cloud, keine Registrierung.")

        # ══════════════════════════════════════════════════════════════════════
        # 2. NAVIGATION
        # ══════════════════════════════════════════════════════════════════════
        card = section(content, "Navigation – Monat & Jahr", "#0284C7", "🗓")
        card.pack(fill="x")
        body(card, "Mit den Pfeilen ◄ ► wechselst du den aktuellen Monat. "
                   "Fährst du mit der Maus über den Monatsnamen, öffnet sich automatisch "
                   "ein Kalender-Dropdown – er bleibt offen solange du über dem Namen oder dem "
                   "Kalender hoverst, und schließt sich sobald du ihn verlässt. "
                   "Die Jahreszahl links zeigt immer das aktuelle Jahr.")
        body(card, "Alternativ navigierst du per Tastatur: ← wechselt zum Vormonat, "
                   "→ zum nächsten Monat – solange kein Texteingabefeld fokussiert ist "
                   "(im Eingabefeld bewegt sich der Cursor wie gewohnt).")
        hint(card, "Beim Monatswechsel werden alle Eingaben des aktuellen Monats automatisch gespeichert.")

        # Aktualisierter Mock-Header (kein 📅, dafür 🔎)
        hdr = tk.Frame(card, bg=T["BG_INPUT"],
                       highlightthickness=1, highlightbackground=T["BORDER"])
        hdr.pack(anchor="w", padx=PAD, pady=(4, 12))
        tk.Label(hdr, text="2025", font=("Helvetica Neue", 14, "bold"),
                 bg=T["BG_INPUT"], fg=T["TEXT_MUTED"], padx=6).pack(side="left")
        tk.Label(hdr, text="◄", font=("Helvetica Neue", 11, "bold"),
                 bg=T["BG_INPUT"], fg=T["TEXT_MUTED"], padx=8).pack(side="left")
        tk.Label(hdr, text="März", font=("Helvetica Neue", 13, "bold"),
                 bg=T["BG_INPUT"], fg=T["TEXT_PRIMARY"], padx=6,
                 cursor="hand2").pack(side="left")
        tk.Label(hdr, text="\U0001F50E", font=("Helvetica Neue", 12),
                 bg=T["BG_INPUT"], fg=T["TEXT_MUTED"], padx=4).pack(side="left")
        tk.Label(hdr, text="►", font=("Helvetica Neue", 11, "bold"),
                 bg=T["BG_INPUT"], fg=T["TEXT_MUTED"], padx=8).pack(side="left")
        tk.Label(hdr, text="ⓘ", font=("Helvetica Neue", 12),
                 bg=T["BG_INPUT"], fg=T["TEXT_MUTED"], padx=6).pack(side="left")
        tk.Label(hdr, text="⚙ Einstellungen",
                 font=("Helvetica Neue", 9, "bold"),
                 bg="#252836", fg=T["TEXT_LABEL"], padx=10, pady=4).pack(side="left", padx=4, pady=4)

        # ══════════════════════════════════════════════════════════════════════
        # 2b. EINTRAGSSUCHE
        # ══════════════════════════════════════════════════════════════════════
        card = section(content, "Eintragssuche \U0001F50E", INCOME_CLR, "")
        card.pack(fill="x")
        body(card, "Der \U0001F50E-Button (direkt neben ⓘ) oder die Tastenkombination Ctrl+F öffnet "
                   "die Eintragssuche. Hier kannst du alle Monate nach Name/Titel oder Betrag durchsuchen.")
        for txt in [
            "• Echtzeit-Suche: Treffer erscheinen sofort während du tippst",
            "• Durchsucht alle Monate und alle Kategorien gleichzeitig",
            "• Suche nach Name (z. B. \"Netflix\") oder nach Betrag (z. B. \"49,99\")",
            "• Ergebnistabelle zeigt: Monat, Kategorie, Name und Betrag",
            "• Doppelklick auf eine Zeile → springt direkt zum Monat und markiert das Betragsfeld",
            "• Fenster bleibt offen – du kannst parallel weiterarbeiten",
            "• Größe und Position des Suchfensters werden gespeichert",
        ]:
            tk.Label(card, text=txt, font=FONT_BODY,
                     bg=T["BG_CARD"], fg=T["TEXT_LABEL"],
                     anchor="w").pack(anchor="w", padx=PAD+8, pady=1)
        hint(card, "Tipp: Doppelklick auf einen Treffer → bei vorhandenem Betrag wird er markiert, "
                   "bei leerem Feld springt der Cursor direkt hinein.")
        tk.Frame(card, bg=T["BG_CARD"], height=8).pack()

        # ══════════════════════════════════════════════════════════════════════
        # 2c. NOTIZEN
        # ══════════════════════════════════════════════════════════════════════
        card = section(content, "Notizen", "#0D9488", "📝")
        card.pack(fill="x")
        body(card, "Unterhalb der Kategorien befindet sich ein freies Notizenfeld für jeden Monat. "
                   "Hier kannst du Anmerkungen, Erinnerungen oder sonstige Infos zum Monat festhalten.")
        hint(card, "Notizen werden beim Monatswechsel automatisch gespeichert – keine manuelle Aktion nötig.")
        tk.Frame(card, bg=T["BG_CARD"], height=8).pack()

        # ══════════════════════════════════════════════════════════════════════
        # 2d. RÜCKGÄNGIG / WIEDERHERSTELLEN
        # ══════════════════════════════════════════════════════════════════════
        card = section(content, "Tastaturkürzel", "#7C3AED", "⌨")
        card.pack(fill="x")
        body(card, "Alle verfügbaren Tastaturkürzel auf einen Blick:")
        for sym, text in [
            ("←",            "Zum Vormonat wechseln  (nicht in Eingabefeldern)"),
            ("→",            "Zum nächsten Monat wechseln  (nicht in Eingabefeldern)"),
            ("Ctrl+F",       "Eintragssuche öffnen"),
            ("Ctrl+Z",       "Letzte Änderung rückgängig machen"),
            ("Ctrl+Shift+Z", "Rückgängig gemachte Änderung wiederherstellen"),
        ]:
            r = tk.Frame(card, bg=T["BG_CARD"])
            r.pack(anchor="w", padx=PAD, pady=2)
            tk.Label(r, text=sym, font=FONT_MONO,
                     bg=T["BG_INPUT"], fg=INCOME_CLR, padx=8, pady=3,
                     highlightthickness=1, highlightbackground=T["BORDER"]).pack(side="left")
            tk.Label(r, text=f"  {text}", font=FONT_BODY,
                     bg=T["BG_CARD"], fg=T["TEXT_LABEL"]).pack(side="left")
        hint(card, "Undo/Redo gilt für den aktuell angezeigten Monat. Beim Monatswechsel wird der Stack geleert.")
        tk.Frame(card, bg=T["BG_CARD"], height=8).pack()

        # ══════════════════════════════════════════════════════════════════════
        # 3. MONATLICHE KATEGORIEN
        # ══════════════════════════════════════════════════════════════════════
        card = section(content, "Monatliche Kategorien", ESSENZ_CLR, "📋")
        card.pack(fill="x")
        body(card, "Jeder Monat hat sechs farblich unterschiedene Kategorien. "
                   "In jede Kategorie trägst du Namen und Betrag ein. "
                   "Die Monatsübersicht rechts aktualisiert sich dabei automatisch.")
        cats_frame = tk.Frame(card, bg=T["BG_CARD"])
        cats_frame.pack(anchor="w", padx=PAD, pady=(4, 12))
        cat_info = [
            (INCOME_CLR,    "Einkommen",    "Gehalt, Nebeneinkünfte …"),
            (ESSENZ_CLR,    "Essenziell",   "Lebensmittel, Miete, Strom …"),
            (FREIZEIT_CLR,  "Freizeit",     "Restaurants, Hobbys, Urlaub …"),
            (AUTO_CLR,      "Auto",         "Tankkosten, Werkstatt …"),
            (VERSICH_CLR,   "Versicherung", "Haftpflicht, KFZ, Kranken …"),
        ]
        for clr, name, desc in cat_info:
            r = tk.Frame(cats_frame, bg=T["BG_CARD"])
            r.pack(anchor="w", pady=2)
            tk.Frame(r, bg=clr, width=18, height=18).pack(side="left", padx=(0, 8))
            tk.Label(r, text=name, font=FONT_H2, bg=T["BG_CARD"], fg=clr).pack(side="left")
            tk.Label(r, text=f" – {desc}", font=FONT_BODY,
                     bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(side="left")

        # ══════════════════════════════════════════════════════════════════════
        # 4. FIXKOSTEN JAHR
        # ══════════════════════════════════════════════════════════════════════
        card = section(content, "Fixkosten Jahr – die besondere Kategorie", FIXKOSTEN_CLR, "📌")
        card.pack(fill="x")
        body(card, "Fixkosten sind Jahreskosten (z. B. Miete, Streaming, Versicherungen), "
                   "die du einmal einträgst – als Jahresbetrag. Das Programm teilt den Betrag "
                   "automatisch durch 12 und rechnet den monatlichen Anteil in die Übersicht ein.")
        body(card, "Änderungen an Fixkosten (Name, Betrag, Farbe) werden sofort gespeichert "
                   "und automatisch ins nächste Jahr übernommen.")

        fix_ex = tk.Frame(card, bg=T["BG_CARD"])
        fix_ex.pack(anchor="w", padx=PAD, pady=(4, 4))
        tk.Label(fix_ex, text="Beispiel:",
                 font=("Helvetica Neue", 9, "bold"),
                 bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(anchor="w")
        mock_row(fix_ex, "Miete",           "12 000",  ESSENZ_CLR)
        mock_row(fix_ex, "Netflix",         "215",     FREIZEIT_CLR)
        mock_row(fix_ex, "KFZ-Versicherung","840",     VERSICH_CLR)
        hint(card, "→ Miete 12 000 ÷ 12 = 1 000 €/Monat, wird automatisch zur Essenziell-Kategorie gezählt.")

        # ══════════════════════════════════════════════════════════════════════
        # 5. FARBSYSTEM BEI FIXKOSTEN
        # ══════════════════════════════════════════════════════════════════════
        card = section(content, "Farbsystem – Fixkosten zuweisen", FREIZEIT_CLR, "🎨")
        card.pack(fill="x")
        body(card, "Jede Fixkosten-Zeile bekommt per Klick auf das farbige Quadrat "
                   "eine Kategorie zugewiesen. So wird der Jahresbetrag der richtigen "
                   "Ausgabenkategorie zugeordnet und im Diagramm korrekt angezeigt.")
        for clr, name, desc in [
            (FIXKOSTEN_CLR, "Fixkosten",    "Allgemeine Fixkosten (Standard)"),
            (ESSENZ_CLR,    "Essenziell",   "Lebensnotwendige Kosten"),
            (FREIZEIT_CLR,  "Freizeit",     "Freizeit & Unterhaltung"),
            (AUTO_CLR,      "Auto",         "Fahrzeugkosten"),
            (VERSICH_CLR,   "Versicherung", "Versicherungsbeiträge"),
        ]:
            swatch_row(card, clr, name, desc)
        body(card, "Eigene (benutzerdefinierte) Kategorien tauchen ebenfalls im Farbwähler auf, "
                   "sobald sie angelegt wurden. Wähle die passende Kategorie-Farbe, um eine "
                   "Fixkosten-Zeile der benutzerdefinierten Kategorie zuzuordnen.")
        hint(card, "Die Farbe einer Fixkosten-Zeile bestimmt, zu welcher Kategorie der monatliche "
                   "Anteil im Diagramm und in der Gesamtübersicht zählt.")
        tk.Frame(card, bg=T["BG_CARD"], height=8).pack()

        # ══════════════════════════════════════════════════════════════════════
        # 5b. EIGENE KATEGORIEN
        # ══════════════════════════════════════════════════════════════════════
        card = section(content, "Eigene Kategorien", "#6366F1", "✚")
        card.pack(fill="x")
        body(card, "Unter ⚙ Einstellungen kannst du mit \"+ Kategorie hinzufügen\" eigene "
                   "Kategorien erstellen. Jede neue Kategorie erhält einen Standardnamen "
                   "und eine Startfarbe, die du sofort anpassen kannst.")
        for txt in [
            "• Name und Farbe über ⚙ Einstellungen jederzeit ändern",
            "• Eigene Kategorie per × in ⚙ Einstellungen löschen",
            "• Im Monatsblatt erscheint sie als eigener Abschnitt mit + / × Zeilen",
            "• Fixkosten können per Farbwähler einer eigenen Kategorie zugewiesen werden",
            "• In Gesamtübersicht, Ranking und Treemap wird sie wie eine Standardkategorie behandelt",
        ]:
            tk.Label(card, text=txt, font=FONT_BODY,
                     bg=T["BG_CARD"], fg=T["TEXT_LABEL"],
                     anchor="w").pack(anchor="w", padx=PAD+8, pady=1)
        hint(card, "Tipp: Vergib aussagekräftige Namen wie 'Sport', 'Haustier' oder 'Bildung'. "
                   "Gelöschte Kategorien bleiben in historischen Daten erhalten.")
        tk.Frame(card, bg=T["BG_CARD"], height=8).pack()

        # ══════════════════════════════════════════════════════════════════════
        # 5c. MONATS-TORTENDIAGRAMM MIT FIXKOSTEN-SCHRAFFUR
        # ══════════════════════════════════════════════════════════════════════
        card = section(content, "Monats-Kreisdiagramm & Fixkostenanteil", FIXKOSTEN_CLR, "🥧")
        card.pack(fill="x")
        body(card, "Das Kreisdiagramm im Hauptfenster zeigt die Ausgabenaufteilung des aktuellen "
                   "Monats. Kategorien, die Fixkosten enthalten, haben einen schraffierten Bereich: "
                   "helle Fläche + Linien in der Originalfarbe markieren den Fixkostenanteil. "
                   "Eine dezente Trennlinie trennt variablen und fixen Anteil.")
        body(card, "Der Fixkostenanteil erscheint auch als Prozentzahl über dem Diagramm "
                   "(\"Fixkostenanteil: X%\") – er gibt an, wie viel der Gesamtausgaben "
                   "auf Fixkosten entfällt.")
        hint(card, "Die Schraffur hilft auf einen Blick zu sehen, welche Kosten fix und "
                   "welche variabel sind.")
        tk.Frame(card, bg=T["BG_CARD"], height=8).pack()

        # ══════════════════════════════════════════════════════════════════════
        # 5d. SPARZIEL
        # ══════════════════════════════════════════════════════════════════════
        card = section(content, "Sparziel (Sparquote)", SAVINGS_CLR, "🎯")
        card.pack(fill="x")
        body(card, "Im Hauptfenster kannst du eine Ziel-Sparquote in Prozent eingeben "
                   "(z. B. 20 für 20 %). Das Sparziel wirkt sich auf die Gesamtübersicht aus:")
        for txt in [
            "• Im kumulierten Ersparnis-Verlauf erscheint eine gepunktete Ziellinie",
            "• Die Ziellinie zeigt: Wie viel hätte ich kumuliert gespart, wenn ich jeden Monat X% gespart hätte?",
            "• Liegt deine Linie über der Ziellinie – hast du dein Ziel übertroffen",
            "• Liegt deine Linie darunter – zeigt die Differenz, wie viel noch aufzuholen ist",
        ]:
            tk.Label(card, text=txt, font=FONT_BODY,
                     bg=T["BG_CARD"], fg=T["TEXT_LABEL"],
                     anchor="w").pack(anchor="w", padx=PAD+8, pady=1)
        body(card, "💡 Tipp – Fadenkreuz im kumulierten Verlauf:")
        for txt in [
            "• Fahre mit der Maus über das Diagramm → ein Fadenkreuz folgt dem Cursor",
            "• Ein grüner Punkt markiert den nächsten Datenpunkt auf der Linie",
            "• Ein Tooltip zeigt Monat und kumulierten Betrag in €",
            "• Prognosepunkte werden als '(Prognose)' gekennzeichnet",
            "• Das Fadenkreuz verschwindet sobald du das Diagramm verlässt",
        ]:
            tk.Label(card, text=txt, font=FONT_BODY,
                     bg=T["BG_CARD"], fg=T["TEXT_LABEL"],
                     anchor="w").pack(anchor="w", padx=PAD+8, pady=1)
        hint(card, "Ein Sparziel von 0 blendet die Ziellinie aus. "
                   "Der ⓘ-Button im kumulierten Chart erklärt die Linien im Detail.")
        tk.Frame(card, bg=T["BG_CARD"], height=8).pack()

        # ══════════════════════════════════════════════════════════════════════
        # 6. ZEILEN BEARBEITEN
        # ══════════════════════════════════════════════════════════════════════
        card = section(content, "Zeilen bearbeiten", "#0D9488", "✏️")
        card.pack(fill="x")
        body(card, "Jede Kategorie hat mehrere Eingabezeilen. Du kannst:")
        bullets = [
            ("✎  Name ändern",    "Klicke auf den Stift-Button → Name bearbeiten → ✔ bestätigen"),
            ("＋  Zeile hinzufügen","Der + Button am unteren Rand jeder Kategorie fügt eine neue Zeile ein"),
            ("✕  Zeile löschen",   "Das × Symbol rechts neben dem Betragsfeld entfernt die Zeile dauerhaft"),
            ("🧮  Rechnen",         "Im Betragsfeld kannst du direkt rechnen: 50+30 → Enter → ergibt 80"),
        ]
        for sym, text in bullets:
            r = tk.Frame(card, bg=T["BG_CARD"])
            r.pack(anchor="w", padx=PAD, pady=2)
            tk.Label(r, text=sym, font=FONT_H2,
                     bg=T["BG_CARD"], fg=INCOME_CLR, width=20, anchor="w").pack(side="left")
            tk.Label(r, text=text, font=FONT_BODY,
                     bg=T["BG_CARD"], fg=T["TEXT_LABEL"]).pack(side="left")

        calc_demo = tk.Frame(card, bg=T["BG_CARD"])
        calc_demo.pack(anchor="w", padx=PAD, pady=(8, 4))
        tk.Label(calc_demo, text="Beispiel Rechner:", font=("Helvetica Neue", 9, "bold"),
                 bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(anchor="w")
        for expr, result in [("100+50", "150"), ("1200*12", "14400"), ("350-80", "270")]:
            r = tk.Frame(calc_demo, bg=T["BG_CARD"])
            r.pack(anchor="w", pady=1)
            tk.Label(r, text=f"  Eingabe: ", font=FONT_BODY,
                     bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(side="left")
            tk.Label(r, text=expr, font=FONT_MONO,
                     bg=T["BG_INPUT"], fg=INCOME_CLR, padx=6, pady=2).pack(side="left")
            tk.Label(r, text="  →  Enter  →  ", font=FONT_BODY,
                     bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(side="left")
            tk.Label(r, text=result, font=FONT_MONO,
                     bg=T["BG_INPUT"], fg=SAVINGS_CLR, padx=6, pady=2).pack(side="left")
        tk.Frame(card, bg=T["BG_CARD"], height=8).pack()

        # ══════════════════════════════════════════════════════════════════════
        # 7. SPEICHERN & BACKUPS
        # ══════════════════════════════════════════════════════════════════════
        card = section(content, "Automatisches Speichern & Backups", SAVINGS_CLR, "💾")
        card.pack(fill="x")
        body(card, "Du musst nie manuell speichern – die App speichert automatisch:")
        for txt in [
            "• Beim Wechsel des Monats (Pfeile oder Kalender)",
            "• Beim Schließen der App",
            "• Bei jeder Fixkosten-Änderung (sofort)",
            "• Beim Bearbeiten eines Zeilen-Namens",
        ]:
            tk.Label(card, text=txt, font=FONT_BODY,
                     bg=T["BG_CARD"], fg=T["TEXT_LABEL"],
                     anchor="w").pack(anchor="w", padx=PAD+8, pady=1)
        body(card, "Backups: Beim Monatswechsel wird automatisch ein Backup erstellt. "
                   "Über den 💾 Backup-Button oben kannst du alle Backups einsehen, "
                   "öffnen und bei Bedarf wiederherstellen.")
        hint(card, f"Gespeichert wird in: finanz_daten.json  |  Backups im Ordner: backups/")

        # ══════════════════════════════════════════════════════════════════════
        # 8. DIAGRAMME & MONATSÜBERSICHT
        # ══════════════════════════════════════════════════════════════════════
        card = section(content, "Monatsübersicht & Diagramme", "#EC4899", "📊")
        card.pack(fill="x")
        body(card, "Die Monatsübersicht rechts zeigt alle Ausgaben des aktuellen Monats "
                   "als Kreis- oder Balkendiagramm. Du kannst zwischen beiden Ansichten "
                   "oben am Diagramm umschalten.")
        body(card, "Die Legende darunter listet alle Positionen mit Betrag auf. "
                   "Fixkosten werden anteilig (÷ 12) eingerechnet. "
                   "Über 📈 Gesamtübersicht siehst du alle Monate im Jahresvergleich.")
        body(card, "💡 Tipp – Klick auf ein Tortenstück:")
        click_demo = tk.Frame(card, bg=T["BG_CARD"])
        click_demo.pack(anchor="w", padx=PAD, pady=(0, 8))
        steps = [
            ("①", INCOME_CLR,   "Klicke auf ein farbiges Segment im Kreisdiagramm …"),
            ("②", FREIZEIT_CLR, "… es öffnet sich ein Detailfenster mit dem monatlichen Verlauf dieser Kategorie"),
            ("③", SAVINGS_CLR,  "Im Verlaufsfenster siehst du alle Monate auf einen Blick"),
        ]
        for num, clr, txt in steps:
            r = tk.Frame(click_demo, bg=T["BG_CARD"])
            r.pack(anchor="w", pady=2)
            tk.Label(r, text=num, font=("Helvetica Neue", 10, "bold"),
                     bg=clr, fg="#FFFFFF", width=3, padx=4
                     ).pack(side="left", padx=(0, 8))
            tk.Label(r, text=txt, font=FONT_BODY,
                     bg=T["BG_CARD"], fg=T["TEXT_LABEL"]).pack(side="left")
        hint(card, "Nur im Kreisdiagramm-Modus verfügbar – Balkendiagramm hat keinen Drilldown.")
        diag_row = tk.Frame(card, bg=T["BG_CARD"])
        diag_row.pack(anchor="w", padx=PAD, pady=(4, 12))
        for label, desc in [("◑ Kreisdiagramm", "Anteil jeder Kategorie"),
                             ("▌▐ Balkendiagramm", "Vergleich aller Kategorien")]:
            r = tk.Frame(diag_row, bg=T["BG_INPUT"],
                         highlightthickness=1, highlightbackground=T["BORDER"])
            r.pack(side="left", padx=(0,8), pady=2)
            tk.Label(r, text=label, font=("Helvetica Neue", 9, "bold"),
                     bg=T["BG_INPUT"], fg=T["TEXT_PRIMARY"], padx=10, pady=4).pack(side="left")
            tk.Label(r, text=f" – {desc}", font=("Helvetica Neue", 9),
                     bg=T["BG_INPUT"], fg=T["TEXT_MUTED"], padx=4).pack(side="left")

        # ══════════════════════════════════════════════════════════════════════
        # 9. EINSTELLUNGEN
        # ══════════════════════════════════════════════════════════════════════
        card = section(content, "⚙ Kategorieeinstellungen", "#6366F1", "")
        card.pack(fill="x", pady=(0, 24))
        body(card, "Über ⚙ Einstellungen kannst du für jede Kategorie:")
        for txt in [
            "• Den angezeigten Namen ändern (z. B. 'Essenziell' → 'Haushalt')",
            "• Die Farbe individuell anpassen – mit einem vollständigen Farbwähler",
            "• Die Reihenfolge der Kategorien verändern",
            "• Eigene neue Kategorien hinzufügen",
        ]:
            tk.Label(card, text=txt, font=FONT_BODY,
                     bg=T["BG_CARD"], fg=T["TEXT_LABEL"],
                     anchor="w").pack(anchor="w", padx=PAD+8, pady=1)
        hint(card, "Farbänderungen wirken sich auf Diagramme und Beschriftungen überall in der App aus.")
        tk.Frame(card, bg=T["BG_CARD"], height=12).pack()

        # ── Schließen-Button ──────────────────────────────────────────────────
        tk.Button(win, text="Schließen", font=("Helvetica Neue", 10, "bold"),
                  bg=INCOME_CLR, fg="#FFFFFF", relief="flat", bd=0,
                  cursor="hand2", padx=20, pady=8,
                  activebackground="#2563EB", activeforeground="#FFFFFF",
                  command=win.destroy).pack(pady=12)

    # ── Rechner ───────────────────────────────────────────────────────────────
    def _open_calculator(self):
        import subprocess, sys
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", "-a", "Calculator"])
            elif sys.platform == "win32":
                subprocess.Popen("calc.exe")
            else:
                # Linux fallback: versuche gängige Taschenrechner
                for cmd in ("gnome-calculator", "kcalc", "xcalc"):
                    try:
                        subprocess.Popen(cmd)
                        break
                    except FileNotFoundError:
                        continue
        except Exception:
            pass

    def _on_goal_changed(self):
        try:
            val = float(self._savings_goal_var.get().replace(",", "."))
            val = max(0.0, val)  # allow any positive value, no upper cap
            self._savings_goal_var.set(str(int(val)) if val == int(val) else str(val))
        except (ValueError, TypeError):
            self._savings_goal_var.set("0")
        self._schedule_refresh()
        try:
            _goal_pct_save = float(self._savings_goal_var.get())
        except (ValueError, TypeError):
            _goal_pct_save = 0
        save_settings({"dark_mode": self.dark_mode,
                       "last_year": self.current_year.get(),
                       "last_month": self.current_month.get(),
                       "overview_chart": self.overview_chart,
                       "cat_settings": self._cat_settings,
                       "custom_cat_order": self._custom_cat_order,
                       "savings_goal_pct": _goal_pct_save,
                       "drilldown_geometry": self._drilldown_geometry,
                       "overview_geometry":   self._overview_geometry,
                       "main_geometry":       self._main_geometry,
                       "search_geometry":     self._search_geometry,
                       "search_exact_amount": self._search_exact_amount,
                       "search_hide_empty":   self._search_hide_empty})

    # ── Kategorie-Einstellungen Dropdown ─────────────────────────────────────
    def _open_cat_settings(self):
        T = self._T()
        # Toggle: close if already open
        if self._cat_settings_popup and self._cat_settings_popup.winfo_exists():
            self._cat_settings_popup.destroy()
            self._cat_settings_popup = None
            return

        pop = tk.Toplevel(self)
        self._cat_settings_popup = pop
        pop.overrideredirect(True)
        pop.attributes("-topmost", True)
        pop.configure(bg=T["BG_CARD"])

        self.update_idletasks()
        bx = self._cat_btn.winfo_rootx()
        by = self._cat_btn.winfo_rooty() + self._cat_btn.winfo_height() + 4
        pop.geometry(f"+{bx}+{by}")

        outer = tk.Frame(pop, bg=T["BORDER"], padx=1, pady=1)
        outer.pack(fill="both", expand=True)
        inner = tk.Frame(outer, bg=T["BG_CARD"])
        inner.pack(fill="both", expand=True)

        # Header
        hdr = tk.Frame(inner, bg=T["BG_CARD"])
        hdr.pack(fill="x", padx=14, pady=(12, 4))
        tk.Label(hdr, text="Kategorie Einstellungen",
                 font=("Helvetica Neue", 11, "bold"),
                 bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(side="left")
        tk.Frame(inner, bg=T["BORDER_LIGHT"], height=1).pack(fill="x", padx=14, pady=(0, 6))

        # Per-category rows
        BUILTIN_KEYS = ["savings", "income", "essenz", "freizeit", "fixkosten", "auto", "versicherung"]
        cat_keys = BUILTIN_KEYS + [k for k in self._custom_cat_order if k in self._cat_settings]
        name_vars  = {}
        color_vars = {}
        budget_vars = {}

        for key in cat_keys:
            row = tk.Frame(inner, bg=T["BG_CARD"])
            row.pack(fill="x", padx=14, pady=4)

            # Color swatch (accent color)
            clr_frame = tk.Frame(row, bg=self._cc(key), width=22, height=22,
                                 cursor="hand2",
                                 highlightthickness=1, highlightbackground=T["BORDER"])
            clr_frame.pack(side="left", padx=(0, 8))
            clr_frame.pack_propagate(False)

            # Name entry
            nv = tk.StringVar(value=self._cn(key))
            name_vars[key] = nv
            ne = tk.Entry(row, textvariable=nv, width=14,
                          font=("Helvetica Neue", 9),
                          bg=T["BG_INPUT"], fg=T["TEXT_PRIMARY"],
                          insertbackground=T["TEXT_PRIMARY"],
                          relief="flat", bd=0,
                          highlightthickness=1, highlightbackground=T["BORDER"])
            ne.pack(side="left", padx=(0, 6), ipady=3)

            # Budget limit field
            _raw_bgt = self._cat_settings.get(key, {}).get("budget", 0) or 0
            bv = tk.StringVar(value=str(int(_raw_bgt)) if _raw_bgt == int(_raw_bgt) else str(_raw_bgt))
            budget_vars[key] = bv
            be = tk.Entry(row, textvariable=bv, width=7,
                          font=("Helvetica Neue", 9),
                          bg=T["BG_INPUT"], fg=T["TEXT_PRIMARY"],
                          insertbackground=T["TEXT_PRIMARY"],
                          relief="flat", bd=0,
                          highlightthickness=1, highlightbackground=T["BORDER"])
            be.pack(side="left", padx=(0,2), ipady=3)
            tk.Label(row, text="€ Limit",
                     font=("Helvetica Neue", 7),
                     bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(side="left", padx=(0,8))

            # Store color var
            cv = tk.StringVar(value=self._cc(key))
            color_vars[key] = cv

            # Click on color swatch → open color picker
            def open_color_picker(k=key, cf=clr_frame, cv_ref=cv):
                def on_pick(hex_color):
                    # Suppress the outside-close handler briefly so
                    # clicking OK in the color picker doesn't also close
                    # the cat-settings popup.
                    self._suppress_cat_outside = True
                    try:
                        self.after(500, lambda: setattr(self, '_suppress_cat_outside', False))
                    except Exception:
                        pass
                    cv_ref.set(hex_color)
                    try:
                        if cf.winfo_exists():
                            cf.config(bg=hex_color)
                    except Exception:
                        pass
                HexColorPicker(self, T, initial=cv_ref.get(),
                               title=f"Farbe \u2013 {self._cn(k)}", callback=on_pick)
            clr_frame.bind("<Button-1>", lambda e, f=open_color_picker: f())

            # Delete button for custom categories
            if key not in BUILTIN_KEYS:
                def make_del(k=key):
                    def _del():
                        if k in self._cat_settings:
                            del self._cat_settings[k]
                        if k in self._custom_cat_order:
                            self._custom_cat_order.remove(k)
                        pop.destroy()
                        self._cat_settings_popup = None
                        self._apply_cat_settings()
                    return _del
                tk.Button(row, text="\xd7",
                          font=("Helvetica Neue", 11, "bold"),
                          bg=T["BG_CARD"], fg="#EF4444",
                          relief="flat", bd=0, cursor="hand2", padx=6,
                          command=make_del()).pack(side="right")

        tk.Frame(inner, bg=T["BORDER_LIGHT"], height=1).pack(fill="x", padx=14, pady=(4, 2))

        def _add_custom_cat():
            import time
            new_key = f"custom_{int(time.time()*1000) % 999999}"
            self._cat_settings[new_key] = {"name": "Neue Kategorie", "color": "#6366F1"}
            self._custom_cat_order.append(new_key)
            pop.destroy()
            self._cat_settings_popup = None
            self._apply_cat_settings()

        add_btn_row = tk.Frame(inner, bg=T["BG_CARD"])
        add_btn_row.pack(fill="x", padx=14, pady=(0, 4))
        tk.Button(add_btn_row, text="+ Kategorie hinzuf\u00fcgen",
                  font=("Helvetica Neue", 9),
                  bg=T["BG_CARD"], fg=self._cc("income"),
                  relief="flat", bd=0, cursor="hand2", padx=0, pady=2,
                  command=_add_custom_cat).pack(anchor="w")

        tk.Frame(inner, bg=T["BORDER_LIGHT"], height=1).pack(fill="x", padx=14, pady=(4, 6))

        btn_row = tk.Frame(inner, bg=T["BG_CARD"])
        btn_row.pack(fill="x", padx=14, pady=(0, 12))

        def _reset():
            for key in BUILTIN_KEYS:
                self._cat_settings[key] = dict(DEFAULT_CAT_SETTINGS[key])
            pop.destroy()
            self._cat_settings_popup = None
            self._apply_cat_settings()

        def _apply():
            for key in cat_keys:
                if key not in self._cat_settings:
                    self._cat_settings[key] = {}
                default_name = DEFAULT_CAT_SETTINGS.get(key, {}).get("name", key)
                self._cat_settings[key]["name"]  = name_vars[key].get().strip() or default_name
                self._cat_settings[key]["color"] = color_vars[key].get()
                budget_str = budget_vars.get(key, tk.StringVar()).get().strip().replace(",", ".")
                try:
                    budget_val = float(budget_str) if budget_str else 0.0
                except ValueError:
                    budget_val = 0.0
                self._cat_settings[key]["budget"] = budget_val if budget_val > 0 else 0
            pop.destroy()
            self._cat_settings_popup = None
            self._apply_cat_settings()

        tk.Button(btn_row, text="Zur\u00fccksetzen",
                  font=("Helvetica Neue", 9),
                  bg=T["BG_INPUT"], fg=T["TEXT_MUTED"],
                  relief="flat", bd=0, cursor="hand2", padx=10, pady=4,
                  command=_reset).pack(side="left")
        tk.Button(btn_row, text="\u00dcbernehmen",
                  font=("Helvetica Neue", 9, "bold"),
                  bg=self._cc("income"), fg="#FFFFFF",
                  relief="flat", bd=0, cursor="hand2", padx=14, pady=4,
                  command=_apply).pack(side="right")

        def _outside(event):
            # Temporarily suppressed after color picker OK is clicked
            if getattr(self, '_suppress_cat_outside', False):
                return
            # Nicht schließen wenn ein modales Fenster (z.B. HexColorPicker) den Grab hält
            try:
                grabbed = self.grab_current()
                if grabbed and grabbed is not pop:
                    return
            except Exception:
                pass
            try:
                if not pop.winfo_exists():
                    return
                wx, wy = pop.winfo_rootx(), pop.winfo_rooty()
                ww, wh = pop.winfo_width(), pop.winfo_height()
                if not (wx <= event.x_root <= wx+ww and wy <= event.y_root <= wy+wh):
                    pop.destroy()
                    self._cat_settings_popup = None
            except Exception:
                pass
        pop._oc_id = self.bind_all("<Button-1>", lambda e: self.after(80, lambda: _outside(e)))

        def _restore_refresh_binding(e=None):
            # When the popup is destroyed, restore the global _schedule_refresh binding.
            try:
                self.bind_all("<Button-1>", lambda ev: self._schedule_refresh())
            except Exception:
                pass
        pop.bind("<Destroy>", _restore_refresh_binding)

    def _apply_cat_settings(self):
        """Save cat_settings and rebuild the entire UI."""
        self._save_month()
        try:
            _goal_pct_save = float(self._savings_goal_var.get())
        except (ValueError, TypeError):
            _goal_pct_save = 0
        save_settings({"dark_mode": self.dark_mode,
                       "last_year": self.current_year.get(),
                       "last_month": self.current_month.get(),
                       "overview_chart": self.overview_chart,
                       "cat_settings": self._cat_settings,
                       "custom_cat_order": self._custom_cat_order,
                       "savings_goal_pct": _goal_pct_save,
                       "drilldown_geometry": self._drilldown_geometry,
                       "overview_geometry":   self._overview_geometry,
                       "main_geometry":       self._main_geometry,
                       "search_geometry":     self._search_geometry,
                       "search_exact_amount": self._search_exact_amount,
                       "search_hide_empty":   self._search_hide_empty})
        # Invalidate legend cache so it rebuilds with new colors/names
        self._legend_key_cache = None
        plt.close("all")
        for w in self.winfo_children():
            w.destroy()
        self._build_ui()
        self._load_month()

    # ── Titelübernahme ────────────────────────────────────────────────────────
    def _copy_titles_forward(self):
        self._save_month()
        current_m = self.current_month.get()
        current_y = self.current_year.get()
        current_key = self._month_key()

        titles = {}
        for cat, card in [
            ("income",       self.income_card),
            ("essenz",       self.essenz_card),
            ("freizeit",     self.freizeit_card),
            ("auto",         self.auto_card),
            ("versicherung", self.versich_card),
        ]:
            titles[cat] = [r["title"].get() for r in card._rows]

        for k in self._custom_cat_order:
            if k in self._custom_cards:
                titles[k] = [r["title"].get() for r in self._custom_cards[k]._rows]

        def _apply_titles(month_data):
            for cat, cat_titles in titles.items():
                rows = month_data.get(cat, [])
                month_data[cat] = [
                    {"title": title, "amount": rows[i]["amount"] if i < len(rows) else ""}
                    for i, title in enumerate(cat_titles)
                ]

        # Restliche Monate des aktuellen Jahres (auch noch nicht gespeicherte)
        for m in range(current_m + 1, 12):
            key = f"{current_y}-{m+1:02d}"
            month_data = self.data.get(key, {})
            _apply_titles(month_data)
            self.data[key] = month_data

        # Alle bereits gespeicherten Monate in zukünftigen Jahren
        for key in sorted(k for k in self.data
                          if not k.startswith("year_") and k > current_key
                          and not k.startswith(f"{current_y}-")):
            _apply_titles(self.data[key])

        save_data(self.data)

    # ── Monatsdiagramm-Modus ──────────────────────────────────────────────────
    def _set_month_chart(self, mode):
        T = self._T()
        self.month_chart = mode
        self._month_chart_btn_pie.config(
            bg=INCOME_CLR if mode == "pie" else T["BG_INPUT"],
            fg="#FFFFFF"   if mode == "pie" else T["TEXT_LABEL"])
        self._month_chart_btn_bar.config(
            bg=INCOME_CLR if mode == "bar" else T["BG_INPUT"],
            fg="#FFFFFF"   if mode == "bar" else T["TEXT_LABEL"])
        self._update_chart()

    # ── Eingabezeile ──────────────────────────────────────────────────────────
    def _add_row(self, card, idx, title_text=None, amount_text="", row_color=None):
        T    = self._T()
        is_fix = (card._key == "fixkosten")
        if title_text is None:
            title_text = f"{card._key.capitalize()} {idx}"
        if row_color is None:
            row_color = FIXKOSTEN_CLR if is_fix else card._color

        row_frame = tk.Frame(card._rows_frame, bg=T["BG_CARD"], pady=3)
        row_frame.pack(fill="x")

        badge = tk.Label(row_frame, text=str(idx), width=2,
                         font=("Helvetica Neue", 8, "bold"),
                         bg=NEUTRAL, fg="#FFFFFF", padx=3)
        badge.pack(side="left", padx=(2,6))

        title_var   = tk.StringVar(value=title_text)
        title_entry = tk.Entry(row_frame, textvariable=title_var,
                               font=("Helvetica Neue", 10, "bold"),
                               bg=T["BG_CARD"], fg=T["TEXT_LABEL"],
                               insertbackground=T["TEXT_PRIMARY"],
                               relief="flat", bd=0, width=1,
                               disabledforeground=T["TEXT_LABEL"],
                               disabledbackground=T["BG_CARD"])
        title_entry.pack(side="left", padx=(0,2), fill="x", expand=True)
        title_entry.config(state="disabled")

        edit_btn = tk.Button(row_frame, text="\u270e",
                             font=("Helvetica Neue", 9),
                             bg=T["BG_CARD"], fg=NEUTRAL, bd=0, cursor="hand2",
                             activebackground=T["BG_HOVER"],
                             activeforeground=T["TEXT_PRIMARY"])
        # edit_btn wird weiter unten rechts gepackt

        def toggle_edit(e=title_entry, b=edit_btn, _T=T, _is_fix=is_fix):
            if e.cget("state") == "disabled":
                self._pre_edit_snapshot()
                e.config(state="normal", bg=_T["BG_INPUT"], relief="flat",
                         highlightthickness=1, highlightbackground=_T["BORDER"])
                b.config(text="\u2714", fg=_T["TEXT_PRIMARY"])
                e.focus_set()
            else:
                e.config(state="disabled", bg=_T["BG_CARD"],
                         relief="flat", highlightthickness=0)
                b.config(text="\u270e", fg=NEUTRAL)
                self._commit_edit_if_changed()
                self._schedule_refresh()
                if _is_fix:
                    self._save_fixkosten_now()
                else:
                    self._copy_titles_forward()
        edit_btn.config(command=toggle_edit)
        title_entry.bind("<Return>", lambda ev: toggle_edit())

        # Farbwähler-Kästchen (nur Fixkosten) – wird weiter unten rechts gepackt
        color_var = tk.StringVar(value=row_color)
        row_data  = {}   # filled below; forward reference for picker closure

        if is_fix:
            color_btn = tk.Frame(row_frame, bg=row_color, width=18, height=18,
                                 relief="flat", cursor="hand2",
                                 highlightthickness=1,
                                 highlightbackground=T["BORDER"])
            color_btn.pack_propagate(False)
            color_btn.bind("<Button-1>",
                           lambda ev, btn=color_btn, cv=color_var, rd=row_data:
                           self._show_fix_color_picker(btn, cv, rd))
        else:
            color_btn = None

        # Betrag (wird weiter unten gepackt – Reihenfolge rechts festgelegt)
        amount_var  = tk.StringVar(value=amount_text)
        amt_wrapper = tk.Frame(row_frame, bg=T["BG_INPUT"],
                               highlightthickness=1, highlightbackground=T["BORDER"])
        tk.Label(amt_wrapper, text="\u20ac", font=("Helvetica Neue", 9),
                 bg=T["BG_INPUT"], fg=T["TEXT_MUTED"], padx=3).pack(side="left")
        amt_entry = tk.Entry(amt_wrapper, textvariable=amount_var,
                             font=("Helvetica Neue", 11),
                             bg=T["BG_INPUT"], fg=T["TEXT_PRIMARY"],
                             insertbackground=T["TEXT_PRIMARY"],
                             relief="flat", bd=0, width=9, justify="right")
        amt_entry.pack(side="left", padx=(0,4), pady=3)

        def _on_amt_eval_save(var=amount_var, _is_fix=is_fix):
            result = self._eval_expr(var.get())
            if result is not None:
                var.set(result)
            self._schedule_refresh()
            if _is_fix:
                self._save_fixkosten_now()

        amt_entry.bind("<FocusIn>",  lambda ev: self._pre_edit_snapshot())

        def _on_amt_focusout(ev, var=amount_var, _is_fix=is_fix):
            self._commit_edit_if_changed()
            if _is_fix:
                # Eval + Refresh sofort, _save_fixkosten_now mit Delay (50ms):
                # Verhindert, dass FocusOut (ausgelöst durch Klick auf ✕-Button)
                # den Dialog öffnet und den Maus-Release des ✕-Buttons schluckt.
                # delete_row setzt _fix_dlg_open=True → blockiert diese verzögerte Auslösung.
                r = self._eval_expr(var.get())
                if r is not None:
                    var.set(r)
                self._schedule_refresh()
                self.after(50, self._save_fixkosten_now)
            else:
                _on_amt_eval_save(var, _is_fix)
        amt_entry.bind("<FocusOut>", _on_amt_focusout)

        def _on_amt_return(ev, e=amt_entry, var=amount_var, _is_fix=is_fix):
            _on_amt_eval_save(var, _is_fix)
            self._focus_next_entry(e)
        amt_entry.bind("<Return>", _on_amt_return)
        amt_entry.bind("<Down>",   lambda ev, e=amt_entry: self._focus_next_entry(e))
        amt_entry.bind("<Up>",     lambda ev, e=amt_entry: self._focus_prev_entry(e))

        del_btn = tk.Button(row_frame, text="\u2715",
                            font=("Helvetica Neue", 8),
                            bg=T["BG_CARD"], fg=NEUTRAL, bd=0, cursor="hand2",
                            activebackground=T["BG_HOVER"],
                            activeforeground=DEFICIT_CLR)

        def delete_row(rf=row_frame, c=card, _is_fix=is_fix):
            # Bei Fixkosten: Flag sofort setzen damit FocusOut-Destroy
            # nicht _save_fixkosten_now triggert und den Dialog blockiert
            if _is_fix:
                self._fix_dlg_open = True
            self._push_undo_state()
            c._rows = [r for r in c._rows if r["frame"] is not rf]
            self._block_undo_push = True
            try:
                rf.destroy()
            finally:
                self._block_undo_push = False
            self._renumber(c)
            self._schedule_refresh()
            if _is_fix:
                self._fix_dlg_open = False
                self._save_fixkosten_now()
            else:
                self._copy_titles_forward()
        del_btn.config(command=delete_row)

        # Rechts außen: [€ Betrag], direkt links davon: [X] [Farbe] [✎]
        amt_wrapper.pack(side="right", padx=(0,4))
        del_btn.pack(side="right", padx=(0,2))
        if is_fix:
            color_btn.pack(side="right", padx=(0,4))
        edit_btn.pack(side="right", padx=(0,2))

        row_data.update({"frame": row_frame, "title": title_var,
                         "amount": amount_var, "badge": badge,
                         "color_var": color_var, "color_btn": color_btn,
                         "amt_entry": amt_entry})
        card._rows.append(row_data)
        # Hover-Tooltip für Fixkosten-Zeilen (S3/S4): erst nach update() binden,
        # damit row_data vollständig befüllt ist wenn der Handler aufgerufen wird.
        if is_fix:
            self._bind_fix_row_hover(row_frame, row_data)
        return row_data

    # ── Fixkosten-Farbwähler ──────────────────────────────────────────────────
    def _show_fix_color_picker(self, anchor, color_var, row_data):
        T   = self._T()
        pop = tk.Toplevel(self)
        pop.overrideredirect(True)
        pop.attributes("-topmost", True)
        pop.configure(bg=T["BG_CARD"])
        self.update_idletasks()
        x = anchor.winfo_rootx()
        y = anchor.winfo_rooty() + anchor.winfo_height() + 2
        pop.geometry(f"+{x}+{y}")

        outer = tk.Frame(pop, bg=T["BORDER"], padx=1, pady=1)
        outer.pack()
        inner = tk.Frame(outer, bg=T["BG_CARD"], padx=10, pady=10)
        inner.pack()
        tk.Label(inner, text="Kategorie zuweisen:",
                 font=("Helvetica Neue", 8, "bold"),
                 bg=T["BG_CARD"], fg=T["TEXT_LABEL"]).pack(anchor="w", pady=(0,6))

        fix_options = [
            (self._cc(k), self._cn(k))
            for k in ("fixkosten", "essenz", "freizeit", "auto", "versicherung")
        ] + [
            (self._cc(k), self._cn(k))
            for k in self._custom_cat_order
        ]
        for clr, label in fix_options:
            rf = tk.Frame(inner, bg=T["BG_CARD"], cursor="hand2")
            rf.pack(fill="x", pady=2)
            is_sel = (color_var.get() == clr)

            swatch = tk.Frame(rf, bg=clr, width=18, height=18)
            swatch.pack(side="left", padx=(0,8))
            swatch.pack_propagate(False)
            lbl = tk.Label(rf, text=label,
                           font=("Helvetica Neue", 9, "bold" if is_sel else ""),
                           bg=T["BG_CARD"],
                           fg=clr if is_sel else T["TEXT_LABEL"],
                           cursor="hand2")
            lbl.pack(side="left")

            def pick(c=clr, p=pop, cv=color_var, rd=row_data, anch=anchor):
                # Snapshot VOR Farbänderung auf aktuellen UI-Stand (mit alter Farbe)
                # setzen – nur die Farbe gilt dann als Diff. Verhindert, dass
                # ungespeicherte Betrags-Änderungen beim Zukunfts-Monat ungewollt
                # zurückgesetzt werden.
                self._fixkosten_snapshot = [
                    {"title":  r["title"].get(),
                     "amount": r["amount"].get(),
                     "color":  r["color_var"].get() if r.get("color_var") else FIXKOSTEN_CLR}
                    for r in self.fixkosten_card._rows
                ]
                cv.set(c)
                if rd.get("color_btn"):
                    rd["color_btn"].config(bg=c)
                p.destroy()
                self._schedule_refresh()
                self._save_fixkosten_now()

            rf.bind("<Button-1>",     lambda e, p=pick: p())
            swatch.bind("<Button-1>", lambda e, p=pick: p())
            lbl.bind("<Button-1>",    lambda e, p=pick: p())

        def _outside_click(event):
            try:
                wx, wy = pop.winfo_rootx(), pop.winfo_rooty()
                ww, wh = pop.winfo_width(), pop.winfo_height()
                if not (wx <= event.x_root <= wx+ww and wy <= event.y_root <= wy+wh):
                    pop.destroy()
            except Exception:
                pass
        pop._outside_id = self.bind_all("<Button-1>",
                                        lambda e: self.after(60, lambda: _outside_click(e)))
        pop.protocol("WM_DELETE_WINDOW", pop.destroy)

        def _restore_refresh_after_picker(e=None):
            # Restore the global _schedule_refresh binding when the popup is gone.
            try:
                self.bind_all("<Button-1>", lambda ev: self._schedule_refresh())
            except Exception:
                pass
        pop.bind("<Destroy>", _restore_refresh_after_picker)

    # ── Row-Verwaltung ────────────────────────────────────────────────────────
    def _add_row_action(self, card):
        self._push_undo_state()
        # Fixkosten: leerer Titel damit _is_default_fix() die neue Zeile nicht als
        # System-Platzhalter behandelt und sie in Ziel-Monaten korrekt anzeigt.
        if card._key == "fixkosten":
            self._add_row(card, len(card._rows)+1, title_text="")
        else:
            self._add_row(card, len(card._rows)+1)
        self._schedule_refresh()
        if card._key == "fixkosten":
            self._save_fixkosten_now()
        else:
            self._copy_titles_forward()

    def _renumber(self, card):
        for i, row in enumerate(card._rows):
            row["badge"].config(text=str(i+1))

    def _all_amt_entries(self):
        """Alle Betragsfelder in Anzeigereihenfolge."""
        entries = []
        cards = [self.income_card, self.essenz_card, self.freizeit_card,
                 self.fixkosten_card, self.auto_card, self.versich_card]
        for k in self._custom_cat_order:
            if k in self._custom_cards:
                cards.append(self._custom_cards[k])
        for card in cards:
            for row in card._rows:
                w = row.get("amt_entry")
                if w and w.winfo_exists():
                    entries.append(w)
        return entries

    def _focus_next_entry(self, current):
        entries = self._all_amt_entries()
        if not entries:
            return
        try:
            idx = (entries.index(current) + 1) % len(entries)
        except ValueError:
            idx = 0
        entries[idx].focus_set()
        entries[idx].select_range(0, "end")

    def _focus_prev_entry(self, current):
        entries = self._all_amt_entries()
        if not entries:
            return
        try:
            idx = (entries.index(current) - 1) % len(entries)
        except ValueError:
            idx = 0
        entries[idx].focus_set()
        entries[idx].select_range(0, "end")

    def _update_rows_inplace(self, card, new_rows_data):
        """Update row values without destroy/recreate → zero flicker."""
        is_fix = (card._key == "fixkosten")
        curr   = len(card._rows)
        need   = len(new_rows_data)
        # Update existing
        for i in range(min(curr, need)):
            card._rows[i]["title"].set(new_rows_data[i]["title"])
            card._rows[i]["amount"].set(new_rows_data[i]["amount"])
            card._rows[i]["badge"].config(text=str(i+1))
            if is_fix:
                clr = new_rows_data[i].get("color", FIXKOSTEN_CLR)
                card._rows[i]["color_var"].set(clr)
                if card._rows[i]["color_btn"]:
                    card._rows[i]["color_btn"].config(bg=clr)
        # Add new
        for i in range(curr, need):
            clr = new_rows_data[i].get("color", FIXKOSTEN_CLR) if is_fix else None
            self._add_row(card, i+1,
                          new_rows_data[i]["title"],
                          new_rows_data[i]["amount"],
                          row_color=clr)
        # Remove surplus
        for _ in range(need, curr):
            row = card._rows.pop()
            row["frame"].destroy()

    # ── Fixkosten nach Farbe aufteilen ────────────────────────────────────────
    def _build_fix_color_to_cat(self):
        """Dynamische Farbe→Kategorie-Map inkl. benutzerdefinierter Kategorien."""
        mapping = dict(FIX_COLOR_TO_CAT)
        for ck in self._custom_cat_order:
            clr = self._cc(ck)
            # Benutzerdefinierte Kategorien überschreiben Built-in bei gleicher Farbe,
            # da der Nutzer diese Farbe explizit für seine Kategorie gewählt hat.
            mapping[clr] = ck
        return mapping

    # ── Fixkosten-Zeilen Hover-Tooltip (S3/S4) ────────────────────────────────
    def _destroy_fix_row_tip(self):
        """Hover-Tooltip sofort entfernen und Job canceln."""
        if getattr(self, '_fix_row_tip_job', None):
            self.after_cancel(self._fix_row_tip_job)
            self._fix_row_tip_job = None
        t = getattr(self, '_fix_row_tip', None)
        if t:
            try:
                t.destroy()
            except Exception:
                pass
            self._fix_row_tip = None

    def _schedule_fix_row_tip_hide(self, event=None):
        """Verzögertes Ausblenden – wird bei erneutem Enter abgebrochen."""
        if getattr(self, '_fix_row_tip_job', None):
            self.after_cancel(self._fix_row_tip_job)
        self._fix_row_tip_job = self.after(120, self._destroy_fix_row_tip)

    def _on_fix_row_enter(self, row_data, event):
        """Hover-Enter auf einer Fixkosten-Zeile → Tooltip anzeigen."""
        if getattr(self, '_fix_row_tip_job', None):
            self.after_cancel(self._fix_row_tip_job)
            self._fix_row_tip_job = None
        self._show_fix_row_tip(row_data, event)

    def _show_fix_row_tip(self, row_data, event):
        """Erstellt den Hover-Tooltip für eine Fixkosten-Zeile (Stil wie Balkendiagramm)."""
        T = self._T()
        # Bestehenden Tooltip entfernen
        t_old = getattr(self, '_fix_row_tip', None)
        if t_old:
            try:
                t_old.destroy()
            except Exception:
                pass
            self._fix_row_tip = None

        # ── Zeilen-Infos auslesen ──────────────────────────────────────────
        title  = row_data.get("title")
        title  = title.get() if hasattr(title, "get") else str(title or "")
        cv     = row_data.get("color_var")
        color  = cv.get() if cv else FIXKOSTEN_CLR
        cat_map  = self._build_fix_color_to_cat()
        cat_key  = cat_map.get(color, "fixkosten")
        cat_name = self._cn(cat_key)
        cat_clr  = self._cc(cat_key)

        # ── Einstellungsinfo bestimmen ────────────────────────────────────
        key        = self._month_key()
        md         = self.data.get(key, {})
        month_only = md.get("fixkosten_month_only", False)
        yr         = self.current_year.get()
        yd         = self.data.get(f"year_{yr}", {})
        from_mo    = yd.get("fixkosten_from_month", 1)
        mo_num     = self.current_month.get() + 1
        mo_name    = MONTHS_DE[mo_num - 1]

        if month_only:
            setting_main = f"Nur {mo_name} {yr}"
            setting_sub  = "Monatsspezifische Einstellung"
            setting_clr  = FREIZEIT_CLR
        else:
            from_mo_name = MONTHS_DE[from_mo - 1]
            setting_main = f"Jahreseinstellung · gilt ab {from_mo_name}"
            setting_sub  = f"Jahr {yr}"
            setting_clr  = INCOME_CLR

        # ── Tooltip-Fenster bauen (identischer Stil wie Balkendiagramm-Tooltip) ──
        tip = tk.Toplevel(self)
        tip.overrideredirect(True)
        tip.attributes("-topmost", True)
        tip.geometry("+9999+9999")
        tip.configure(bg=T["BORDER"])

        outer = tk.Frame(tip, bg=T["BG_CARD"])
        outer.pack(padx=1, pady=1)
        stripe = tk.Frame(outer, bg=color, height=3)
        stripe.pack(fill="x")
        pad = tk.Frame(outer, bg=T["BG_CARD"])
        pad.pack(fill="x", padx=10, pady=(5, 6))

        tk.Label(pad, text=title or "–",
                 font=("Helvetica Neue", 9, "bold"),
                 bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(anchor="w")
        tk.Label(pad, text=f"Kategorie: {cat_name}",
                 font=("Helvetica Neue", 8),
                 bg=T["BG_CARD"], fg=cat_clr).pack(anchor="w")
        tk.Frame(pad, bg=T["BORDER_LIGHT"], height=1).pack(fill="x", pady=(4, 3))
        tk.Label(pad, text=setting_main,
                 font=("Helvetica Neue", 8, "bold"),
                 bg=T["BG_CARD"], fg=setting_clr).pack(anchor="w")
        tk.Label(pad, text=setting_sub,
                 font=("Helvetica Neue", 7),
                 bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(anchor="w")

        self._fix_row_tip = tip
        # Höhe berechnen nachdem Layout fertig ist, dann oben-rechts positionieren
        tip.update_idletasks()
        h = tip.winfo_reqheight()
        tip.geometry(f"+{event.x_root + 14}+{event.y_root - h - 5}")

    def _move_fix_row_tip(self, event):
        """Verschiebt den Hover-Tooltip smooth zur aktuellen Mausposition (oben-rechts)."""
        t = getattr(self, '_fix_row_tip', None)
        if t:
            try:
                if t.winfo_exists():
                    h = t.winfo_height()
                    if h <= 1:
                        h = t.winfo_reqheight()
                    t.geometry(f"+{event.x_root + 14}+{event.y_root - h - 5}")
            except Exception:
                pass

    def _bind_fix_row_hover(self, widget, row_data):
        """Bindet Hover-Events rekursiv an alle Kind-Widgets einer Fixkosten-Zeile.
        tk.Entry-Widgets und deren Wrapper-Frame werden ausgeschlossen – das
        Betrag-Eingabefeld (inkl. €-Label-Rahmen) soll kein Popup auslösen."""
        if isinstance(widget, tk.Entry):
            return
        # Wrapper-Frame des Betragsfeldes ausschliessen (enthält €-Label + Entry)
        amt = row_data.get("amt_entry")
        if amt and widget is amt.master:
            return
        widget.bind("<Enter>",  lambda ev, rd=row_data: self._on_fix_row_enter(rd, ev))
        widget.bind("<Leave>",  self._schedule_fix_row_tip_hide)
        widget.bind("<Motion>", self._move_fix_row_tip)
        for child in widget.winfo_children():
            self._bind_fix_row_hover(child, row_data)

    def _get_fixkosten_split(self):
        """Returns dict cat_key → [(name, value_per_month)]"""
        color_to_cat = self._build_fix_color_to_cat()
        all_cats = list(dict.fromkeys(list(FIX_COLOR_TO_CAT.values()) + self._custom_cat_order))
        result = {cat: [] for cat in all_cats}
        for row in self.fixkosten_card._rows:
            try:
                v = float(row["amount"].get().replace(",", "."))
            except ValueError:
                v = 0.0
            clr = row["color_var"].get() if row.get("color_var") else FIXKOSTEN_CLR
            cat = color_to_cat.get(clr, "fixkosten")
            if cat not in result:
                result[cat] = []
            result[cat].append((row["title"].get(), v / 12.0))
        return result

    # ── Datenzugriff ──────────────────────────────────────────────────────────
    def _get_rows_data(self, card):
        result = []
        for row in card._rows:
            try:
                v = float(row["amount"].get().replace(",", "."))
            except ValueError:
                v = 0.0
            result.append((row["title"].get(), v))
        return result

    def _get_amounts(self, card):
        return [v for _, v in self._get_rows_data(card)]

    # ── Debounced refresh ─────────────────────────────────────────────────────
    def _schedule_refresh(self):
        if self._refresh_pending is not None:
            self.after_cancel(self._refresh_pending)
        self._refresh_pending = self.after(60, self._do_refresh)

    def _refresh(self):
        self._do_refresh()

    def _do_refresh(self):
        self._refresh_pending = None
        self._update_totals()
        self._update_chart()

    # ── Budget-Fortschrittsbalken ─────────────────────────────────────────────
    def _update_budget_bar(self, card, total):
        T = self._T()
        budget = 0.0
        try:
            raw = self._cat_settings.get(card._key, {}).get("budget", 0) or 0
            budget = float(str(raw).replace(",", "."))
        except (ValueError, TypeError):
            pass
        try:
            track = card._budget_track
            fill  = card._budget_fill
            if not track.winfo_exists():
                return
            if budget <= 0:
                track.config(bg=T["BG_CARD"])
                fill.place_configure(relwidth=0.0)
                return
            pct = min(1.0, max(0.0, total / budget))
            clr = "#10B981" if pct < 0.60 else ("#F59E0B" if pct < 0.85 else "#EF4444")
            track.config(bg=T["BORDER_LIGHT"])
            fill.config(bg=clr)
            fill.place_configure(relwidth=pct)
        except Exception:
            pass

    # ── Gesamtbeträge ─────────────────────────────────────────────────────────
    def _update_totals(self):
        fix_total_year = sum(self._get_amounts(self.fixkosten_card))
        self.fixkosten_card._total_var.set(
            f"{fix_total_year:,.2f} \u20ac  \xf712  {fix_total_year/12:,.2f} \u20ac/Mo")
        self._update_budget_bar(self.fixkosten_card, fix_total_year / 12)
        for card in (self.income_card, self.essenz_card, self.freizeit_card,
                     self.auto_card, self.versich_card):
            total = sum(self._get_amounts(card))
            card._total_var.set(f"{total:,.2f} \u20ac")
            self._update_budget_bar(card, total)
        for card in self._custom_cards.values():
            total = sum(self._get_amounts(card))
            card._total_var.set(f"{total:,.2f} \u20ac")
            self._update_budget_bar(card, total)

    # ── Kreisdiagramm + tkinter-Legende ──────────────────────────────────────
    def _update_chart(self):
        T         = self._T()
        fix_split = self._get_fixkosten_split()

        income_rows   = self._get_rows_data(self.income_card)
        essenz_rows   = self._get_rows_data(self.essenz_card)
        freizeit_rows = self._get_rows_data(self.freizeit_card)
        auto_rows     = self._get_rows_data(self.auto_card)
        versich_rows  = self._get_rows_data(self.versich_card)
        custom_rows   = {k: self._get_rows_data(self._custom_cards[k])
                         for k in self._custom_cat_order if k in self._custom_cards}

        total_income   = sum(v for _, v in income_rows   if v > 0)
        total_essenz   = sum(v for _, v in essenz_rows   if v > 0) + \
                         sum(v for _, v in fix_split["essenz"])
        total_freizeit = sum(v for _, v in freizeit_rows if v > 0) + \
                         sum(v for _, v in fix_split["freizeit"])
        total_auto     = sum(v for _, v in auto_rows     if v > 0) + \
                         sum(v for _, v in fix_split["auto"])
        total_versich  = sum(v for _, v in versich_rows  if v > 0) + \
                         sum(v for _, v in fix_split["versicherung"])
        total_fixmo    = sum(v for _, v in fix_split["fixkosten"])
        total_custom   = sum(
            sum(v for _, v in rows if v > 0) + sum(v for _, v in fix_split.get(k, []) if v > 0)
            for k, rows in custom_rows.items()
        )
        total_out      = (total_essenz + total_freizeit + total_auto +
                          total_versich + total_fixmo + total_custom)
        savings        = max(0.0, total_income - total_out)

        # ── Jahresdurchschnitt pro Kategorie (für Hover-Tooltip) ──────────
        _cur_yr_str  = str(self.current_year.get())
        _dyn_ctc_mo  = self._build_fix_color_to_cat()
        _check_cats_mo = ["income","essenz","freizeit","auto","versicherung"] + self._custom_cat_order
        _yr_sums = {"income":0.0,"essenz":0.0,"freizeit":0.0,"auto":0.0,
                    "versicherung":0.0,"fixkosten":0.0,"savings":0.0}
        for _ck in self._custom_cat_order:
            _yr_sums.setdefault(_ck, 0.0)
        _yr_n = 0
        _yd_data = self.data.get(f"year_{_cur_yr_str}", {})
        _yd_fix_rows_base = _yd_data.get("fixkosten", [])
        _yd_from_mo = _yd_data.get("fixkosten_from_month", 1)
        for _mo in range(1, 13):
            _mk = f"{_cur_yr_str}-{_mo:02d}"
            _md = self.data.get(_mk, {})
            if not any(any(self._parse_amount(r.get("amount","")) > 0
                           for r in _md.get(_cat, []))
                       for _cat in _check_cats_mo):
                continue
            _yr_n += 1
            # Fixkosten pro Monat korrekt auflösen (month_only / from_month berücksichtigen)
            if _md.get("fixkosten_month_only") or "fixkosten" in _md:
                _yd_fix_rows = _md.get("fixkosten", [])
            elif _mo < _yd_from_mo:
                _yd_fix_rows = []
            else:
                _yd_fix_rows = _yd_fix_rows_base
            _fbc = {_cat: 0.0 for _cat in list(FIX_COLOR_TO_CAT.values()) + self._custom_cat_order}
            for _fr in _yd_fix_rows:
                _amt2 = self._parse_amount(_fr.get("amount","")) / 12.0
                _clr2 = _fr.get("color", FIXKOSTEN_CLR)
                _fbc[_dyn_ctc_mo.get(_clr2, "fixkosten")] += _amt2
            _inc2 = sum(self._parse_amount(r.get("amount","")) for r in _md.get("income", []))
            _ess2 = sum(self._parse_amount(r.get("amount","")) for r in _md.get("essenz", [])) + _fbc["essenz"]
            _fre2 = sum(self._parse_amount(r.get("amount","")) for r in _md.get("freizeit", [])) + _fbc["freizeit"]
            _aut2 = sum(self._parse_amount(r.get("amount","")) for r in _md.get("auto", [])) + _fbc["auto"]
            _ver2 = sum(self._parse_amount(r.get("amount","")) for r in _md.get("versicherung", [])) + _fbc["versicherung"]
            _fix2 = _fbc["fixkosten"]
            _cust_tot2 = 0.0
            for _ck in self._custom_cat_order:
                _cv2 = sum(self._parse_amount(r.get("amount","")) for r in _md.get(_ck, [])) + _fbc.get(_ck, 0.0)
                _yr_sums[_ck] = _yr_sums.get(_ck, 0.0) + _cv2
                _cust_tot2 += _cv2
            _yr_sums["income"] += _inc2; _yr_sums["essenz"] += _ess2; _yr_sums["freizeit"] += _fre2
            _yr_sums["auto"] += _aut2; _yr_sums["versicherung"] += _ver2; _yr_sums["fixkosten"] += _fix2
            _yr_sums["savings"] += max(0.0, _inc2 - _ess2 - _fre2 - _aut2 - _ver2 - _fix2 - _cust_tot2)
        _yr_n = max(_yr_n, 1)
        _cat_yr_avg = {k: v / _yr_n for k, v in _yr_sums.items()}

        # ── Diagramm ──────────────────────────────────────────────────────
        if self.month_chart == "bar":
            # Balken: tkinter-Canvas, kein matplotlib nötig
            if self.mpl_canvas.get_tk_widget().winfo_ismapped():
                self.mpl_canvas.get_tk_widget().pack_forget()
            # Reihenfolge: zuerst Canvas, dann Trennlinie + Legende
            self._chart_legend_sep.pack_forget()
            self._legend_outer.pack_forget()
            bar_items = [(lbl, v, c, a) for lbl, v, c, a in [
                (self._cn("income"),      total_income,   self._cc("income"),       _cat_yr_avg.get("income", 0.0)),
                (self._cn("essenz"),      total_essenz,   self._cc("essenz"),       _cat_yr_avg.get("essenz", 0.0)),
                (self._cn("freizeit"),    total_freizeit, self._cc("freizeit"),     _cat_yr_avg.get("freizeit", 0.0)),
                (self._cn("fixkosten") + "/Mo", total_fixmo, self._cc("fixkosten"), _cat_yr_avg.get("fixkosten", 0.0)),
                (self._cn("auto"),        total_auto,     self._cc("auto"),         _cat_yr_avg.get("auto", 0.0)),
                (self._cn("versicherung"),total_versich,  self._cc("versicherung"), _cat_yr_avg.get("versicherung", 0.0)),
                (self._cn("savings"),     savings,        self._cc("savings"),      _cat_yr_avg.get("savings", 0.0)),
                *[(self._cn(k),
                   sum(v for _,v in rows if v > 0) + sum(v for _,v in fix_split.get(k,[]) if v > 0),
                   self._cc(k), _cat_yr_avg.get(k, 0.0))
                  for k, rows in custom_rows.items()],
            ] if v > 0]
            n_bars = len(bar_items)
            bar_canvas_h = max(120, n_bars * 32 + 36)
            self._bar_canvas.config(height=bar_canvas_h)
            if not self._bar_canvas.winfo_ismapped():
                self._bar_canvas.pack(fill="x", expand=False)
            self._chart_legend_sep.pack(fill="x", padx=14, pady=(4,0))
            self._legend_outer.pack(fill="both", expand=True)
            self._draw_tk_bars(bar_items)
        else:
            # Torte: matplotlib
            if self._bar_canvas.winfo_ismapped():
                self._bar_canvas.pack_forget()
            if not self._chart_legend_sep.winfo_ismapped():
                self._chart_legend_sep.pack(fill="x", padx=14, pady=(4,0))
            if not self._legend_outer.winfo_ismapped():
                self._legend_outer.pack(fill="both", expand=True)
            if not self.mpl_canvas.get_tk_widget().winfo_ismapped():
                self.mpl_canvas.get_tk_widget().pack(fill="both", expand=True)

            self.ax.clear()
            self.ax.set_facecolor(T["BG_CARD"])
            self.fig.set_facecolor(T["BG_CARD"])
            segs_full = [(v, c, ck, cn, av) for v, c, ck, cn, av in [
                (total_essenz,   self._cc("essenz"),       "essenz",       self._cn("essenz"),       _cat_yr_avg.get("essenz", 0.0)),
                (total_freizeit, self._cc("freizeit"),     "freizeit",     self._cn("freizeit"),     _cat_yr_avg.get("freizeit", 0.0)),
                (total_fixmo,    self._cc("fixkosten"),    "fixkosten",    self._cn("fixkosten"),    _cat_yr_avg.get("fixkosten", 0.0)),
                (total_auto,     self._cc("auto"),         "auto",         self._cn("auto"),         _cat_yr_avg.get("auto", 0.0)),
                (total_versich,  self._cc("versicherung"), "versicherung", self._cn("versicherung"), _cat_yr_avg.get("versicherung", 0.0)),
                (savings,        self._cc("savings"),      "savings",      self._cn("savings"),      _cat_yr_avg.get("savings", 0.0)),
                *[(sum(v for _,v in rows if v > 0) + sum(v for _,v in fix_split.get(k,[]) if v > 0),
                   self._cc(k), k, self._cn(k), _cat_yr_avg.get(k, 0.0))
                  for k, rows in custom_rows.items()],
            ] if v > 0]
            segs = [(v, c) for v, c, *_ in segs_full]
            if not segs:
                self.ax.text(0, 0, "Noch keine\nDaten",
                             ha="center", va="center",
                             color=T["TEXT_MUTED"], fontsize=10)
                self.ax.set_xlim(-1,1); self.ax.set_ylim(-1,1); self.ax.axis("off")
            else:
                wedges, _, autotexts = self.ax.pie(
                    [s for s,_ in segs], colors=[c for _,c in segs], labels=None,
                    autopct=lambda p: f"{p:.0f}%" if p > 4 else "",
                    startangle=90, pctdistance=0.68,
                    wedgeprops=dict(linewidth=0.5, edgecolor="#777777"), radius=0.90)
                for at in autotexts:
                    at.set_color("#FFFFFF"); at.set_fontsize(8); at.set_fontweight("bold")
                # ── Hover-Tooltip + Drilldown ─────────────────────────────
                for _cid_attr in ('_pie_hover_cid', '_pie_pick_cid'):
                    if getattr(self, _cid_attr, None) is not None:
                        try: self.fig.canvas.mpl_disconnect(getattr(self, _cid_attr))
                        except Exception: pass
                # Persistent tip window – create once, update content per hover
                if getattr(self, '_pie_tip_win', None) is not None:
                    try: self._pie_tip_win.destroy()
                    except Exception: pass
                _tw = tk.Toplevel(self); _tw.overrideredirect(True)
                _tw.attributes("-topmost", True); _tw.geometry("+9999+9999")
                try: _tw.wm_attributes("-disabled", True)
                except Exception: pass
                _tw.configure(bg=T["BORDER"])
                _tw_out = tk.Frame(_tw, bg=T["BG_CARD"]); _tw_out.pack(padx=1, pady=1)
                _tw_stripe = tk.Frame(_tw_out, bg=T["BG_CARD"], height=3); _tw_stripe.pack(fill="x")
                _tw_pad = tk.Frame(_tw_out, bg=T["BG_CARD"]); _tw_pad.pack(fill="x", padx=10, pady=(5,6))
                _tw_name = tk.Label(_tw_pad, text="", font=("Helvetica Neue", 9, "bold"),
                                    bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]); _tw_name.pack(anchor="w")
                _tw_val  = tk.Label(_tw_pad, text="", font=("Helvetica Neue", 8),
                                    bg=T["BG_CARD"], fg=T["TEXT_MUTED"]); _tw_val.pack(anchor="w")
                _tw_avg  = tk.Label(_tw_pad, text="", font=("Helvetica Neue", 8),
                                    bg=T["BG_CARD"], fg=T["TEXT_MUTED"]); _tw_avg.pack(anchor="w")
                self._pie_tip_win = _tw
                _pie_last_idx = [-1]; _pie_hide_job = [None]
                _pie_snap2 = segs_full[:]
                _pie_wdgs2 = wedges[:]
                _pie_seg_total = max(sum(s[0] for s in segs_full), 1e-9)
                _PIE_R = 0.90
                def _pie_cancel_hide():
                    if _pie_hide_job[0]: self.after_cancel(_pie_hide_job[0]); _pie_hide_job[0] = None
                def _pie_do_hide():
                    try:
                        if _tw.winfo_exists():
                            _tw.geometry("+9999+9999")
                    except Exception: pass
                    _pie_last_idx[0] = -1
                def _pie_hide():
                    _pie_cancel_hide(); _pie_hide_job[0] = self.after(60, _pie_do_hide)
                def _pie_update(cat_name, val, avg_val, pct, clr, sx, sy):
                    try:
                        if not _tw.winfo_exists(): return
                        _tw_stripe.configure(bg=clr)
                        _tw_name.configure(text=f"{cat_name}  {pct:.1f}\u202f%")
                        _tw_val.configure(text=f"{val:,.2f}\u00a0\u20ac")
                        _tw_avg.configure(text=f"\u00d8 {avg_val:,.2f}\u00a0\u20ac / Monat")
                        _tw.geometry(f"+{sx + 14}+{sy - 76}")
                    except Exception: pass
                def _pie_idx_at(ev, _w=_pie_wdgs2, _r=_PIE_R):
                    if ev.xdata is None or ev.ydata is None: return -1
                    if math.sqrt(ev.xdata**2 + ev.ydata**2) > _r: return -1
                    ang = math.degrees(math.atan2(ev.ydata, ev.xdata)) % 360
                    for i, wdg in enumerate(_w):
                        t1, t2 = wdg.theta1 % 360, wdg.theta2 % 360
                        if t1 <= t2:
                            if t1 <= ang <= t2: return i
                        else:
                            if ang >= t1 or ang <= t2: return i
                    return -1
                def _on_pie_hover(ev, _s=_pie_snap2, _tot=_pie_seg_total):
                    if ev.inaxes is None: _pie_hide(); return
                    i = _pie_idx_at(ev)
                    if i >= 0:
                        _pie_cancel_hide()
                        _pie_last_idx[0] = i
                        _wgt = self.mpl_canvas.get_tk_widget()
                        sx = _wgt.winfo_rootx() + int(ev.x) + 2
                        sy = _wgt.winfo_rooty() + _wgt.winfo_height() - int(ev.y) - 2
                        _pct = _s[i][0] / _tot * 100
                        _pie_update(_s[i][3], _s[i][0], _s[i][4], _pct, _s[i][1], sx, sy)
                    else:
                        _pie_hide()
                self._pie_hover_cid = self.fig.canvas.mpl_connect('motion_notify_event', _on_pie_hover)
                # Drilldown: Linksklick auf Segment → Kategorie-Monatsverlauf
                for wedge in wedges:
                    wedge.set_picker(True)
                _snap = segs_full[:]
                _wdgs = wedges[:]
                def _on_pie_pick(event, _s=_snap, _w=_wdgs):
                    if not hasattr(event, 'artist'): return
                    me = getattr(event, 'mouseevent', None)
                    if me is None or me.button not in (1, 3): return
                    try: idx = _w.index(event.artist)
                    except ValueError: return
                    if 0 <= idx < len(_s):
                        _pie_do_hide()
                        self._open_cat_drilldown(_s[idx][2], _s[idx][3])
                self._pie_pick_cid = self.fig.canvas.mpl_connect('pick_event', _on_pie_pick)
                # ── Fixkosten-Anteil schraffiert markieren ─────────────────
                fix_per_cat_mo = {
                    "essenz":       sum(v for _, v in fix_split.get("essenz", [])       if v > 0),
                    "freizeit":     sum(v for _, v in fix_split.get("freizeit", [])     if v > 0),
                    "fixkosten":    total_fixmo,
                    "auto":         sum(v for _, v in fix_split.get("auto", [])         if v > 0),
                    "versicherung": sum(v for _, v in fix_split.get("versicherung", []) if v > 0),
                    "savings":      0.0,
                    **{k: sum(v for _, v in fix_split.get(k, []) if v > 0)
                       for k in self._custom_cat_order},
                }
                _old_hlw = matplotlib.rcParams.get('hatch.linewidth', 1.0)
                matplotlib.rcParams['hatch.linewidth'] = 5.0
                for wdg, (val, clr, ck, *_) in zip(wedges, segs_full):
                    fix_v = fix_per_cat_mo.get(ck, 0.0)
                    if fix_v <= 0 or val <= 0:
                        continue
                    t1, t2 = wdg.theta1, wdg.theta2
                    fix_span = (t2 - t1) * fix_v / val
                    _lclr = self._lighten_color(clr, factor=0.28)
                    # Helle Fläche (Zwischenräume ausgefüllt) + Originalfarbe als Linien
                    self.ax.add_patch(matplotlib.patches.Wedge(
                        (0, 0), 0.90, t1, t1 + fix_span,
                        facecolor=_lclr, hatch='//', edgecolor=clr,
                        linewidth=0, zorder=3))
                    # Dezente Trennlinie (wie Tortenstück-Grenzen)
                    if fix_v < val:
                        _sep_rad = math.radians(t1 + fix_span)
                        self.ax.plot(
                            [0, 0.90 * math.cos(_sep_rad)],
                            [0, 0.90 * math.sin(_sep_rad)],
                            color=_lclr, linewidth=0.5, zorder=4)
                matplotlib.rcParams['hatch.linewidth'] = _old_hlw
                for at in autotexts:
                    at.set_zorder(6)
                total_all_fix_mo = sum(fix_per_cat_mo.values())
                if total_out > 0 and total_all_fix_mo > 0:
                    fix_pct_mo = total_all_fix_mo / total_out * 100
                    self.ax.set_title(f"Fixkostenanteil: {fix_pct_mo:.1f}%",
                                      color=T["TEXT_MUTED"], fontsize=8, pad=4)
            self.fig.subplots_adjust(top=0.87, bottom=0.05, left=0.05, right=0.95)
            self.mpl_canvas.draw()

        # ── tkinter-Legende (Torte + Balken) ─────────────────────────────
        if self.month_chart in ("pie", "bar"):
            # Nur neu aufbauen wenn sich Daten oder Theme geändert haben → kein Flackern
            _fix_key = tuple(sorted((k, tuple(v)) for k, v in fix_split.items()))
            _cat_color_key = tuple(
                (k, self._cc(k))
                for k in ["savings", "income", "essenz", "freizeit", "fixkosten", "auto", "versicherung"]
                         + self._custom_cat_order
            )
            _custom_key = tuple((k, tuple(v)) for k, v in custom_rows.items())
            _legend_key = (
                tuple(income_rows), tuple(essenz_rows), tuple(freizeit_rows),
                tuple(auto_rows), tuple(versich_rows),
                _fix_key, self.month_chart, T["BG_CARD"], _cat_color_key,
                _custom_key,
            )
            if getattr(self, "_legend_key_cache", None) == _legend_key:
                # Keine Datenänderung → Legende unverändert lassen
                pass
            else:
                self._legend_key_cache = _legend_key
                for w in self.legend_frame.winfo_children():
                    w.destroy()
                tk.Frame(self.legend_frame, bg=T["BG_CARD"], height=6).pack(fill="x")

                legend_cats = [
                    (self._cn("income"),      self._cc("income"),
                     [(n,v) for n,v in income_rows   if v > 0],       total_income),
                    (self._cn("essenz"),      self._cc("essenz"),
                     [(n,v) for n,v in essenz_rows   if v > 0] +
                     fix_split["essenz"],                              total_essenz),
                    (self._cn("freizeit"),    self._cc("freizeit"),
                     [(n,v) for n,v in freizeit_rows if v > 0] +
                     fix_split["freizeit"],                            total_freizeit),
                    (self._cn("fixkosten") + "/Mo", self._cc("fixkosten"),
                     fix_split["fixkosten"],                           total_fixmo),
                    (self._cn("auto"),        self._cc("auto"),
                     [(n,v) for n,v in auto_rows     if v > 0] +
                     fix_split["auto"],                                total_auto),
                    (self._cn("versicherung"), self._cc("versicherung"),
                     [(n,v) for n,v in versich_rows  if v > 0] +
                     fix_split["versicherung"],                        total_versich),
                    *[(self._cn(k), self._cc(k),
                       [(n,v) for n,v in rows if v > 0] + [(n,v) for n,v in fix_split.get(k,[]) if v > 0],
                       sum(v for _,v in rows if v > 0) + sum(v for _,v in fix_split.get(k,[]) if v > 0))
                      for k, rows in custom_rows.items()
                      if any(v > 0 for _, v in rows) or any(v > 0 for _, v in fix_split.get(k, []))],
                ]

                for cat_title, clr, rows, cat_total in legend_cats:
                    if not any(v > 0 for _, v in rows):
                        continue
                    hdr = tk.Frame(self.legend_frame, bg=T["BG_CARD"])
                    hdr.pack(fill="x", padx=(54,8), pady=(6,1))
                    bar = tk.Frame(hdr, bg=clr, width=5)
                    bar.pack(side="left", fill="y", padx=(0,7))
                    bar.pack_propagate(False)
                    tk.Label(hdr, text=f"{cat_title}:",
                             font=("Helvetica Neue", 9, "bold"),
                             bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(side="left", anchor="w")
                    tk.Label(hdr, text=f"{cat_total:,.2f} \u20ac",
                             font=("Helvetica Neue", 9, "bold"),
                             bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(side="right", anchor="e",
                                                                          padx=(0, 40))
                    for name, val in rows:
                        if val <= 0:
                            continue
                        sub = tk.Frame(self.legend_frame, bg=T["BG_CARD"])
                        sub.pack(fill="x", padx=(54,48), pady=0)
                        tk.Label(sub, text=f"    {name}",
                                 font=("Helvetica Neue", 8),
                                 bg=T["BG_CARD"], fg=T["TEXT_MUTED"],
                                 anchor="w").pack(side="left")
                        tk.Label(sub, text=f"{val:,.2f} \u20ac",
                                 font=("Helvetica Neue", 8),
                                 bg=T["BG_CARD"], fg=T["TEXT_MUTED"],
                                 anchor="e").pack(side="right")

                if total_out > 0:
                    tk.Frame(self.legend_frame, bg=T["BORDER_LIGHT"], height=1).pack(
                        fill="x", padx=54, pady=(8,4))
                    tot_row = tk.Frame(self.legend_frame, bg=T["BG_CARD"])
                    tot_row.pack(fill="x", padx=(54,48), pady=(0,4))
                    # Platzhalter statt Farbbalken – gleiche Breite für Ausrichtung
                    tk.Frame(tot_row, bg=T["BG_CARD"], width=12).pack(side="left")
                    tk.Label(tot_row, text="Gesamtausgaben:",
                             font=("Helvetica Neue", 9, "bold"),
                             bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(side="left", anchor="w")
                    tk.Label(tot_row, text=f"{total_out:,.2f} \u20ac",
                             font=("Helvetica Neue", 9, "bold"),
                             bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(side="right", anchor="e")

                if savings > 0 or total_income > 0:
                    tk.Frame(self.legend_frame, bg=T["BORDER_LIGHT"], height=1).pack(
                        fill="x", padx=54, pady=(4,4))
                    sav_row = tk.Frame(self.legend_frame, bg=T["BG_CARD"])
                    sav_row.pack(fill="x", padx=(54,48), pady=(0,6))
                    sav_clr = self._cc("savings") if savings > 0 else DEFICIT_CLR
                    bar2 = tk.Frame(sav_row, bg=sav_clr, width=5)
                    bar2.pack(side="left", fill="y", padx=(0,7))
                    bar2.pack_propagate(False)
                    if savings > 0:
                        tk.Label(sav_row, text=f"{self._cn('savings')}:  {savings:,.2f} \u20ac",
                                 font=("Helvetica Neue", 9, "bold"),
                                 bg=T["BG_CARD"], fg=self._cc("savings")).pack(side="left", anchor="w")
                    elif total_income > 0:
                        deficit = total_out - total_income
                        tk.Label(sav_row, text=f"Defizit:  \u2013{deficit:,.2f} \u20ac",
                                 font=("Helvetica Neue", 9, "bold"),
                                 bg=T["BG_CARD"], fg=DEFICIT_CLR).pack(side="left", anchor="w")

        if savings > 0:
            self.savings_lbl.config(
                text=f"{self._cn('savings')}: {savings:,.2f} \u20ac \u2713", fg=self._cc("savings"))
        elif total_income > 0:
            deficit = total_out - total_income
            self.savings_lbl.config(
                text=f"Defizit: \u2013{deficit:,.2f} \u20ac", fg=DEFICIT_CLR)
        else:
            self.savings_lbl.config(text="Ersparnis: \u2013", fg=T["TEXT_MUTED"])

        # Update savings goal badge
        try:
            _goal_pct = float(self._savings_goal_var.get().replace(",", "."))
        except (ValueError, TypeError):
            _goal_pct = 0.0
        try:
            if _goal_pct > 0 and total_income > 0 and hasattr(self, "_goal_badge_lbl"):
                _goal_amt  = total_income * _goal_pct / 100.0   # target € for input %
                _achieve   = (savings / _goal_amt * 100) if _goal_amt > 0 else 0.0
                _sym = "\u2713" if _achieve >= 100 else "\u2717"
                _clr = self._cc("savings") if _achieve >= 100 else DEFICIT_CLR
                self._goal_badge_lbl.config(
                    text=f"{_goal_amt:,.0f}\u20ac {_sym} {_achieve:.0f}%", fg=_clr)
            elif hasattr(self, "_goal_badge_lbl"):
                self._goal_badge_lbl.config(text="")
        except Exception:
            pass

    # ── Kategorien-Canvas Scroll ──────────────────────────────────────────────
    def _on_cats_configure(self, event=None):
        self._cats_canvas.configure(scrollregion=self._cats_canvas.bbox("all"))
        self._check_cats_scroll()

    def _update_cats_scroll(self, first, last):
        self._cats_vsb.set(first, last)
        self._check_cats_scroll()

    def _check_cats_scroll(self):
        """Scrollbar nur anzeigen wenn Inhalt überläuft."""
        self._cats_scroll_after_id = None
        if getattr(self, '_app_closing', False):
            return
        try:
            inner_h  = self._cats_inner.winfo_reqheight()
            canvas_h = self._cats_canvas.winfo_height()
            if inner_h > canvas_h + 10:
                if not self._cats_vsb.winfo_ismapped():
                    # Pack scrollbar on the right; canvas was already packed on the left.
                    self._cats_vsb.pack(side="right", fill="y")
            else:
                if self._cats_vsb.winfo_ismapped():
                    self._cats_vsb.pack_forget()
        except Exception:
            pass

    # ── Balkendiagramm (tkinter Canvas) ───────────────────────────────────────
    def _on_bar_canvas_resize(self):
        if self.month_chart == "bar" and hasattr(self, "_bar_items_cache"):
            self._draw_tk_bars(self._bar_items_cache)

    def _draw_tk_bars(self, bar_items):
        self._bar_items_cache = bar_items
        T  = self._T()
        c  = self._bar_canvas
        c.delete("all")
        w  = c.winfo_width()
        h  = c.winfo_height()
        if w < 10 or h < 10:
            return
        c.config(bg=T["BG_CARD"])
        if not bar_items:
            c.create_text(w // 2, h // 2, text="Noch keine Daten",
                          fill=T["TEXT_MUTED"], font=("Helvetica Neue", 11))
            return
        pad_l, pad_r, pad_t, pad_b = 118, 14, 18, 18
        n       = len(bar_items)
        area_w  = w - pad_l - pad_r
        area_h  = h - pad_t - pad_b
        slot_h  = area_h / n
        bar_h   = min(slot_h * 0.68, 22)
        max_val = max(item[1] for item in bar_items)
        if max_val == 0:
            return
        bar_area = area_w * 0.68          # 68 % für Balken, Rest für Werttext
        for i, (lbl, val, clr, *_) in enumerate(bar_items):
            yc    = pad_t + slot_h * (i + 0.5)
            bw    = (val / max_val) * bar_area
            # Kategorie-Label
            c.create_text(pad_l - 8, yc, text=lbl,
                          fill=T["TEXT_PRIMARY"], font=("Helvetica Neue", 9),
                          anchor="e")
            # Farbiger Balken
            c.create_rectangle(pad_l, yc - bar_h / 2,
                                pad_l + bw, yc + bar_h / 2,
                                fill=clr, outline="")
            # Wertbeschriftung rechts vom Balken
            c.create_text(pad_l + bw + 8, yc,
                          text=f"{val:,.2f} \u20ac",
                          fill=T["TEXT_PRIMARY"],
                          font=("Helvetica Neue", 8, "bold"),
                          anchor="w")
        # Trennlinie unten
        c.create_line(pad_l, h - pad_b, w - pad_r, h - pad_b,
                      fill=T["BORDER"], width=1)
        # ── Hover-Tooltip (smooth follow, cursor at bottom-left) ──────────
        # Persistent tip window – reuse across hover moves
        if getattr(self, '_bar_tip_win', None) is not None:
            try: self._bar_tip_win.destroy()
            except Exception: pass
        _btw = tk.Toplevel(self); _btw.overrideredirect(True)
        _btw.attributes("-topmost", True); _btw.geometry("+9999+9999")
        try: _btw.wm_attributes("-disabled", True)
        except Exception: pass
        _btw.configure(bg=T["BORDER"])
        _btw_out = tk.Frame(_btw, bg=T["BG_CARD"]); _btw_out.pack(padx=1, pady=1)
        _btw_stripe = tk.Frame(_btw_out, bg=T["BG_CARD"], height=3); _btw_stripe.pack(fill="x")
        _btw_pad = tk.Frame(_btw_out, bg=T["BG_CARD"]); _btw_pad.pack(fill="x", padx=10, pady=(5,6))
        _btw_name = tk.Label(_btw_pad, text="", font=("Helvetica Neue", 9, "bold"),
                             bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]); _btw_name.pack(anchor="w")
        _btw_val  = tk.Label(_btw_pad, text="", font=("Helvetica Neue", 8),
                             bg=T["BG_CARD"], fg=T["TEXT_MUTED"]); _btw_val.pack(anchor="w")
        _btw_avg  = tk.Label(_btw_pad, text="", font=("Helvetica Neue", 8),
                             bg=T["BG_CARD"], fg=T["TEXT_MUTED"]); _btw_avg.pack(anchor="w")
        self._bar_tip_win = _btw
        _bt_last = [-1]; _bt_job = [None]
        # Prozentwert relativ zu Ausgaben + Ersparnis (ohne Einkommen) –
        # konsistent mit Tortendiagramm-Tooltip (Einkommen hat kein Tortenstück).
        _income_clr   = self._cc("income")
        _bt_bar_total = max(sum(item[1] for item in bar_items if item[2] != _income_clr), 1e-9)
        def _bt_cancel():
            if _bt_job[0]: self.after_cancel(_bt_job[0]); _bt_job[0] = None
        def _bt_do_hide():
            try:
                if _btw.winfo_exists():
                    _btw.geometry("+9999+9999")
            except Exception: pass
            _bt_last[0] = -1
        def _bt_hide(e=None):
            _bt_cancel(); _bt_job[0] = self.after(60, _bt_do_hide)
        def _bt_update(lbl, val, avg_val, pct, clr, xr, yr):
            try:
                if not _btw.winfo_exists(): return
                _btw_stripe.configure(bg=clr)
                _btw_name.configure(text=f"{lbl}  {pct:.1f}\u202f%")
                _btw_val.configure(text=f"{val:,.2f}\u00a0\u20ac")
                _btw_avg.configure(text=f"\u00d8 {avg_val:,.2f}\u00a0\u20ac / Monat")
                _btw.geometry(f"+{xr + 14}+{yr - 76}")
            except Exception: pass
        def _bt_motion(e, _items=bar_items[:], _n=n, _sl=slot_h, _pt=pad_t, _pw=w, _tot=_bt_bar_total):
            if e.x < 0 or e.x > _pw:
                _bt_hide(); return
            idx = int((e.y - _pt) / _sl) if _sl > 0 else -1
            if 0 <= idx < _n:
                _bt_cancel(); _bt_last[0] = idx
                _pct = _items[idx][1] / _tot * 100
                _bt_update(_items[idx][0], _items[idx][1], _items[idx][3], _pct, _items[idx][2], e.x_root, e.y_root)
            else:
                _bt_hide()
        c.bind("<Motion>", _bt_motion)
        c.bind("<Leave>", _bt_hide)

    # ── Monatswechsel ─────────────────────────────────────────────────────────
    def _prev_month(self):
        self._save_month()
        self._create_backup("auto")
        m = self.current_month.get() - 1
        if m < 0:
            m = 11; self.current_year.set(self.current_year.get() - 1)
        self.current_month.set(m)
        self.month_lbl.config(text=MONTHS_DE[m])
        self._load_month()

    def _next_month(self):
        self._save_month()
        self._create_backup("auto")
        m = self.current_month.get() + 1
        if m > 11:
            m = 0; self.current_year.set(self.current_year.get() + 1)
        self.current_month.set(m)
        self.month_lbl.config(text=MONTHS_DE[m])
        self._load_month()

    def _on_arrow_nav(self, direction):
        """Pfeiltaste Links/Rechts → Monatsnavigation.
        Wird ignoriert wenn ein Texteingabefeld (Entry/Text) fokussiert ist."""
        w = self.focus_get()
        if isinstance(w, (tk.Entry, tk.Text)):
            return
        if direction == "prev":
            self._prev_month()
        else:
            self._next_month()

    def _month_key(self):
        return f"{self.current_year.get()}-{self.current_month.get()+1:02d}"

    def _year_key(self):
        return f"year_{self.current_year.get()}"

    def _save_fixkosten_now(self):
        """Fixkosten sofort speichern. Bei Änderung gegenüber Snapshot → Dialog (einmalig)."""
        if getattr(self, '_loading_month', False):
            return
        if getattr(self, '_fix_dlg_open', False):
            return
        fix_data = [
            {"title":  r["title"].get(),
             "amount": r["amount"].get(),
             "color":  r["color_var"].get() if r.get("color_var") else FIXKOSTEN_CLR}
            for r in self.fixkosten_card._rows
        ]
        snapshot = getattr(self, '_fixkosten_snapshot', None)
        changed = (
            snapshot is not None and
            fix_data != snapshot
        )
        if changed:
            self._fix_dlg_open = True
            try:
                from_mo = self._ask_fixkosten_from_month(show_current_only=True)
            finally:
                self._fix_dlg_open = False
            current_mo = self.current_month.get() + 1
            if from_mo is None:
                # Abbrechen → UI auf alten Stand zurücksetzen (kein Save)
                self._update_rows_inplace(self.fixkosten_card, snapshot)
            elif from_mo == 0:
                # Nur aktuellen Monat
                key = self._month_key()
                if key not in self.data:
                    self.data[key] = {}
                self.data[key]["fixkosten"] = [dict(r) for r in fix_data]
                self.data[key]["fixkosten_month_only"] = True
                self._fixkosten_snapshot = [dict(r) for r in fix_data]
                save_data(self.data)
            else:
                self._apply_fixkosten_from_month(from_mo, fix_data, snapshot=snapshot)
                if from_mo > current_mo:
                    # Gewählter Monat liegt in der Zukunft → UI auf alten Stand zurücksetzen
                    self._update_rows_inplace(self.fixkosten_card, snapshot)
                    self._fixkosten_snapshot = [dict(r) for r in snapshot]
                    # Aktuellen Monat als month_only markieren: verhindert dass _save_month()
                    # und der else-Branch unten den year_key mit dem zurückgesetzten (alten)
                    # UI-Stand überschreiben und die gespeicherten Zukunfts-Daten zerstören.
                    key = self._month_key()
                    if key not in self.data:
                        self.data[key] = {}
                    if "fixkosten" not in self.data[key]:
                        self.data[key]["fixkosten"] = [dict(r) for r in snapshot]
                    self.data[key]["fixkosten_month_only"] = True
                    # _apply_fixkosten_from_month() hat save_data() bereits aufgerufen
                    # und vergangene unbesuchte Monate mit korrektem alten Stand gesichert.
                else:
                    self._fixkosten_snapshot = [dict(r) for r in fix_data]
            # Diagramm und Tooltips nach Dialog-Interaktion aktualisieren
            self._schedule_refresh()
        else:
            # Keine Änderung gegenüber Snapshot → nur speichern, year_key NICHT verändern.
            # year_key wird ausschließlich durch _apply_fixkosten_from_month() (expliziter Dialog)
            # geschrieben. Jede andere Aktualisierung würde bei Besuchen von Monaten vor
            # fixkosten_from_month die gespeicherten Fixkosten-Daten mit fix_default überschreiben.
            save_data(self.data)

    def _save_fixkosten_silent(self):
        """Fixkosten-Betrag stilles Speichern ohne Dialog.
        Wird ausschliesslich vom Betrag-Eingabefeld aufgerufen – kein Popup,
        kein Propagieren. Snapshot auf aktuellen Stand bringen damit spätere
        dialog-relevante Änderungen (Farbe, Titel, Zeile hinzu/löschen) korrekt
        als Diff erkannt werden."""
        if getattr(self, '_loading_month', False): return
        if getattr(self, '_fix_dlg_open', False): return
        fix_data = [
            {"title":  r["title"].get(),
             "amount": r["amount"].get(),
             "color":  r["color_var"].get() if r.get("color_var") else FIXKOSTEN_CLR}
            for r in self.fixkosten_card._rows
        ]
        self._fixkosten_snapshot = [dict(r) for r in fix_data]
        save_data(self.data)

    def _ask_fixkosten_from_month(self, title=None, question=None, show_current_only=False):
        """Zeigt Dialog: Ab welchem Monat sollen Fixkosten gelten/gelöscht werden?
        Gibt zurück:
          1–12  → ab diesem Monat anwenden
          0     → nur aktuellen Monat (wenn show_current_only=True)
          None  → Abbruch
        """
        T = self._T()
        result = [None]
        current_mo = self.current_month.get() + 1  # 0-based → 1-based

        dlg = tk.Toplevel(self)
        dlg.title(title or "Fixkosten \u2013 G\u00fcltig ab")
        dlg.configure(bg=T["BG_CARD"])
        dlg.resizable(False, False)

        tk.Label(dlg, text=question or "Ab welchem Monat sollen die ge\u00e4nderten Fixkosten gelten?",
                 font=("Helvetica Neue", 11, "bold"),
                 bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"],
                 wraplength=400).pack(padx=24, pady=(20, 4))
        tk.Label(dlg, text="Alle 12 Monate des aktuellen Jahres sind w\u00e4hlbar.",
                 font=("Helvetica Neue", 9),
                 bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(padx=24, pady=(0, 14))

        btn_frame = tk.Frame(dlg, bg=T["BG_CARD"])
        btn_frame.pack(padx=20, pady=(0, 4))

        def _pick(mo):
            result[0] = mo
            dlg.destroy()

        for i, name in enumerate(MONTHS_DE):
            mo = i + 1
            is_current = (mo == current_mo)
            is_past    = (mo < current_mo)
            if is_current:
                bg, fg = INCOME_CLR, "#FFFFFF"
            elif is_past:
                bg, fg = T["BG_HOVER"], T["TEXT_MUTED"]
            else:
                bg, fg = T["BG_INPUT"], T["TEXT_PRIMARY"]
            btn = tk.Button(btn_frame, text=name[:3], width=4,
                            font=("Helvetica Neue", 9),
                            bg=bg, fg=fg, relief="flat", bd=0, padx=6, pady=6,
                            cursor="hand2",
                            command=lambda m=mo: _pick(m))
            btn.grid(row=0, column=i, padx=2, pady=2)

        # Hinweis: vergangene Monate führen zu rückwirkender Anpassung
        tk.Label(dlg, text="Gedimmte Monate liegen in der Vergangenheit – eine Auswahl passt\n"
                            "die Fixkosten für diese Monate rückwirkend an.",
                 font=("Helvetica Neue", 8), justify="left",
                 bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(padx=24, pady=(0, 8))

        bottom = tk.Frame(dlg, bg=T["BG_CARD"])
        bottom.pack(pady=(2, 16))

        if show_current_only:
            tk.Button(bottom, text="Nur aktuellen Monat",
                      font=("Helvetica Neue", 9),
                      bg=T["BG_INPUT"], fg=T["TEXT_PRIMARY"],
                      relief="flat", bd=0, padx=14, pady=5, cursor="hand2",
                      command=lambda: _pick(0)).pack(side="left", padx=(0, 8))

        tk.Button(bottom, text="Abbrechen",
                  font=("Helvetica Neue", 9),
                  bg=T["BG_APP"], fg=T["TEXT_MUTED"],
                  relief="flat", bd=0, padx=14, pady=5, cursor="hand2",
                  command=dlg.destroy).pack(side="left")

        dlg.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width()  - dlg.winfo_width())  // 2
        y = self.winfo_rooty() + (self.winfo_height() - dlg.winfo_height()) // 2
        dlg.geometry(f"+{x}+{y}")
        dlg.lift()
        dlg.focus_force()
        dlg.grab_set()
        self.wait_window(dlg)
        return result[0]

    def _apply_fixkosten_from_month(self, from_mo, fix_data, snapshot=None):
        """Speichert fix_data ab from_mo (1–12) für alle Monate bis Jahresende
        sowie im Jahres-Key (für noch nicht existierende Monate).
        snapshot: Stand vor der Änderung – wird genutzt um nur tatsächlich geänderte
        Felder (Titel/Betrag/Farbe) in bestehende Monats-/Jahresdaten zu übertragen.
        Ohne snapshot: vollständige Überschreibung (altes Verhalten)."""
        yr = self.current_year.get()
        year_key = f"year_{yr}"
        # Alten year_key Stand sichern – für Schutz vergangener unbesuchter Monate
        old_year_fix = [dict(r) for r in self.data.get(year_key, {}).get("fixkosten", [])]
        if year_key not in self.data:
            self.data[year_key] = {}

        def _apply_diff(fix_new, fix_snap, fix_exist):
            """Wendet nur geänderte Felder (new != snap) auf fix_exist an.
            snap_row-Lookup: positionsbasiert (erkennt was der User geändert hat).
            exist_row-Lookup: titelbasiert (findet den richtigen Monatseintrag auch
            wenn Zeilen verschoben wurden, z.B. nach einer Löschung). Verhindert,
            dass Löschungen die Beträge nachfolgender Zeilen in anderen Monaten
            überschreiben."""
            snap_by_pos    = list(fix_snap or [])
            exist_by_title = {r["title"]: r for r in (fix_exist or [])}
            result = []
            for i, new_row in enumerate(fix_new):
                snap_row  = snap_by_pos[i] if i < len(snap_by_pos) else None
                # Titelbasierte Suche: findet Zeile in Zielmonat auch nach Positionsverschiebung
                exist_row = exist_by_title.get(new_row["title"])
                if snap_row is None:
                    # Neu hinzugefügte Zeile (kein Snapshot-Pendant) → direkt übernehmen
                    result.append(dict(new_row))
                else:
                    # Nur geänderte Felder übernehmen, unveränderte aus exist_row lesen
                    title = (new_row["title"]
                             if new_row["title"] != snap_row.get("title", "")
                             else (exist_row.get("title", new_row["title"]) if exist_row else new_row["title"]))
                    amount = (new_row["amount"]
                              if new_row["amount"] != snap_row.get("amount", "")
                              else (exist_row.get("amount", new_row["amount"]) if exist_row else new_row["amount"]))
                    c_new  = new_row.get("color", FIXKOSTEN_CLR)
                    c_snap = snap_row.get("color", FIXKOSTEN_CLR)
                    color  = (c_new
                              if c_new != c_snap
                              else (exist_row.get("color", c_new) if exist_row else c_new))
                    result.append({"title": title, "amount": amount, "color": color})
            return result

        # Year-Key aktualisieren
        self.data[year_key]["fixkosten"] = _apply_diff(fix_data, snapshot, old_year_fix)
        # Gültigkeitsmonat im year_key merken – _load_month() überspringt year_key
        # für Monate vor diesem Schwellwert (verhindert ungewollte Zukunfts-Übernahme).
        self.data[year_key]["fixkosten_from_month"] = from_mo
        # Alle bereits gespeicherten Monate >= from_mo im aktuellen Jahr aktualisieren
        for mo in range(from_mo, 13):
            mk = f"{yr}-{mo:02d}"
            if mk in self.data:
                existing = self.data[mk].get("fixkosten", [])
                self.data[mk]["fixkosten"] = _apply_diff(fix_data, snapshot, existing)
                if fix_data:
                    # Nicht-leere Daten → monatsspezifischen Override aufheben
                    self.data[mk].pop("fixkosten_month_only", None)
                else:
                    # Leere Liste → Flag setzen, sonst würde _load_month auf
                    # Jahres-/Vergangenheitsdaten zurückfallen und die Löschung rückgängig machen
                    self.data[mk]["fixkosten_month_only"] = True
        # Vergangene unbesuchte Monate vor from_mo mit dem korrekten alten Stand sichern –
        # nur wenn old_year_fix Daten enthält. Leere Monate werden über fixkosten_from_month
        # in _load_month() korrekt behandelt (kein year_key-Zugriff, Fallback auf fix_default).
        if old_year_fix:
            for mo in range(1, from_mo):
                mk = f"{yr}-{mo:02d}"
                if mk not in self.data:
                    # Unbesuchter Monat: vollständigen Schutz-Eintrag erstellen
                    self.data[mk] = {
                        "fixkosten": [dict(r) for r in old_year_fix],
                        "fixkosten_month_only": True
                    }
                elif "fixkosten" not in self.data[mk]:
                    # Besuchter Monat ohne eigene Fixkosten: Schutz nachträglich setzen
                    self.data[mk]["fixkosten"] = [dict(r) for r in old_year_fix]
                    self.data[mk]["fixkosten_month_only"] = True
                # Hat Monat bereits eigene fixkosten → kein Eingriff nötig
        # Zukünftige Jahres-Keys übernehmen + bereits besuchte Monate dort aktualisieren
        for yk in list(self.data.keys()):
            if yk.startswith("year_"):
                try:
                    y = int(yk.replace("year_", ""))
                except ValueError:
                    continue
                if y > yr:
                    old_yk_fix = self.data[yk].get("fixkosten", [])
                    new_yk_fix = _apply_diff(fix_data, snapshot, old_yk_fix)
                    self.data[yk]["fixkosten"] = new_yk_fix
                    # Bereits besuchte Monate des Folgejahres ebenfalls aktualisieren.
                    # Nur Monate ohne month_only anfassen – month_only bedeutet: Nutzer hat
                    # für diesen Monat bewusst eine eigene Einstellung gesetzt → nicht überschreiben.
                    # Monate ohne month_only haben ihren Snapshot nur durch Navigation erhalten
                    # und sollen den year_key widerspiegeln.
                    fut_from_mo = self.data[yk].get("fixkosten_from_month", 1)
                    for fut_mo in range(1, 13):
                        fut_mk = f"{y}-{fut_mo:02d}"
                        if fut_mk not in self.data:
                            continue
                        if self.data[fut_mk].get("fixkosten_month_only"):
                            continue  # Explizit vom Nutzer gesetzt → nicht anfassen
                        if fut_mo < fut_from_mo:
                            continue  # Vor dem Gültigkeitsdatum des Folgejahres → nicht anfassen
                        if "fixkosten" in self.data[fut_mk]:
                            # Navigations-Snapshot veraltet → auf aktuellen year_key-Stand bringen
                            self.data[fut_mk]["fixkosten"] = [dict(r) for r in new_yk_fix]
        save_data(self.data)

    def _save_month(self):
        key = self._month_key()
        # Flag retten bevor self.data[key] überschrieben wird
        month_only = self.data.get(key, {}).get("fixkosten_month_only", False)
        base_cats = [
            ("income",       self.income_card),
            ("essenz",       self.essenz_card),
            ("freizeit",     self.freizeit_card),
            ("auto",         self.auto_card),
            ("versicherung", self.versich_card),
        ]
        custom_cats = [(k, self._custom_cards[k])
                       for k in self._custom_cat_order if k in self._custom_cards]
        self.data[key] = {
            cat: [{"title": r["title"].get(), "amount": r["amount"].get()}
                  for r in card._rows]
            for cat, card in base_cats + custom_cats
        }
        year_key = self._year_key()
        if year_key not in self.data:
            self.data[year_key] = {}

        current_fix = [
            {"title":  r["title"].get(),
             "amount": r["amount"].get(),
             "color":  r["color_var"].get() if r.get("color_var") else FIXKOSTEN_CLR}
            for r in self.fixkosten_card._rows
        ]
        # Year-Key wird nur noch via _apply_fixkosten_from_month() (Dialog) aktualisiert,
        # nie durch normale Navigation – verhindert unbeabsichtigtes Überschreiben.
        self.data[key]["fixkosten"] = [dict(r) for r in current_fix]
        if month_only:
            self.data[key]["fixkosten_month_only"] = True  # Flag wiederherstellen

        self.data[key]["notes"] = self.notes_text.get("1.0", "end-1c")
        save_data(self.data)

    def _load_month(self):
        self._loading_month = True
        key        = self._month_key()
        month_data = self.data.get(key, {})
        year_data  = self.data.get(self._year_key(), {})

        defaults = {
            "income":       [{"title": f"Einkommen {i+1}",    "amount": ""} for i in range(3)],
            "essenz":       [{"title": f"Ausgaben {i+1}",     "amount": ""} for i in range(4)],
            "freizeit":     [{"title": f"Ausgaben {i+1}",     "amount": ""} for i in range(4)],
            "auto":         [{"title": f"Auto {i+1}",         "amount": ""} for i in range(2)],
            "versicherung": [{"title": f"Versicherung {i+1}", "amount": ""} for i in range(2)],
        }
        fix_default = [{"title": f"Fixkosten {i+1}", "amount": "",
                        "color": FIXKOSTEN_CLR} for i in range(2)]

        # Vergangene Monatskeysliste (chronologisch absteigend, nur < aktueller Monat)
        # wird für alle Kategorien genutzt um Zeilennamen rückwärts zu erben.
        past_month_keys = sorted(
            [k for k in self.data if not k.startswith("year_") and k < key],
            reverse=True
        )

        def _inherit_titles(cat, fallback_rows):
            """Gibt Zeilen zurück: gespeichert wenn vorhanden, sonst Titel vom
            letzten Monat mit Daten (Beträge leer) – nie rückwirkend."""
            if cat in month_data:
                return month_data[cat]
            for pk in past_month_keys:
                prev = self.data[pk].get(cat)
                if prev:
                    return [{"title": r["title"], "amount": ""} for r in prev]
            return fallback_rows

        for cat, card in [
            ("income",       self.income_card),
            ("essenz",       self.essenz_card),
            ("freizeit",     self.freizeit_card),
            ("auto",         self.auto_card),
            ("versicherung", self.versich_card),
        ]:
            self._update_rows_inplace(card, _inherit_titles(cat, defaults[cat]))

        def _is_default_fix(fix_list):
            """True wenn die Liste leer ist oder nur unveränderte Auto-Platzhalter enthält.
            Eine Zeile mit angepasster Farbe gilt als nicht-default, auch wenn Titel und
            Betrag noch auf den Vorgabewerten stehen."""
            if not fix_list:
                return True
            return all(
                re.match(r'^Fixkosten \d+$', r.get("title", "")) and
                r.get("amount", "") == "" and
                r.get("color", FIXKOSTEN_CLR) == FIXKOSTEN_CLR
                for r in fix_list
            )

        # Per-Monat-Snapshot hat Vorrang (schützt vergangene Monate vor Jahres-Änderungen)
        month_fix = month_data.get("fixkosten")
        month_only = month_data.get("fixkosten_month_only", False)
        # month_only=True: Nutzer hat "nur aktuellen Monat" gewählt → month_fix gilt auch
        # wenn leer (z.B. alle Zeilen gelöscht). Sonst: nur nutzen wenn nicht-leer und nicht default.
        if (month_only and "fixkosten" in month_data) or (month_fix and not _is_default_fix(month_fix)):
            raw_fix = [dict(r) for r in (month_fix or [])]
            for r in raw_fix:
                if "color" not in r:
                    r["color"] = FIXKOSTEN_CLR
        else:
            # year_key nur nutzen wenn dieser Monat innerhalb des Gültigkeitsbereichs liegt
            year_from_mo = year_data.get("fixkosten_from_month", 1)
            current_mo = self.current_month.get() + 1
            if current_mo < year_from_mo:
                raw_fix = None  # Monat liegt vor dem gesetzten Gültigkeitsdatum → fix_default
            else:
                raw_fix = year_data.get("fixkosten", None)
            if raw_fix is None or _is_default_fix(raw_fix):
                # Effektiven Fixkosten-Stand aus dem Vorjahr ermitteln –
                # repliziert exakt die _load_month()-Logik für vergangene Monate:
                # month_only-Einträge haben Vorrang, dann year_key wenn Monat
                # innerhalb des Gültigkeitsbereichs liegt.
                # Sucht rückwärts durch alle Vorjahre bis ein echter Stand gefunden wird.
                current_yr = self.current_year.get()
                all_prev_yrs = sorted(
                    {int(k.replace("year_", "")) for k in self.data if k.startswith("year_")}
                    | {int(k.split("-")[0]) for k in self.data if not k.startswith("year_")},
                    reverse=True
                )
                for prev_yr in all_prev_yrs:
                    if prev_yr >= current_yr:
                        continue
                    prev_yd       = self.data.get(f"year_{prev_yr}", {})
                    prev_year_fix = prev_yd.get("fixkosten")
                    prev_from_mo  = prev_yd.get("fixkosten_from_month", 1)
                    effective_fix = None
                    for mo in range(12, 0, -1):
                        mk_prev = f"{prev_yr}-{mo:02d}"
                        md_prev = self.data.get(mk_prev, {})
                        m_fix   = md_prev.get("fixkosten")
                        m_only  = md_prev.get("fixkosten_month_only", False)
                        # Monat hat eigene Fixkosten (month_only oder non-default)?
                        if ((m_only and "fixkosten" in md_prev)
                                or (m_fix and not _is_default_fix(m_fix))):
                            effective_fix = m_fix or []
                            break
                        # Monat liegt im Gültigkeitsbereich des year_key?
                        if (mo >= prev_from_mo
                                and prev_year_fix
                                and not _is_default_fix(prev_year_fix)):
                            effective_fix = prev_year_fix
                            break
                        # Vor dem Gültigkeitsdatum → nächstfrüheren Monat prüfen
                    # Falls kein Monat besucht: year_key direkt nutzen
                    if effective_fix is None and prev_year_fix and not _is_default_fix(prev_year_fix):
                        effective_fix = prev_year_fix
                    if effective_fix:
                        raw_fix = [dict(r) for r in effective_fix]
                        cur_year_key = self._year_key()
                        yk_has_fix = bool(
                            self.data.get(cur_year_key, {}).get("fixkosten"))
                        if not yk_has_fix:
                            # year_key fehlt oder hat noch keine Fixkosten:
                            # Dezember-Stand als neuen Jahres-Standard anlegen,
                            # ab Januar gültig (fixkosten_from_month=1).
                            if cur_year_key not in self.data:
                                self.data[cur_year_key] = {}
                            self.data[cur_year_key]["fixkosten"] = raw_fix
                            self.data[cur_year_key]["fixkosten_from_month"] = 1
                        else:
                            # year_key hat bereits eigene Fixkosten (User hat im
                            # neuen Jahr schon etwas eingestellt, z.B. "ab März").
                            # year_key unberührt lassen – nur diesen Monat direkt
                            # mit Dezember-Stand sichern (month_only).
                            if key not in self.data:
                                self.data[key] = {}
                            self.data[key].setdefault("fixkosten", raw_fix)
                            self.data[key]["fixkosten_month_only"] = True
                        save_data(self.data)
                        break
            if not raw_fix:
                raw_fix = fix_default
            for r in raw_fix:
                if "color" not in r:
                    r["color"] = FIXKOSTEN_CLR
            # Sofort als Monats-Snapshot sichern → schützt diesen Monat vor
            # späteren Jahres-Änderungen in anderen Monaten
            if any(r.get("amount", "").strip() for r in raw_fix):
                if key not in self.data:
                    self.data[key] = {}
                self.data[key].setdefault("fixkosten", [dict(r) for r in raw_fix])
        self._update_rows_inplace(self.fixkosten_card, raw_fix)
        self._fixkosten_snapshot = [dict(r) for r in raw_fix]

        # Benutzerdefinierte Kategorien laden
        for ck in self._custom_cat_order:
            if ck in self._custom_cards:
                default_rows = [{"title": f"{self._cn(ck)} {i+1}", "amount": ""} for i in range(2)]
                self._update_rows_inplace(self._custom_cards[ck],
                                          _inherit_titles(ck, default_rows))

        # Notizen laden + Datum aktualisieren
        self._notes_date_var.set(
            f"{MONTHS_DE[self.current_month.get()]} {self.current_year.get()}")
        notes = month_data.get("notes", "")
        self.notes_text.delete("1.0", "end")
        if notes:
            self.notes_text.insert("1.0", notes)

        self._loading_month = False
        self._do_refresh()
        # Tkinter-Layout sofort erzwingen (wichtig nach Undo/Redo im Canvas-Window)
        try:
            self.update_idletasks()
        except Exception:
            pass

    # ── Kalender ──────────────────────────────────────────────────────────────
    def _on_month_lbl_enter(self):
        """Maus betritt den Monats-Label → Kalender öffnen."""
        # Laufende Schließ-Überwachung canceln
        if self._hover_watch_id:
            try:
                self.after_cancel(self._hover_watch_id)
            except Exception:
                pass
            self._hover_watch_id = None
        if not (self._cal_dropdown and self._cal_dropdown.winfo_exists()):
            self._open_calendar()

    def _on_month_lbl_leave(self):
        """Maus verlässt den Monats-Label → Schließ-Überwachung starten."""
        self._start_hover_watch()

    def _start_hover_watch(self):
        """Startet einen Polling-Timer, der Kalender schließt wenn Maus weder
        über dem Monats-Label noch über dem Kalender-Dropdown steht."""
        if self._hover_watch_id:
            try:
                self.after_cancel(self._hover_watch_id)
            except Exception:
                pass
        self._hover_watch_id = self.after(120, self._hover_watch_tick)

    def _hover_watch_tick(self):
        self._hover_watch_id = None
        if not (self._cal_dropdown and self._cal_dropdown.winfo_exists()):
            return
        try:
            mx, my = self.winfo_pointerxy()
            # Über dem Monats-Label?
            try:
                lx = self.month_lbl.winfo_rootx()
                ly = self.month_lbl.winfo_rooty()
                lw = self.month_lbl.winfo_width()
                lh = self.month_lbl.winfo_height()
                if lx <= mx <= lx + lw and ly <= my <= ly + lh:
                    self._hover_watch_id = self.after(120, self._hover_watch_tick)
                    return
            except Exception:
                pass
            # Über dem Kalender-Dropdown?
            try:
                wx = self._cal_dropdown.winfo_rootx()
                wy = self._cal_dropdown.winfo_rooty()
                ww = self._cal_dropdown.winfo_width()
                wh = self._cal_dropdown.winfo_height()
                if wx <= mx <= wx + ww and wy <= my <= wy + wh:
                    self._hover_watch_id = self.after(120, self._hover_watch_tick)
                    return
            except Exception:
                pass
            # Weder noch → Kalender schließen
            self._close_calendar()
        except Exception:
            pass

    def _close_calendar(self):
        # Hover-Watch stoppen
        if self._hover_watch_id:
            try:
                self.after_cancel(self._hover_watch_id)
            except Exception:
                pass
            self._hover_watch_id = None
        if self._cal_dropdown:
            try:
                self._cal_dropdown.destroy()
            except Exception:
                pass
        self._cal_dropdown = None

    def _open_calendar(self):
        T = self._T()
        self._close_calendar()
        self.update_idletasks()
        bx = self.month_lbl.winfo_rootx()
        by = self.month_lbl.winfo_rooty() + self.month_lbl.winfo_height() + 4
        drop = tk.Toplevel(self)
        drop.overrideredirect(True)
        drop.geometry(f"+{bx}+{by}")
        drop.configure(bg=T["BG_CARD"])
        drop.attributes("-topmost", True)
        outer = tk.Frame(drop, bg=T["BORDER"], padx=1, pady=1)
        outer.pack(fill="both", expand=True)
        inner = tk.Frame(outer, bg=T["BG_CARD"])
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        self._cal_dropdown = drop

        cal_year = tk.IntVar(value=self.current_year.get())
        year_row = tk.Frame(inner, bg=T["BG_CARD"])
        year_row.pack(fill="x", padx=18, pady=(16,10))
        tk.Label(year_row, text="Jahr",
                 font=("Helvetica Neue", 13, "bold"),
                 bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(side="left")
        tk.Button(year_row, text="\u25ba",
                  font=("Helvetica Neue", 13, "bold"),
                  bg=T["BG_CARD"], fg=T["TEXT_MUTED"], bd=0, cursor="hand2",
                  activebackground=T["BG_HOVER"], activeforeground=T["TEXT_PRIMARY"],
                  command=lambda: cal_year.set(cal_year.get()+1)
                  ).pack(side="right", padx=(4,0))
        tk.Label(year_row, textvariable=cal_year,
                 font=("Helvetica Neue", 20, "bold"),
                 bg=T["BG_CARD"], fg=INCOME_CLR, width=5).pack(side="right")
        tk.Button(year_row, text="\u25c4",
                  font=("Helvetica Neue", 13, "bold"),
                  bg=T["BG_CARD"], fg=T["TEXT_MUTED"], bd=0, cursor="hand2",
                  activebackground=T["BG_HOVER"], activeforeground=T["TEXT_PRIMARY"],
                  command=lambda: cal_year.set(cal_year.get()-1)
                  ).pack(side="right", padx=(0,4))
        tk.Frame(inner, bg=T["BORDER_LIGHT"], height=1).pack(fill="x", padx=14, pady=(0,10))

        mf = tk.Frame(inner, bg=T["BG_CARD"])
        mf.pack(padx=16, pady=(0,16))

        def _month_net(yr, m):
            """Gibt den Netto-Wert (Einnahmen minus alle Ausgaben inkl. anteilige Fixkosten)
            für Monat m (1-basiert) zurück. None wenn keine Benutzerdaten vorhanden
            (leerer Monat oder reiner Fixkosten-Snapshot ohne eingetragene Werte)."""
            k  = f"{yr}-{m:02d}"
            md = self.data.get(k)
            if md is None:
                return None
            inc = sum(self._parse_amount(r["amount"]) for r in md.get("income",      []))
            ess = sum(self._parse_amount(r["amount"]) for r in md.get("essenz",       []))
            fre = sum(self._parse_amount(r["amount"]) for r in md.get("freizeit",     []))
            aut = sum(self._parse_amount(r["amount"]) for r in md.get("auto",         []))
            ver = sum(self._parse_amount(r["amount"]) for r in md.get("versicherung", []))
            cus = sum(
                sum(self._parse_amount(r["amount"]) for r in md.get(ck, []))
                for ck in self._custom_cat_order
            )
            # Keinen Rahmen wenn keine Benutzerdaten vorhanden (nur Fixkosten-Snapshot)
            if inc == 0 and (ess + fre + aut + ver + cus) == 0:
                return None
            # Anteilige Fixkosten einrechnen (Jahresbetrag ÷ 12) –
            # nur wenn tatsächlich Benutzerdaten vorhanden, damit leere Monate
            # mit Fixkosten-Snapshot nicht fälschlich als "eingetragen" erscheinen.
            yd       = self.data.get(f"year_{yr}", {})
            from_mo  = yd.get("fixkosten_from_month", 1)
            if md.get("fixkosten_month_only") or "fixkosten" in md:
                fix_rows = md.get("fixkosten", [])
            elif m < from_mo:
                fix_rows = []
            else:
                fix_rows = yd.get("fixkosten", [])
            fix = sum(self._parse_amount(fr.get("amount", "")) / 12.0 for fr in fix_rows)
            return inc - ess - fre - aut - ver - cus - fix

        def _rebuild_months(yr):
            for w in mf.winfo_children():
                w.destroy()
            for i, name in enumerate(MONTHS_DE):
                col, row_i = i % 3, i // 3
                is_cur = (i == self.current_month.get() and yr == self.current_year.get())
                net    = _month_net(yr, i + 1)
                if net is not None and not is_cur:
                    border_clr = "#10B981" if net >= 0 else "#EF4444"
                    bpx = 2
                else:
                    border_clr = T["BG_CARD"]
                    bpx = 0
                wrap = tk.Frame(mf, bg=border_clr, padx=bpx, pady=bpx)
                wrap.grid(row=row_i, column=col, padx=5, pady=5)
                btn = tk.Button(wrap, text=name,
                                font=("Helvetica Neue", 12, "bold"),
                                width=9, height=2, bd=0, cursor="hand2", relief="flat",
                                bg=INCOME_CLR if is_cur else T["BG_INPUT"],
                                fg="#FFFFFF"  if is_cur else T["TEXT_LABEL"],
                                activebackground=INCOME_CLR, activeforeground="#FFFFFF")
                def pick(m=i):
                    self._save_month()
                    self.current_year.set(cal_year.get())
                    self.current_month.set(m)
                    self.month_lbl.config(text=MONTHS_DE[m])
                    self._load_month()
                    self._close_calendar()
                btn.config(command=pick)
                btn.pack(fill="both", expand=True)

        _rebuild_months(cal_year.get())

        def _on_year_change(*_):
            _rebuild_months(cal_year.get())
        cal_year.trace_add("write", _on_year_change)

        drop.protocol("WM_DELETE_WINDOW", self._close_calendar)
        # Hover-Watch starten – schließt Kalender wenn Maus beide Bereiche verlässt
        self._start_hover_watch()

    # ── Eintragssuche ─────────────────────────────────────────────────────────
    def _open_search(self):
        """Öffnet ein Suchfenster, das alle Monate nach Titel oder Betrag durchsucht."""
        import tkinter.ttk as ttk
        T = self._T()

        # Nur einmal öffnen
        if hasattr(self, '_search_win') and self._search_win and self._search_win.winfo_exists():
            self._search_win.lift()
            self._search_win.focus_set()
            return

        pop = tk.Toplevel(self)
        self._search_win = pop
        pop.title("Eintragssuche")
        try:
            pop.geometry(self._search_geometry or "720x480")
        except Exception:
            self._search_geometry = None
            pop.geometry("720x480")
        pop.configure(bg=T["BG_CARD"])
        pop.resizable(True, True)

        def _track_search_geometry(e=None):
            if e is not None and e.widget is not pop:
                return
            try:
                geom = pop.geometry()
                if geom and "x" in geom:
                    w = int(geom.split("x")[0])
                    h = int(geom.split("x")[1].split("+")[0].split("-")[0])
                    if w >= 400 and h >= 300:
                        self._search_geometry = geom
            except Exception:
                pass
        pop.after(500, lambda: pop.bind("<Configure>", _track_search_geometry))

        # ── Header ────────────────────────────────────────────────────────────
        hdr = tk.Frame(pop, bg=T["BG_CARD"])
        hdr.pack(fill="x", padx=16, pady=(14, 6))
        tk.Label(hdr, text="\U0001F50E  Eintragssuche",
                 font=("Helvetica Neue", 14, "bold"),
                 bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(side="left")
        tk.Label(hdr, text="Ctrl+F",
                 font=("Helvetica Neue", 9),
                 bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(side="right", pady=4)

        # ── Suchzeile ─────────────────────────────────────────────────────────
        sf = tk.Frame(pop, bg=T["BG_CARD"])
        sf.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(sf, text="Suche:",
                 font=("Helvetica Neue", 10),
                 bg=T["BG_CARD"], fg=T["TEXT_LABEL"]).pack(side="left", padx=(0, 8))
        search_var = tk.StringVar()
        search_entry = tk.Entry(sf, textvariable=search_var,
                                font=("Helvetica Neue", 11),
                                bg=T["BG_INPUT"], fg=T["TEXT_PRIMARY"],
                                insertbackground=T["TEXT_PRIMARY"],
                                relief="flat", bd=0,
                                highlightthickness=1, highlightbackground=T["BORDER"])
        search_entry.pack(side="left", fill="x", expand=True, ipady=3)
        tk.Label(sf, text="(Name oder Betrag)",
                 font=("Helvetica Neue", 9),
                 bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(side="left", padx=(8, 0))

        # ── Filteroptionen (Toggle-Buttons) ────────────────────────────────────
        exact_var      = tk.BooleanVar(value=getattr(self, "_search_exact_amount", False))
        hide_empty_var = tk.BooleanVar(value=getattr(self, "_search_hide_empty",   False))

        def _make_toggle(parent, text, var):
            """Flacher Toggle-Button im App-Stil."""
            btn = tk.Button(parent, text=text,
                            font=("Helvetica Neue", 9),
                            bg=INCOME_CLR if var.get() else T["BG_INPUT"],
                            fg="#FFFFFF"   if var.get() else T["TEXT_MUTED"],
                            relief="flat", bd=0, cursor="hand2", padx=10, pady=4,
                            activebackground=INCOME_CLR, activeforeground="#FFFFFF")
            def _toggle(b=btn, v=var):
                v.set(not v.get())
                b.config(bg=INCOME_CLR if v.get() else T["BG_INPUT"],
                         fg="#FFFFFF"   if v.get() else T["TEXT_MUTED"])
                _do_search()
            btn.config(command=_toggle)
            return btn

        cb_frame = tk.Frame(pop, bg=T["BG_CARD"])
        cb_frame.pack(fill="x", padx=16, pady=(0, 6))
        _make_toggle(cb_frame, "Genauer Betrag",        exact_var).pack(side="left", padx=(0, 8))
        _make_toggle(cb_frame, "Leere Betr\u00e4ge ausblenden", hide_empty_var).pack(side="left")

        # ── Betragsbereich-Filter ──────────────────────────────────────────────
        range_frame = tk.Frame(pop, bg=T["BG_CARD"])
        range_frame.pack(fill="x", padx=16, pady=(0, 6))
        tk.Label(range_frame, text="Betrag von:",
                 font=("Helvetica Neue", 9),
                 bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(side="left", padx=(0, 5))
        amount_from_var = tk.StringVar()
        tk.Entry(range_frame, textvariable=amount_from_var,
                 width=9, font=("Helvetica Neue", 10),
                 bg=T["BG_INPUT"], fg=T["TEXT_PRIMARY"],
                 insertbackground=T["TEXT_PRIMARY"],
                 relief="flat", bd=0,
                 highlightthickness=1, highlightbackground=T["BORDER"]
                 ).pack(side="left", ipady=2)
        tk.Label(range_frame, text=" \u20ac   bis:",
                 font=("Helvetica Neue", 9),
                 bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(side="left", padx=(4, 5))
        amount_to_var = tk.StringVar()
        tk.Entry(range_frame, textvariable=amount_to_var,
                 width=9, font=("Helvetica Neue", 10),
                 bg=T["BG_INPUT"], fg=T["TEXT_PRIMARY"],
                 insertbackground=T["TEXT_PRIMARY"],
                 relief="flat", bd=0,
                 highlightthickness=1, highlightbackground=T["BORDER"]
                 ).pack(side="left", ipady=2)
        tk.Label(range_frame, text=" \u20ac",
                 font=("Helvetica Neue", 9),
                 bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(side="left")
        tk.Label(range_frame, text="   (leer = kein Filter)",
                 font=("Helvetica Neue", 8, "italic"),
                 bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(side="left", padx=(6, 0))

        # ── Jahresfilter ───────────────────────────────────────────────────────
        year_filter_var = [None]   # None = alle Jahre
        _non_fix_cats = (["income", "essenz", "freizeit", "auto", "versicherung"]
                         + self._custom_cat_order)

        def _year_has_input(yr_str):
            """True wenn das Jahr mindestens einen Nicht-Fixkosten-Eintrag mit Betrag hat."""
            for mk, md in self.data.items():
                if mk.startswith("year_") or not mk.startswith(yr_str + "-"):
                    continue
                for cat in _non_fix_cats:
                    if any(str(r.get("amount", "")).strip() for r in md.get(cat, [])):
                        return True
            return False

        all_years_avail = sorted(set(
            k.split("-")[0] for k in self.data
            if not k.startswith("year_") and "-" in k
               and _year_has_input(k.split("-")[0])
        ))
        yf_btns = {}

        def _update_yf_styles():
            for _k, _b in yf_btns.items():
                _active = (year_filter_var[0] == (None if _k == "all" else _k))
                _b.config(bg=INCOME_CLR if _active else T["BG_INPUT"],
                          fg="#FFFFFF"   if _active else T["TEXT_MUTED"])

        def _set_year_filter(yr):
            year_filter_var[0] = yr
            _update_yf_styles()
            _do_search()

        yf_frame = tk.Frame(pop, bg=T["BG_CARD"])
        yf_frame.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(yf_frame, text="Zeitraum:",
                 font=("Helvetica Neue", 9),
                 bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(side="left", padx=(0, 8))

        def _make_yf_btn(lbl, yr):
            _act = (year_filter_var[0] == yr)
            b = tk.Button(yf_frame, text=lbl,
                          font=("Helvetica Neue", 9),
                          bg=INCOME_CLR if _act else T["BG_INPUT"],
                          fg="#FFFFFF"   if _act else T["TEXT_MUTED"],
                          relief="flat", bd=0, cursor="hand2", padx=10, pady=4,
                          activebackground=INCOME_CLR, activeforeground="#FFFFFF",
                          command=lambda y=yr: _set_year_filter(y))
            return b

        yf_btns["all"] = _make_yf_btn("Alle", None)
        yf_btns["all"].pack(side="left", padx=(0, 6))
        for _yr in all_years_avail:
            yf_btns[_yr] = _make_yf_btn(_yr, _yr)
            yf_btns[_yr].pack(side="left", padx=(0, 4))

        tk.Frame(pop, bg=T["BORDER"], height=1).pack(fill="x", padx=12)

        # ── Trefferliste (Treeview + tk.Scrollbar im Stil des Hauptfensters) ──
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Search.Treeview",
                        background=T["BG_CARD"],
                        fieldbackground=T["BG_CARD"],
                        foreground=T["TEXT_PRIMARY"],
                        rowheight=26,
                        borderwidth=0)
        style.configure("Search.Treeview.Heading",
                        background=T["BG_INPUT"],
                        foreground=T["TEXT_LABEL"],
                        font=("Helvetica Neue", 9, "bold"),
                        relief="flat")
        style.map("Search.Treeview",
                  background=[("selected", INCOME_CLR)],
                  foreground=[("selected", "#FFFFFF")])

        cols = ("monat", "kategorie", "name", "betrag")
        tree_frame = tk.Frame(pop, bg=T["BG_CARD"])
        tree_frame.pack(fill="both", expand=True, padx=12, pady=(8, 4))

        tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                            style="Search.Treeview")
        tree.heading("monat",     text="Monat",        anchor="w")
        tree.heading("kategorie", text="Kategorie",    anchor="w")
        tree.heading("name",      text="Name / Titel", anchor="w")
        tree.heading("betrag",    text="Betrag",       anchor="e")
        tree.column("monat",     width=110, anchor="w", stretch=False)
        tree.column("kategorie", width=120, anchor="w", stretch=False)
        tree.column("name",      width=280, anchor="w", stretch=True)
        tree.column("betrag",    width=100, anchor="e", stretch=False)

        # tk.Scrollbar – gleicher Stil wie im Hauptfenster (_cats_vsb)
        vsb = tk.Scrollbar(tree_frame, orient="vertical",
                           command=tree.yview, bg=T["BG_APP"])
        tree.configure(yscrollcommand=vsb.set)
        tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        # ── Status + Summe (eine Zeile, Summe rechts unter "Betrag") ──────────
        bot_row = tk.Frame(pop, bg=T["BG_CARD"])
        bot_row.pack(fill="x", padx=12, pady=(4, 0))
        status_var = tk.StringVar(value="Suchbegriff eingeben \u2026")
        tk.Label(bot_row, textvariable=status_var,
                 font=("Helvetica Neue", 9),
                 bg=T["BG_CARD"], fg=T["TEXT_MUTED"], anchor="w").pack(
                     side="left", fill="x", expand=True)
        sum_var = tk.StringVar(value="")
        tk.Label(bot_row, textvariable=sum_var,
                 font=("Helvetica Neue", 9, "bold"),
                 bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"], anchor="e").pack(
                     side="right", padx=(0, 18))

        tk.Frame(pop, bg=T["BORDER_LIGHT"], height=1).pack(fill="x", padx=12, pady=(4, 0))
        tk.Button(pop, text="Schliessen",
                  font=("Helvetica Neue", 9),
                  bg=T["BG_INPUT"], fg=T["TEXT_LABEL"],
                  relief="flat", bd=0, cursor="hand2", padx=14, pady=4,
                  command=pop.destroy).pack(anchor="e", padx=16, pady=(6, 10))

        # ── Mausrad nur im Suchfenster scrollen ───────────────────────────────
        def _search_scroll(e):
            try:
                tree.yview_scroll(int(-1 * (e.delta / 120)), "units")
            except Exception:
                pass
        self.bind_all("<MouseWheel>", _search_scroll)

        def _restore_mwheel(e=None):
            if e is not None and e.widget is not pop:
                return
            # Checkbox-Zustände speichern
            try:
                self._search_exact_amount = exact_var.get()
                self._search_hide_empty   = hide_empty_var.get()
                s = load_settings()
                s["search_exact_amount"] = self._search_exact_amount
                s["search_hide_empty"]   = self._search_hide_empty
                save_settings(s)
            except Exception:
                pass
            try:
                if hasattr(self, "_global_mousewheel_fn"):
                    self.bind_all("<MouseWheel>", self._global_mousewheel_fn)
            except Exception:
                pass
        pop.bind("<Destroy>", _restore_mwheel)

        # ── Kategorienamen für die Anzeige ────────────────────────────────────
        def _cat_display_name(cat_key):
            cs = self._cat_settings
            if cat_key in cs:
                return cs[cat_key].get("name", cat_key.capitalize())
            return cat_key.capitalize()

        # ── Alle Kategorien (inkl. Custom) ────────────────────────────────────
        ALL_CATS = ["income", "essenz", "freizeit", "auto", "versicherung"] + self._custom_cat_order

        # Metadata pro Treeview-Eintrag: item_id → (month_key, cat_key, row_idx)
        tree_meta = {}

        def _do_search(*_):
            term = search_var.get().strip().lower()
            for iid in tree.get_children():
                tree.delete(iid)
            tree_meta.clear()

            exact_amount = exact_var.get()
            hide_empty   = hide_empty_var.get()

            # Betragsbereich parsen (leer = kein Filter)
            range_from = None
            range_to   = None
            try:
                _rf = amount_from_var.get().strip().replace(",", ".")
                if _rf:
                    range_from = float(_rf)
            except (ValueError, TypeError):
                pass
            try:
                _rt = amount_to_var.get().strip().replace(",", ".")
                if _rt:
                    range_to = float(_rt)
            except (ValueError, TypeError):
                pass
            has_range = range_from is not None or range_to is not None

            if not term and not has_range:
                status_var.set("Suchbegriff eingeben \u2026")
                sum_var.set("")
                return

            # Suchbegriff als Zahl parsen (für genauen Betragsvergleich)
            term_num = None
            try:
                term_num = float(term.replace(",", "."))
            except (ValueError, TypeError):
                pass

            # Aktuellen Monat speichern damit Namensänderungen sofort erfasst werden
            try:
                self._save_month()
            except Exception:
                pass

            hits = []
            for month_key in sorted(self.data.keys()):
                if month_key.startswith("year_"):
                    continue
                if year_filter_var[0] is not None and not month_key.startswith(year_filter_var[0]):
                    continue
                try:
                    yr, mo = month_key.split("-")
                    mo_name = f"{MONTHS_DE[int(mo)-1]} {yr}"
                except Exception:
                    mo_name = month_key

                md = self.data[month_key]
                for cat_key in ALL_CATS:
                    for row_idx, rec in enumerate(md.get(cat_key, [])):
                        title  = str(rec.get("title",  "")).strip()
                        amount = str(rec.get("amount", "")).strip()

                        # Textfilter (nur wenn Suchbegriff vorhanden)
                        if term:
                            title_match = term in title.lower()
                            if exact_amount and term_num is not None:
                                try:
                                    amt_f_chk = self._parse_amount(amount)
                                    amount_match = abs(amt_f_chk - term_num) < 0.005
                                except Exception:
                                    amount_match = False
                            else:
                                amount_match = term in amount.lower()
                            if not (title_match or amount_match):
                                continue

                        # Filter: Einträge ohne Betrag ausblenden
                        amt_f = self._parse_amount(amount)

                        # Betragsbereich-Filter
                        if range_from is not None and amt_f < range_from:
                            continue
                        if range_to is not None and amt_f > range_to:
                            continue
                        if hide_empty and (not amount.strip() or amt_f == 0.0):
                            continue

                        amt_str = (f"{amt_f:,.2f}\u00a0\u20ac"
                                   .replace(",", "X").replace(".", ",").replace("X", "."))
                        hits.append((mo_name, _cat_display_name(cat_key),
                                     title, amt_str, month_key, cat_key, row_idx, amt_f))

            for mo_name, cat_name, title, amt_str, mk, ck, ri, _amt in hits:
                iid = tree.insert("", "end", values=(mo_name, cat_name, title, amt_str))
                tree_meta[iid] = (mk, ck, ri)

            count = len(hits)
            if count == 0:
                _hint = search_var.get().strip()
                if has_range and not _hint:
                    _from = f"{range_from:,.0f}".replace(",",".")+" €" if range_from is not None else "–"
                    _to   = f"{range_to:,.0f}".replace(",",".")+" €" if range_to is not None else "–"
                    status_var.set(f"Keine Treffer im Bereich {_from} bis {_to}")
                else:
                    status_var.set(f'Keine Treffer f\u00fcr "{_hint}"')
                sum_var.set("")
            else:
                status_var.set(f"{count} Treffer gefunden  \u2014  Doppelklick zum \u00d6ffnen")
                total = sum(h[7] for h in hits)
                total_str = (f"{total:,.2f}\u00a0\u20ac"
                             .replace(",", "X").replace(".", ",").replace("X", "."))
                sum_var.set(f"Summe: {total_str}")

        # ── Doppelklick → Monat öffnen & Betrag-Feld fokussieren ──────────────
        def _on_doubleclick(event):
            sel = tree.selection()
            if not sel:
                return
            meta = tree_meta.get(sel[0])
            if not meta:
                return
            mk, ck, ri = meta
            try:
                yr_s, mo_s = mk.split("-")
                yr, mo = int(yr_s), int(mo_s)
            except Exception:
                return

            # Monat laden
            self._save_month()
            self.current_year.set(yr)
            self.current_month.set(mo - 1)
            self.month_lbl.config(text=MONTHS_DE[mo - 1])
            self._load_month()

            # Karte für die Kategorie ermitteln
            card_map = {
                "income":       getattr(self, "income_card",  None),
                "essenz":       getattr(self, "essenz_card",  None),
                "freizeit":     getattr(self, "freizeit_card", None),
                "auto":         getattr(self, "auto_card",    None),
                "versicherung": getattr(self, "versich_card", None),
            }
            for k in self._custom_cat_order:
                card_map[k] = self._custom_cards.get(k)

            def _focus_entry():
                try:
                    card = card_map.get(ck)
                    if card and ri < len(card._rows):
                        ae = card._rows[ri].get("amt_entry")
                        if ae and ae.winfo_exists():
                            ae.focus_set()
                            if ae.get():
                                ae.select_range(0, "end")
                    pop.lift()
                except Exception:
                    pass
            self.after(60, _focus_entry)

        tree.bind("<Double-Button-1>", _on_doubleclick)
        search_var.trace_add("write", _do_search)
        amount_from_var.trace_add("write", _do_search)
        amount_to_var.trace_add("write",   _do_search)
        pop.bind("<Escape>", lambda e: pop.destroy())
        search_entry.focus_set()

    # ── Undo / Redo ───────────────────────────────────────────────────────────
    def _pre_edit_snapshot(self):
        """Speichert einen Snapshot VOR der Bearbeitung eines Feldes.
        Wird bei FocusIn aufgerufen – noch kein Push in den Undo-Stack."""
        if getattr(self, '_loading_month', False) or getattr(self, '_block_undo_push', False):
            return
        import copy
        try:
            self._save_month()
        except Exception:
            pass
        self._pre_edit_snap = copy.deepcopy(self.data)

    def _commit_edit_if_changed(self):
        """Wird bei FocusOut aufgerufen. Hat sich etwas geändert, wird der
        Pre-Edit-Snapshot als Undo-Eintrag committet (und Redo geleert)."""
        if getattr(self, '_loading_month', False) or getattr(self, '_block_undo_push', False):
            return
        snap_before = getattr(self, '_pre_edit_snap', None)
        if snap_before is None:
            return
        self._pre_edit_snap = None
        import copy
        try:
            self._save_month()
        except Exception:
            pass
        if self.data == snap_before:
            return   # keine Änderung → kein Eintrag
        key = self._month_key()
        is_dup = (
            self._undo_stack and
            self._undo_stack[-1]["key"] == key and
            self._undo_stack[-1]["snap"] == snap_before
        )
        if not is_dup:
            self._undo_stack.append({"key": key, "snap": snap_before})
            if len(self._undo_stack) > 100:
                self._undo_stack.pop(0)
        self._redo_stack.clear()

    def _push_undo_state(self, clear_redo=True):
        """Vollständigen Daten-Snapshot auf den Undo-Stack legen.

        Speichert immer den GESAMTEN self.data-Zustand (alle Monate), damit
        _copy_titles_forward-Propagierungen zu Zukunftsmonaten korrekt
        rückgängig gemacht werden können.

        clear_redo=False  → Redo-Stack bleibt erhalten (FocusIn / Titelbearbeitung –
                            nur Vorab-Sicherung, noch keine echte Aktion).
        clear_redo=True   → Redo-Stack wird gelöscht (echte Strukturänderung).
        """
        if getattr(self, '_loading_month', False) or getattr(self, '_block_undo_push', False):
            return
        import copy
        try:
            self._save_month()
        except Exception:
            pass
        key  = self._month_key()
        snap = copy.deepcopy(self.data)   # ← gesamtes Daten-Dict

        # Doppelten Zustand nicht mehrfach speichern
        is_dup = bool(
            self._undo_stack and
            self._undo_stack[-1]["key"] == key and
            self._undo_stack[-1]["snap"] == snap
        )
        if not is_dup:
            self._undo_stack.append({"key": key, "snap": snap})
            if len(self._undo_stack) > 100:
                self._undo_stack.pop(0)
        # Redo-Stack leeren, wenn dies eine echte Aktion ist (auch bei Duplikat)
        if clear_redo:
            self._redo_stack.clear()

    def _do_undo(self, event=None):
        # Pending edit erst committen – damit jedes Ctrl+Z genau einen Schritt macht
        if getattr(self, '_pre_edit_snap', None) is not None:
            self._commit_edit_if_changed()
            # Nach commit neu prüfen: falls der commit selbst eine Aktion ergab, fertig
            if not self._undo_stack:
                return
        if not self._undo_stack:
            return
        import copy
        try:
            self._save_month()
        except Exception:
            pass
        key_now  = self._month_key()
        snap_now = copy.deepcopy(self.data)
        # Aktuellen Vollzustand in Redo-Stack sichern (Duplikat vermeiden)
        if not self._redo_stack or self._redo_stack[-1]["snap"] != snap_now:
            self._redo_stack.append({"key": key_now, "snap": snap_now})

        entry    = self._undo_stack.pop()
        undo_key = entry["key"]
        # Gesamten Datenzustand wiederherstellen (inkl. aller Zukunftsmonate)
        self.data = copy.deepcopy(entry["snap"])
        save_data(self.data)
        if undo_key != key_now:
            parts = undo_key.split("-")
            self.current_year.set(int(parts[0]))
            self.current_month.set(int(parts[1]) - 1)
        self._load_month()

    def _do_redo(self, event=None):
        # Pending edit erst committen bevor redo läuft
        if getattr(self, '_pre_edit_snap', None) is not None:
            self._commit_edit_if_changed()
        if not self._redo_stack:
            return
        import copy
        try:
            self._save_month()
        except Exception:
            pass
        key_now  = self._month_key()
        snap_now = copy.deepcopy(self.data)
        # Aktuellen Vollzustand in Undo-Stack sichern (Duplikat vermeiden)
        if not self._undo_stack or self._undo_stack[-1]["snap"] != snap_now:
            self._undo_stack.append({"key": key_now, "snap": snap_now})

        entry    = self._redo_stack.pop()
        redo_key = entry["key"]
        # Gesamten Datenzustand wiederherstellen (inkl. aller Zukunftsmonate)
        self.data = copy.deepcopy(entry["snap"])
        save_data(self.data)
        if redo_key != key_now:
            parts = redo_key.split("-")
            self.current_year.set(int(parts[0]))
            self.current_month.set(int(parts[1]) - 1)
        self._load_month()

    def _ctx_widget(self):
        """Gibt das Ziel-Widget für Clipboard-Aktionen zurück (Entry oder Text)."""
        w = getattr(self, '_ctx_target', None)
        if w is None:
            w = self.focus_get()
        if isinstance(w, (tk.Entry, tk.Text)):
            return w
        return None

    def _do_copy(self, event=None):
        """Kopiert den markierten Text (oder den gesamten Inhalt) ins Clipboard."""
        w = self._ctx_widget()
        if w is None:
            return
        try:
            if isinstance(w, tk.Entry):
                try:
                    text = w.selection_get()
                except tk.TclError:
                    text = w.get()
            else:  # tk.Text
                try:
                    text = w.get(tk.SEL_FIRST, tk.SEL_LAST)
                except tk.TclError:
                    text = w.get("1.0", "end-1c")
            self.clipboard_clear()
            self.clipboard_append(text)
        except Exception:
            pass

    def _do_cut(self, event=None):
        """Schneidet den markierten Text aus und legt ihn ins Clipboard."""
        w = self._ctx_widget()
        if w is None:
            return
        try:
            if isinstance(w, tk.Entry):
                try:
                    text = w.selection_get()
                    self.clipboard_clear()
                    self.clipboard_append(text)
                    w.delete(tk.SEL_FIRST, tk.SEL_LAST)
                except tk.TclError:
                    text = w.get()
                    self.clipboard_clear()
                    self.clipboard_append(text)
                    w.delete(0, tk.END)
            else:  # tk.Text
                try:
                    text = w.get(tk.SEL_FIRST, tk.SEL_LAST)
                    self.clipboard_clear()
                    self.clipboard_append(text)
                    w.delete(tk.SEL_FIRST, tk.SEL_LAST)
                except tk.TclError:
                    text = w.get("1.0", "end-1c")
                    self.clipboard_clear()
                    self.clipboard_append(text)
                    w.delete("1.0", tk.END)
        except Exception:
            pass

    def _do_paste(self, event=None):
        """Fügt Text aus dem Clipboard ein; ersetzt Markierung falls vorhanden."""
        w = self._ctx_widget()
        if w is None:
            return
        try:
            text = self.clipboard_get()
            if isinstance(w, tk.Entry):
                try:
                    w.delete(tk.SEL_FIRST, tk.SEL_LAST)
                    w.insert(tk.SEL_FIRST, text)
                except tk.TclError:
                    w.insert(tk.INSERT, text)
            else:  # tk.Text
                try:
                    w.delete(tk.SEL_FIRST, tk.SEL_LAST)
                except tk.TclError:
                    pass
                w.insert(tk.INSERT, text)
        except Exception:
            pass

    def _do_select_all(self, event=None):
        """Markiert den gesamten Inhalt des Ziel-Widgets."""
        w = self._ctx_widget()
        if w is None:
            return
        try:
            w.focus_set()
            if isinstance(w, tk.Entry):
                w.selection_range(0, tk.END)
            else:  # tk.Text
                w.tag_add(tk.SEL, "1.0", tk.END)
                w.mark_set(tk.INSERT, tk.END)
        except Exception:
            pass

    def _copy_from_prev_month(self):
        """Kopiert Eintrags-Werte (Betrag + Titel) des Vormonats in den aktuellen Monat."""
        import copy
        yr = self.current_year.get()
        mo = self.current_month.get()  # 0-based
        if mo == 0:
            prev_yr, prev_mo = yr - 1, 11
        else:
            prev_yr, prev_mo = yr, mo - 1
        prev_key = f"{prev_yr}-{prev_mo+1:02d}"
        prev_data = self.data.get(prev_key, {})
        if not prev_data:
            tk.messagebox.showinfo("Vormonat übertragen",
                                   f"Keine Daten im Vormonat ({prev_key}) vorhanden.")
            return
        self._push_undo_state()
        self._save_month()
        key = self._month_key()
        cats = ["income", "essenz", "freizeit", "auto", "versicherung"] + self._custom_cat_order
        cur = self.data.setdefault(key, {})
        for cat in cats:
            if cat in prev_data:
                cur[cat] = copy.deepcopy(prev_data[cat])
        save_data(self.data)
        self._load_month()

    def _clear_month_entries(self):
        """Löscht alle Eingabewerte (Beträge) des aktuellen Monats – Zeilen bleiben erhalten."""
        if not tk.messagebox.askyesno("Einträge löschen",
                                      "Alle Einträge des aktuellen Monats wirklich löschen?"):
            return
        self._push_undo_state()
        self._save_month()
        key = self._month_key()
        md = self.data.get(key, {})
        cats = ["income", "essenz", "freizeit", "auto", "versicherung"] + self._custom_cat_order
        for cat in cats:
            for row in md.get(cat, []):
                row["amount"] = ""
        save_data(self.data)
        self._load_month()

    # ── Gesamtübersicht ───────────────────────────────────────────────────────
    def _open_overview(self):
        T = self._T()
        self._save_month()

        filled = {}
        _check_cats = ["income","essenz","freizeit","auto","versicherung"] + self._custom_cat_order
        for k, v in self.data.items():
            if k.startswith("year_"):
                continue
            if any(any(self._parse_amount(r["amount"]) > 0 for r in v.get(cat, []))
                   for cat in _check_cats):
                filled[k] = v

        if not filled:
            tk.messagebox.showinfo("Gesamtübersicht",
                                   "Noch keine gespeicherten Daten vorhanden.")
            return

        win = tk.Toplevel(self)
        win.title("Gesamtübersicht \u2013 alle Monate")
        try:
            win.geometry(self._overview_geometry or "1400x900")
        except Exception:
            self._overview_geometry = None
            win.geometry("1400x900")
        win.configure(bg=T["BG_APP"])

        def _track_ov_geometry(e=None):
            try:
                geom = win.geometry()
                if geom and "x" in geom:
                    self._overview_geometry = geom
            except Exception:
                pass
        win.bind("<Configure>", _track_ov_geometry)

        # Mehrere Fenster gleichzeitig erlaubt – Zähler für offene Übersichtsfenster
        if not hasattr(self, "_ov_open_count"):
            self._ov_open_count = 0
        self._ov_open_count += 1
        # Haupt-Scrolling beim ersten Fenster deaktivieren
        if self._ov_open_count == 1:
            self.unbind_all("<MouseWheel>")

        # _zoom_active[0]: True = Zoom-Modus (nach Klick ins Diagramm aktiv)
        #                  False = Scroll-Modus (Standard, Klick außerhalb Diagramm)
        _zoom_active = [False]
        _active_cv   = [None]
        _open_figs   = []

        def _add_mwheel_zoom(fig, ax):
            def _zoom(event):
                # Zoom nur aktiv wenn Zoom-Modus per Klick ins Diagramm eingeschaltet
                if not _zoom_active[0]:
                    return
                if event.inaxes != ax:
                    return
                factor = 0.85 if event.button == "up" else 1.15
                xl, yl = ax.get_xlim(), ax.get_ylim()
                xc, yc = event.xdata, event.ydata
                ax.set_xlim([xc + (x-xc)*factor for x in xl])
                ax.set_ylim([yc + (y-yc)*factor for y in yl])
                fig.canvas.draw_idle()
            fig.canvas.mpl_connect("scroll_event", _zoom)

            # Left-click drag pan + Zoom-Modus aktivieren
            _pan_state = [False, None, None]  # [active, x0, y0]

            def _pan_press(event):
                if event.button == 1 and event.inaxes == ax:
                    _zoom_active[0] = True   # Zoom-Modus einschalten
                    _pan_state[0] = True
                    _pan_state[1] = event.xdata
                    _pan_state[2] = event.ydata
                elif event.button == 1:
                    # Klick ins Diagramm-Widget, aber außerhalb der Achsen
                    # (Rand, Titel, Achsenbeschriftung) → Zoom deaktivieren
                    _zoom_active[0] = False

            def _pan_release(event):
                _pan_state[0] = False

            def _pan_motion(event):
                if not _pan_state[0] or event.inaxes != ax:
                    return
                if event.xdata is None or event.ydata is None:
                    return
                dx = _pan_state[1] - event.xdata
                dy = _pan_state[2] - event.ydata
                xl = ax.get_xlim()
                yl = ax.get_ylim()
                ax.set_xlim(xl[0]+dx, xl[1]+dx)
                ax.set_ylim(yl[0]+dy, yl[1]+dy)
                fig.canvas.draw_idle()

            fig.canvas.mpl_connect("button_press_event",   _pan_press)
            fig.canvas.mpl_connect("button_release_event", _pan_release)
            fig.canvas.mpl_connect("motion_notify_event",  _pan_motion)

        def _ov_scroll(e):
            try:
                if not _zoom_active[0]:
                    _ov_canvas.yview_scroll(int(-1*(e.delta/120)), "units")
            except Exception:
                pass
        def _activate_this_window(e=None):
            """Dieses Fenster übernimmt Scroll- und Klick-Events (mehrere Fenster)."""
            win.bind_all("<MouseWheel>", _ov_scroll)
            win.bind_all("<Button-1>", _ov_click_check)

        def _ov_click_check(e):
            """Deaktiviert Zoom-Modus, wenn außerhalb des aktiven Diagramms geklickt.
            Schließt auch das Kontext-Menü-Popup falls es offen ist."""
            # Kontext-Menü schließen wenn außerhalb geklickt
            try:
                pop = getattr(self, '_ctx_popup', None)
                if pop and pop.winfo_exists():
                    px, py = pop.winfo_rootx(), pop.winfo_rooty()
                    pw, ph = pop.winfo_width(), pop.winfo_height()
                    if not (px <= e.x_root <= px + pw and py <= e.y_root <= py + ph):
                        pop.destroy()
            except Exception:
                pass
            # Zoom-Modus deaktivieren
            if _active_cv[0] is not None:
                try:
                    cw = _active_cv[0].get_tk_widget()
                    cx, cy = cw.winfo_rootx(), cw.winfo_rooty()
                    cw2, ch = cw.winfo_width(), cw.winfo_height()
                    if not (cx <= e.x_root <= cx + cw2 and cy <= e.y_root <= cy + ch):
                        _zoom_active[0] = False
                except Exception:
                    _zoom_active[0] = False
            else:
                _zoom_active[0] = False
        # Beim Betreten dieses Fensters Scroll/Klick-Events übernehmen
        win.bind("<Enter>", _activate_this_window)
        _activate_this_window()  # sofort aktivieren

        def _restore_mwheel(e=None):
            self._ov_open_count = max(0, getattr(self, "_ov_open_count", 1) - 1)
            if self._ov_open_count == 0:
                if hasattr(self, "_global_mousewheel_fn"):
                    self.bind_all("<MouseWheel>", self._global_mousewheel_fn)
                self.bind_all("<Button-1>", lambda ev: self._schedule_refresh())
        win.bind("<Destroy>", _restore_mwheel)

        # Scrollbarer Übersichts-Container
        _ov_vsb = tk.Scrollbar(win, orient="vertical")
        _ov_vsb.pack(side="right", fill="y")
        _ov_canvas = tk.Canvas(win, bg=T["BG_APP"], highlightthickness=0,
                               yscrollcommand=_ov_vsb.set)
        _ov_vsb.configure(command=_ov_canvas.yview)
        _ov_canvas.pack(fill="both", expand=True)
        _ov_inner = tk.Frame(_ov_canvas, bg=T["BG_APP"])
        _ov_wid   = _ov_canvas.create_window((0, 0), window=_ov_inner, anchor="nw")
        _ov_inner.bind("<Configure>",
            lambda e: _ov_canvas.configure(scrollregion=_ov_canvas.bbox("all")))
        _ov_canvas.bind("<Configure>",
            lambda e: _ov_canvas.itemconfig(_ov_wid, width=e.width))

        # ── Info-Fenster für Gesamtübersicht ─────────────────────────────────
        def _open_ov_info():
            iT = self._T()
            iwin = tk.Toplevel(win)
            iwin.title("Gesamtübersicht – Hilfe")
            iwin.configure(bg=iT["BG_APP"])
            iwin.geometry("760x600")
            iwin.attributes("-topmost", True)
            iwin.grab_set()
            wx = win.winfo_rootx(); wy = win.winfo_rooty()
            ww = win.winfo_width(); wh = win.winfo_height()
            iwin.geometry(f"760x600+{wx + ww//2 - 380}+{wy + wh//2 - 300}")

            outer_i = tk.Frame(iwin, bg=iT["BG_APP"])
            outer_i.pack(fill="both", expand=True)
            cv_i = tk.Canvas(outer_i, bg=iT["BG_APP"], highlightthickness=0)
            vsb_i = tk.Scrollbar(outer_i, orient="vertical", command=cv_i.yview)
            vsb_i.pack(side="right", fill="y")
            cv_i.pack(side="left", fill="both", expand=True)
            cv_i.configure(yscrollcommand=vsb_i.set)
            ct_i = tk.Frame(cv_i, bg=iT["BG_APP"])
            cw_i = cv_i.create_window((0, 0), window=ct_i, anchor="nw")
            ct_i.bind("<Configure>",
                      lambda e: cv_i.configure(scrollregion=cv_i.bbox("all")))
            cv_i.bind("<Configure>",
                      lambda e: cv_i.itemconfig(cw_i, width=e.width))
            def _cv_i_scroll(e):
                try:
                    cv_i.yview_scroll(int(-1*(e.delta/120)), "units")
                except Exception:
                    pass
            cv_i.bind_all("<MouseWheel>", _cv_i_scroll)

            def _restore_ov_mwheel(e=None):
                if e is not None and e.widget is not iwin:
                    return
                try:
                    win.bind_all("<MouseWheel>", _ov_scroll)
                except Exception:
                    pass
            iwin.bind("<Destroy>", _restore_ov_mwheel)

            FH1   = ("Helvetica Neue", 14, "bold")
            FH2   = ("Helvetica Neue", 10, "bold")
            FBODY = ("Helvetica Neue", 10)
            IP    = 22

            def isec(title, color, icon=""):
                row = tk.Frame(ct_i, bg=color, pady=5)
                row.pack(fill="x", pady=(14, 0))
                tk.Label(row, text=f"  {icon}  {title}" if icon else f"  {title}",
                         font=FH1, bg=color, fg="#FFFFFF").pack(side="left", padx=8)
                c = tk.Frame(ct_i, bg=iT["BG_CARD"],
                             highlightthickness=1, highlightbackground=iT["BORDER"])
                return c

            def ibody(c, text):
                tk.Label(c, text=text, font=FBODY, bg=iT["BG_CARD"],
                         fg=iT["TEXT_LABEL"], justify="left",
                         wraplength=680, anchor="w").pack(anchor="w", padx=IP, pady=(6,3))

            def ihint(c, text):
                tk.Label(c, text=f"  {text}", font=("Helvetica Neue", 9, "italic"),
                         bg=iT["BG_CARD"], fg=iT["TEXT_MUTED"],
                         justify="left", wraplength=680, anchor="w"
                         ).pack(anchor="w", padx=IP, pady=(0, 6))

            def ibullet(c, items):
                for sym, txt in items:
                    r = tk.Frame(c, bg=iT["BG_CARD"])
                    r.pack(anchor="w", padx=IP, pady=1)
                    tk.Label(r, text=sym, font=FH2, bg=iT["BG_CARD"],
                             fg=INCOME_CLR, width=4).pack(side="left")
                    tk.Label(r, text=txt, font=FBODY,
                             bg=iT["BG_CARD"], fg=iT["TEXT_LABEL"]).pack(side="left")

            # 1. Überblick
            c = isec("Was zeigt die Gesamtübersicht?", INCOME_CLR, "📊")
            c.pack(fill="x")
            ibody(c, "Die Gesamtübersicht fasst alle Monate mit eingetragenen Daten zusammen. "
                     "Oben siehst du Statistikkarten mit Gesamteinnahmen, Gesamtausgaben, "
                     "Ersparnis und Durchschnittswerten. Darunter folgt das Hauptdiagramm "
                     "mit allen Monaten im Überblick.")
            # Statistik-Mock
            sm = tk.Frame(c, bg=iT["BG_CARD"])
            sm.pack(anchor="w", padx=IP, pady=(4, 8))
            for lbl, val, clr in [("Gesamteinnahmen","24 500 €", INCOME_CLR),
                                   ("Gesamtausgaben", "18 200 €", ESSENZ_CLR),
                                   ("Ersparnis",      " 6 300 €", SAVINGS_CLR)]:
                box = tk.Frame(sm, bg=iT["BG_CARD"],
                               highlightthickness=1, highlightbackground=iT["BORDER"])
                box.pack(side="left", padx=4)
                tk.Frame(box, bg=clr, height=3).pack(fill="x")
                tk.Label(box, text=val, font=("Helvetica Neue", 11, "bold"),
                         bg=iT["BG_CARD"], fg=clr, padx=12, pady=4).pack()
                tk.Label(box, text=lbl, font=("Helvetica Neue", 8),
                         bg=iT["BG_CARD"], fg=iT["TEXT_MUTED"], padx=12, pady=4).pack()

            # 1b. Jahresfilter
            c = isec("Jahresfilter", "#0284C7", "🗓")
            c.pack(fill="x", pady=(0, 0))
            ibody(c, "Direkt unter dem Titel findest du den Jahresfilter: einen Button "
                     "\"Alle Jahre\" sowie je einen Button pro vorhandenem Jahr. "
                     "Standardmäßig ist das Jahr des letzten Eintrags aktiv.")
            ibody(c, "Ein Klick auf einen Jahres-Button filtert alle Inhalte auf dieses Jahr: "
                     "Statistikkarten, Balken-/Linien-/Wasserfalldiagramm, Tortendiagramm, "
                     "Heatmap, Prognose, Top-Ausgaben-Ranking und Treemap zeigen dann nur "
                     "die Daten des gewählten Jahres.")
            ihint(c, "\"Alle Jahre\" zeigt die vollständige Historie. "
                     "Drilldown aus dem Tortendiagramm öffnet sich ebenfalls gefiltert.")

            # 2. Diagrammtypen
            c = isec("Diagrammtypen", "#0369A1", "📈")
            c.pack(fill="x")
            ibody(c, "Oben links kannst du zwischen drei Ansichten wechseln:")
            ibullet(c, [
                ("▐▌", "Balkendiagramm – alle Kategorien als gestapelte Balken pro Monat"),
                ("〜",  "Liniendiagramm – Verlauf jeder Kategorie als Linie über die Zeit"),
                ("≋",   "Wasserfalldiagramm – zeigt wie Einnahmen zu Ersparnis werden (Ø der gefilterten Monate)"),
            ])
            ihint(c, "Rechts erscheint zusätzlich ein Tortendiagramm mit der Gesamtaufteilung aller gefilterten Monate.")

            # 2b. Tortendiagramm & Fixkosten-Schraffur
            c = isec("Tortendiagramm & Fixkostenanteil-Schraffur", FIXKOSTEN_CLR, "🥧")
            c.pack(fill="x")
            ibody(c, "Das Tortendiagramm rechts zeigt die Gesamtaufteilung aller gefilterten Monate. "
                     "Bereiche mit Fixkosten-Anteil sind zusätzlich schraffiert dargestellt: "
                     "eine hellere Füllfarbe füllt den Schraffur-Bereich, Linien in der Originalfarbe "
                     "überlagern ihn. Eine dezente Trennlinie teilt variablen und fixen Anteil.")
            ibody(c, "Über dem Diagramm erscheint der Label \"Fixkostenanteil: X%\" – er zeigt, "
                     "wie viel Prozent der Gesamtausgaben (ohne Ersparnis) auf Fixkosten entfallen.")
            ihint(c, "Klick auf ein Tortenstück öffnet den Drilldown für diese Kategorie – "
                     "gefiltert nach dem aktuell gewählten Jahr.")

            # 2c. Drilldown – jahresbewusst
            c = isec("Drilldown – Kategorie-Monatsverlauf", AUTO_CLR, "🔎")
            c.pack(fill="x")
            ibody(c, "Ein Klick auf ein Segment im Tortendiagramm öffnet ein Detailfenster "
                     "mit dem monatlichen Verlauf dieser Kategorie als Balkendiagramm. "
                     "Durchschnittslinie (gestrichelt) und Gesamtbetrag-Badge werden angezeigt.")
            ibody(c, "Ist ein Jahresfilter aktiv, zeigt der Drilldown nur die Monate dieses Jahres. "
                     "Ist \"Alle Jahre\" gewählt, erscheint die vollständige Historie.")
            ihint(c, "Das Detailfenster merkt sich seine letzte Größe und Position.")

            # 2d. Monatsheatmap
            c = isec("Monatsheatmap", "#0891B2", "🟦")
            c.pack(fill="x")
            ibody(c, "Die Heatmap visualisiert alle Monate als farbige Kacheln: "
                     "Je dunkler/intensiver die Farbe, desto höher die Ausgaben in diesem Monat. "
                     "Monate ohne Daten erscheinen hell/leer.")
            ihint(c, "Die Heatmap reagiert auf den Jahresfilter – bei einem aktiven Jahr "
                     "werden nur die Monate dieses Jahres eingefärbt.")

            # 2e. Kumulierter Ersparnis-Verlauf
            c = isec("Kumulierter Ersparnis-Verlauf", SAVINGS_CLR, "📈")
            c.pack(fill="x")
            ibody(c, "Unterhalb des Hauptdiagramms zeigt ein Liniendiagramm die kumulierte "
                     "Ersparnis über alle gefilterten Monate. Jeder Punkt ist die Summe aller "
                     "bisherigen Ersparnisse bis zu diesem Monat.")
            ibody(c, "Ist ein Sparziel (%) gesetzt, erscheint zusätzlich eine gepunktete "
                     "Ziellinie: sie zeigt, wie viel du kumuliert gespart hättest, wenn du jeden "
                     "Monat exakt diesen Prozentsatz deines Einkommens gespart hättest.")
            ihint(c, "Liegt deine Linie über der Ziellinie – Ziel erreicht oder übertroffen. "
                     "Liegt sie darunter – zeigt die Differenz, wie viel noch aufzuholen ist.")

            # 2f. Prognose
            c = isec("Jahresprognose", "#F59E0B", "🔭")
            c.pack(fill="x")
            ibody(c, "Im Analyse-Bereich wird auf Basis der bisherigen Monatsdaten eine "
                     "Hochrechnung für das Gesamtjahr erstellt. Die Prognose extrapoliert "
                     "Einnahmen, Ausgaben und Ersparnis auf 12 Monate.")
            ihint(c, "Je mehr Monate bereits erfasst sind, desto genauer wird die Prognose.")

            # 2g. Top-Ausgaben-Ranking
            c = isec("Top-Ausgaben-Ranking", NEUTRAL, "🏆")
            c.pack(fill="x")
            ibody(c, "Unterhalb der Heatmap werden die Top 20 Einzelposten nach Gesamtbetrag "
                     "in zwei Spalten gelistet. Alle gleich betitelten Zeilen werden über alle "
                     "gefilterten Monate summiert.")
            ibody(c, "Fixkosten gehen anteilig ein: (Jahresbetrag ÷ 12) × Anzahl der befüllten Monate. "
                     "Die Top-3-Plätze erhalten farbige Badges in der dominanten Kategorie-Farbe. "
                     "Ein horizontaler Balken zeigt die relative Größe des Betrags.")
            ihint(c, "Das Ranking reagiert auf den Jahresfilter – bei \"2025\" erscheinen nur "
                     "Posten, die in 2025 erfasst wurden.")

            # 2e. Ausgaben-Treemap
            c = isec("Ausgaben-Treemap", VERSICH_CLR, "🗺")
            c.pack(fill="x")
            ibody(c, "Die Treemap stellt Ausgabenkategorien als Rechtecke dar – je größer das "
                     "Rechteck, desto höher der Gesamtbetrag. Jede Kachel zeigt Kategorienamen, "
                     "absoluten Betrag und prozentualen Anteil. Farben entsprechen den "
                     "Kategoriefarben.")
            ibody(c, "Kleine Kacheln zeigen nur den Namen oder werden ohne Text dargestellt, "
                     "wenn der Platz nicht ausreicht.")
            ihint(c, "Die Treemap wird ebenfalls durch den Jahresfilter eingegrenzt. "
                     "Erscheint sie leer, gibt es keine Ausgaben für den gewählten Zeitraum.")

            # 3. Zoom & Pan
            c = isec("Zoom & Verschieben im Diagramm", FREIZEIT_CLR, "🔍")
            c.pack(fill="x")
            ibody(c, "Du kannst direkt im Diagramm interagieren:")
            steps_z = [
                ("①", INCOME_CLR,   "Klicke ins Diagramm → Zoom-Modus wird aktiviert"),
                ("②", FREIZEIT_CLR, "Scrolle mit dem Mausrad → hinein- oder herauszoomen"),
                ("③", AUTO_CLR,     "Klicke & ziehe → Diagramm verschieben (panning)"),
                ("④", SAVINGS_CLR,  "Klicke außerhalb des Diagramms → Zoom-Modus deaktiviert, normales Scrollen geht wieder"),
            ]
            for num, clr, txt in steps_z:
                r = tk.Frame(c, bg=iT["BG_CARD"])
                r.pack(anchor="w", padx=IP, pady=2)
                tk.Label(r, text=num, font=("Helvetica Neue", 10, "bold"),
                         bg=clr, fg="#FFFFFF", width=3, padx=4).pack(side="left", padx=(0,8))
                tk.Label(r, text=txt, font=FBODY,
                         bg=iT["BG_CARD"], fg=iT["TEXT_LABEL"]).pack(side="left")
            ihint(c, "Tipp: Nach dem Zoomen einfach außerhalb des Diagramms klicken, "
                     "um wieder normal in der Gesamtübersicht zu scrollen.")

            # 4. Zurück / Weiterarbeiten
            c = isec("Zurück zur normalen Ansicht", FIXKOSTEN_CLR, "↩")
            c.pack(fill="x", pady=(0, 20))
            ibody(c, "Die Gesamtübersicht ist ein eigenes Fenster – du kannst es jederzeit "
                     "schließen (× oben rechts) und kehrst automatisch zur Hauptansicht zurück. "
                     "Alle Eingaben bleiben erhalten.")
            ibody(c, "Wenn du im Zoom-Modus bist und wieder in der Gesamtübersicht scrollen möchtest: "
                     "einfach einmal außerhalb des Diagramms klicken – das deaktiviert den Zoom-Modus sofort.")
            ihint(c, "Die Gesamtübersicht liest nur die gespeicherten Daten – Änderungen im "
                     "Hauptfenster werden erst nach erneutem Öffnen sichtbar.")

            tk.Button(iwin, text="Schließen", font=("Helvetica Neue", 10, "bold"),
                      bg=INCOME_CLR, fg="#FFFFFF", relief="flat", bd=0,
                      cursor="hand2", padx=20, pady=8,
                      activebackground="#2563EB", activeforeground="#FFFFFF",
                      command=iwin.destroy).pack(pady=10)

        # Kopf
        _ov_head = tk.Frame(_ov_inner, bg=T["BG_APP"])
        _ov_head.pack(fill="x", padx=26, pady=(18, 2))
        tk.Label(_ov_head, text="Gesamtübersicht", bg=T["BG_APP"],
                 font=("Helvetica Neue", 18, "bold"),
                 fg=T["TEXT_PRIMARY"]).pack(side="left")
        tk.Button(_ov_head, text="\u24d8",
                  font=("Helvetica Neue", 13, "bold"),
                  bg=T["BG_APP"], fg=T["TEXT_MUTED"], bd=0, cursor="hand2",
                  activebackground=T["BG_HOVER"], activeforeground=INCOME_CLR,
                  command=_open_ov_info).pack(side="left", padx=(10, 0))
        tk.Frame(_ov_inner, bg=T["BORDER"], height=1).pack(fill="x", padx=26, pady=10)

        # Jahresfilter-Buttons
        all_years = sorted(set(k.split("-")[0] for k in filled.keys()))
        _active_yf = [sorted(filled.keys())[-1].split("-")[0]]  # default = Jahr des letzten Eintrags

        _yf_row = tk.Frame(_ov_inner, bg=T["BG_APP"])
        _yf_row.pack(fill="x", padx=24, pady=(4, 8))

        _yf_btns = {}

        def _make_yf_btn(lbl, yf):
            is_active = (_active_yf[0] == yf)
            return tk.Button(
                _yf_row, text=lbl,
                font=("Helvetica Neue", 11, "bold"),
                bg=self._cc("income") if is_active else T["BG_INPUT"],
                fg="#FFFFFF" if is_active else T["TEXT_LABEL"],
                relief="flat", bd=0, cursor="hand2", padx=18, pady=8,
                activebackground=self._cc("income"), activeforeground="#FFFFFF")

        # Vergleichen-Button zuerst packen (side="right" → erscheint ganz rechts)
        tk.Button(
            _yf_row, text="⊕  Vergleichen",
            font=("Helvetica Neue", 11, "bold"),
            bg=T["BG_INPUT"], fg=T["TEXT_LABEL"],
            relief="flat", bd=0, cursor="hand2", padx=18, pady=8,
            activebackground=self._cc("income"), activeforeground="#FFFFFF",
            command=self._open_overview
        ).pack(side="right", padx=(12, 0))

        _yf_btns["all"] = _make_yf_btn("Alle Jahre", None)
        _yf_btns["all"].pack(side="left", padx=(0, 6))
        for _yr in all_years:
            _yf_btns[_yr] = _make_yf_btn(_yr, _yr)
            _yf_btns[_yr].pack(side="left", padx=(0, 4))

        _cp = tk.Frame(_ov_inner, bg=T["BG_APP"])
        _cp.pack(fill="x")

        def _render_content(year_filter):
            # Alte Matplotlib-Figuren schliessen
            if _active_cv[0] is not None:
                try: plt.close(_active_cv[0].figure)
                except Exception: pass
            for _fig in list(_open_figs):
                try: plt.close(_fig)
                except Exception: pass
            _open_figs.clear()
            _active_cv[0] = None

            # Inhalt-Frame leeren
            for _w in _cp.winfo_children():
                _w.destroy()

            # Jahresfilter-Button-Styles aktualisieren
            _active_yf[0] = year_filter
            for _k, _b in _yf_btns.items():
                _yf_val = None if _k == "all" else _k
                _is_act = (_active_yf[0] == _yf_val)
                _b.config(
                    bg=self._cc("income") if _is_act else T["BG_INPUT"],
                    fg="#FFFFFF" if _is_act else T["TEXT_LABEL"])

            # Schlüssel nach Filter bestimmen
            all_sk = sorted(filled.keys())
            if year_filter is not None:
                sorted_keys = [k for k in all_sk if k.startswith(year_filter)]
            else:
                sorted_keys = all_sk

            if not sorted_keys:
                tk.Label(_cp, text=f"Keine Daten für {year_filter}.",
                         bg=T["BG_APP"], font=("Helvetica Neue", 11),
                         fg=T["TEXT_MUTED"]).pack(anchor="w", padx=26, pady=20)
                return

            # ── Daten-Loop ────────────────────────────────────────────────────
            months_lbls = []
            inc_vals, ess_vals, fre_vals = [], [], []
            auto_vals, versich_vals, fixmo_vals, sav_vals, net_vals = [], [], [], [], []
            custom_vals_by_cat = {ck: [] for ck in self._custom_cat_order}
            # fix-Anteile je Kategorie (für Kreisdiagramm-Schraffur)
            fix_ess_vals, fix_fre_vals, fix_aut_vals, fix_ver_vals = [], [], [], []
            fix_custom_vals_by_cat = {ck: [] for ck in self._custom_cat_order}
            _dyn_color_to_cat = self._build_fix_color_to_cat()

            for key in sorted_keys:
                md     = filled[key]
                year   = int(key.split("-")[0])
                yd     = self.data.get(f"year_{year}", {})
                month_num    = int(key.split("-")[1])
                year_from_mo = yd.get("fixkosten_from_month", 1)
                if md.get("fixkosten_month_only") or "fixkosten" in md:
                    fix_rows = md.get("fixkosten", [])
                elif month_num < year_from_mo:
                    fix_rows = []
                else:
                    fix_rows = yd.get("fixkosten", [])
                fix_by_cat = {cat: 0.0 for cat in list(FIX_COLOR_TO_CAT.values()) + self._custom_cat_order}
                for fr in fix_rows:
                    amt = self._parse_amount(fr["amount"]) / 12.0
                    clr = fr.get("color", FIXKOSTEN_CLR)
                    cat = _dyn_color_to_cat.get(clr, "fixkosten")
                    fix_by_cat[cat] += amt

                inc = sum(self._parse_amount(r["amount"]) for r in md.get("income",       []))
                ess = sum(self._parse_amount(r["amount"]) for r in md.get("essenz",        [])) + \
                      fix_by_cat["essenz"]
                fre = sum(self._parse_amount(r["amount"]) for r in md.get("freizeit",      [])) + \
                      fix_by_cat["freizeit"]
                aut = sum(self._parse_amount(r["amount"]) for r in md.get("auto",          [])) + \
                      fix_by_cat["auto"]
                ver = sum(self._parse_amount(r["amount"]) for r in md.get("versicherung",  [])) + \
                      fix_by_cat["versicherung"]
                fix = fix_by_cat["fixkosten"]

                fix_ess_vals.append(fix_by_cat["essenz"])
                fix_fre_vals.append(fix_by_cat["freizeit"])
                fix_aut_vals.append(fix_by_cat["auto"])
                fix_ver_vals.append(fix_by_cat["versicherung"])

                total_custom_mo = 0.0
                for ck in self._custom_cat_order:
                    cv = sum(self._parse_amount(r["amount"]) for r in md.get(ck, []))
                    cv += fix_by_cat.get(ck, 0.0)
                    custom_vals_by_cat[ck].append(cv)
                    fix_custom_vals_by_cat[ck].append(fix_by_cat.get(ck, 0.0))
                    total_custom_mo += cv

                _net = inc - ess - fre - aut - ver - fix - total_custom_mo
                sav  = max(0.0, _net)

                try:
                    y, m  = key.split("-")
                    label = f"{MONTHS_DE[int(m)-1][:3]} {y[2:]}"
                except Exception:
                    label = key
                months_lbls.append(label)
                inc_vals.append(inc);  ess_vals.append(ess);   fre_vals.append(fre)
                auto_vals.append(aut); versich_vals.append(ver)
                fixmo_vals.append(fix); sav_vals.append(sav); net_vals.append(_net)

            # fix-Gesamtanteile je Kategorie (für Kreisdiagramm-Schraffur)
            total_fix_in_ess = sum(fix_ess_vals)
            total_fix_in_fre = sum(fix_fre_vals)
            total_fix_in_aut = sum(fix_aut_vals)
            total_fix_in_ver = sum(fix_ver_vals)
            total_fix_in_custom = {ck: sum(fix_custom_vals_by_cat[ck]) for ck in self._custom_cat_order}

            # Monatsanzahl-Label
            tk.Label(_cp, text=f"{len(sorted_keys)} Monat(e) mit Daten",
                     bg=T["BG_APP"], font=("Helvetica Neue", 10),
                     fg=T["TEXT_MUTED"]).pack(anchor="w", padx=26)

            # ── Statistik-Karten ──────────────────────────────────────────────
            stats_row = tk.Frame(_cp, bg=T["BG_APP"])
            stats_row.pack(fill="x", padx=26, pady=(0,12))
            total_inc = sum(inc_vals); total_ess = sum(ess_vals)
            total_fre = sum(fre_vals); total_aut = sum(auto_vals)
            total_ver = sum(versich_vals); total_fix = sum(fixmo_vals)
            total_custom_all = {ck: sum(custom_vals_by_cat[ck]) for ck in self._custom_cat_order}
            total_out = total_ess + total_fre + total_aut + total_ver + total_fix + sum(total_custom_all.values())
            total_sav = sum(sav_vals)
            avg_inc   = total_inc / len(inc_vals) if inc_vals else 0
            avg_sav   = total_sav / len(sav_vals) if sav_vals else 0
            best_idx  = sav_vals.index(max(sav_vals)) if sav_vals else 0

            for label, value, clr in [
                ("Gesamteinnahmen",                       f"{total_inc:,.2f} \u20ac", self._cc("income")),
                ("Gesamtausgaben",                        f"{total_out:,.2f} \u20ac", self._cc("essenz")),
                (f"Gesamt{self._cn('savings').lower()}",  f"{total_sav:,.2f} \u20ac", self._cc("savings")),
                (f"\xf8 {self._cn('income')} / Mo",       f"{avg_inc:,.2f} \u20ac",   self._cc("income")),
                (f"\xf8 {self._cn('savings')} / Mo",      f"{avg_sav:,.2f} \u20ac",   self._cc("savings")),
                (f"Bester {self._cn('savings')}monat",
                 months_lbls[best_idx] if months_lbls else "\u2013",                  self._cc("savings")),
            ]:
                c = tk.Frame(stats_row, bg=T["BG_CARD"],
                             highlightthickness=1, highlightbackground=T["BORDER"])
                c.pack(side="left", expand=True, fill="x", padx=4)
                tk.Frame(c, bg=clr, height=3).pack(fill="x")
                tk.Label(c, text=value, font=("Helvetica Neue", 13, "bold"),
                         bg=T["BG_CARD"], fg=clr).pack(pady=(8,2), padx=10)
                tk.Label(c, text=label, font=("Helvetica Neue", 8),
                         bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(pady=(0,8), padx=10)

            # ── Toggle ────────────────────────────────────────────────────────
            toggle_bar = tk.Frame(_cp, bg=T["BG_APP"])
            toggle_bar.pack(fill="x", padx=24, pady=(0,4))

            def _make_toggle(text, mode):
                return tk.Button(toggle_bar, text=text,
                                 font=("Helvetica Neue", 9, "bold"),
                                 bg=self._cc("income") if self.overview_chart == mode else T["BG_INPUT"],
                                 fg="#FFFFFF"          if self.overview_chart == mode else T["TEXT_LABEL"],
                                 relief="flat", bd=0, cursor="hand2", padx=14, pady=5,
                                 activebackground=self._cc("income"), activeforeground="#FFFFFF")

            btn_bar  = _make_toggle("▐▌ Balkendiagramm", "bar")
            btn_line = _make_toggle("〜  Liniendiagramm", "line")
            btn_wfall = _make_toggle("≋ Wasserfall", "waterfall")
            btn_bar.pack(side="left", padx=(0,6))
            btn_line.pack(side="left")
            btn_wfall.pack(side="left", padx=(6, 0))

            charts_frame = tk.Frame(_cp, bg=T["BG_APP"])
            charts_frame.pack(fill="x", padx=20, pady=(0,4))
            chart_host = tk.Frame(charts_frame, bg=T["BG_APP"])
            chart_host.pack(side="left", fill="both", expand=True)
            pie_host = tk.Frame(charts_frame, bg=T["BG_APP"])
            pie_host.pack(side="left", fill="both")

            bar_data_sets = [
                (inc_vals,     self._cc("income"),      self._cn("income")),
                (ess_vals,     self._cc("essenz"),       self._cn("essenz")),
                (fre_vals,     self._cc("freizeit"),     self._cn("freizeit")),
                (auto_vals,    self._cc("auto"),         self._cn("auto")),
                (versich_vals, self._cc("versicherung"), self._cn("versicherung")),
                (fixmo_vals,   self._cc("fixkosten"),    self._cn("fixkosten") + "/Mo"),
                (sav_vals,     self._cc("savings"),      self._cn("savings")),
                *[(custom_vals_by_cat[ck], self._cc(ck), self._cn(ck))
                  for ck in self._custom_cat_order if any(v > 0 for v in custom_vals_by_cat[ck])],
            ]

            _pie_hover_reconnect = [None]   # set after pie hover is wired up

            def _draw_chart(mode):
                if _active_cv[0]:
                    _active_cv[0].get_tk_widget().destroy()
                    plt.close(_active_cv[0].figure)
                    _active_cv[0] = None

                fig_c, ax_c = plt.subplots(figsize=(6.0, 4.6), facecolor=T["BG_APP"])
                ax_c.set_facecolor(T["BG_CARD"])
                x = list(range(len(months_lbls)))

                if mode == "bar":
                    n_ds  = len(bar_data_sets)
                    w     = max(0.06, min(0.12, 0.84 / n_ds))
                    half  = (n_ds - 1) / 2.0
                    offs  = [i - half for i in range(n_ds)]
                    for (vals, clr, lbl), off in zip(bar_data_sets, offs):
                        ax_c.bar([i+off*w for i in x], vals, width=w,
                                 color=clr, label=lbl, alpha=0.9, edgecolor="none")
                    ax_c.set_title("Monatlicher Verlauf – Balken",
                                   color=T["TEXT_PRIMARY"], fontsize=10,
                                   fontweight="bold", pad=8)
                elif mode == "waterfall":
                    n_mo = len(months_lbls) if months_lbls else 1
                    avg_inc_w  = sum(inc_vals)     / n_mo
                    avg_ess_w  = sum(ess_vals)     / n_mo
                    avg_fre_w  = sum(fre_vals)     / n_mo
                    avg_aut_w  = sum(auto_vals)    / n_mo
                    avg_ver_w  = sum(versich_vals) / n_mo
                    avg_fix_w  = sum(fixmo_vals)   / n_mo

                    _wf_exp_items = [
                        (self._cn("essenz"),        avg_ess_w, self._cc("essenz")),
                        (self._cn("freizeit"),      avg_fre_w, self._cc("freizeit")),
                        (self._cn("auto"),          avg_aut_w, self._cc("auto")),
                        (self._cn("versicherung"),  avg_ver_w, self._cc("versicherung")),
                        (self._cn("fixkosten")+"/Mo", avg_fix_w, self._cc("fixkosten")),
                        *[(self._cn(ck),
                           sum(custom_vals_by_cat[ck]) / n_mo,
                           self._cc(ck))
                          for ck in self._custom_cat_order
                          if any(v > 0 for v in custom_vals_by_cat[ck])],
                    ]
                    _wf_exp_items = [(l, v, c) for l, v, c in _wf_exp_items if v > 0.5]

                    avg_total_out_w = sum(v for _, v, _ in _wf_exp_items)
                    avg_net_w = avg_inc_w - avg_total_out_w

                    _wf_labels = ([self._cn("income")] +
                                  [l for l, v, c in _wf_exp_items] +
                                  [self._cn("savings") if avg_net_w >= 0 else "Defizit"])
                    _wf_heights = ([avg_inc_w] +
                                   [v for l, v, c in _wf_exp_items] +
                                   [abs(avg_net_w)])
                    _wf_colors  = ([self._cc("income")] +
                                   [c for l, v, c in _wf_exp_items] +
                                   [self._cc("savings") if avg_net_w >= 0 else DEFICIT_CLR])

                    # Compute waterfall bottoms
                    _wf_bottoms = []
                    _running_w = avg_inc_w
                    _wf_bottoms.append(0.0)  # income: starts at 0
                    for i in range(1, len(_wf_heights) - 1):
                        _running_w -= _wf_heights[i]
                        _wf_bottoms.append(max(0.0, _running_w))
                    _wf_bottoms.append(0.0)  # savings/deficit: starts at 0

                    _x_wf = list(range(len(_wf_labels)))
                    ax_c.bar(_x_wf, _wf_heights, bottom=_wf_bottoms,
                             color=_wf_colors, width=0.55, edgecolor="none", alpha=0.9)

                    # Connector lines
                    _conn_y = avg_inc_w
                    for i in range(1, len(_wf_labels) - 1):
                        ax_c.plot([i - 0.5, i - 0.275],
                                  [_conn_y, _conn_y],
                                  color=T["BORDER"], linewidth=0.8, linestyle="--")
                        _conn_y -= _wf_heights[i]

                    # Value labels on bars
                    _max_h_wf = max(_wf_heights) if _wf_heights else 1
                    for i, (b, h) in enumerate(zip(_wf_bottoms, _wf_heights)):
                        ax_c.text(i, b + h + _max_h_wf * 0.012,
                                  f"{h:,.0f}€",
                                  ha="center", va="bottom",
                                  fontsize=6.5, color=T["TEXT_PRIMARY"],
                                  fontweight="bold")

                    ax_c.set_xticks(_x_wf)
                    ax_c.set_xticklabels(_wf_labels, rotation=35, ha="right",
                                          fontsize=8, color=T["TEXT_MUTED"])
                    ax_c.set_title("Ø Monatliches Wasserfall-Diagramm",
                                   color=T["TEXT_PRIMARY"], fontsize=10,
                                   fontweight="bold", pad=8)
                else:
                    for vals, clr, lbl in bar_data_sets:
                        if any(v > 0 for v in vals):
                            ax_c.plot(x, vals, color=clr, label=lbl,
                                      linewidth=2.2, marker="", alpha=0.9)
                    ax_c.set_title("Monatlicher Verlauf – Linie",
                                   color=T["TEXT_PRIMARY"], fontsize=10,
                                   fontweight="bold", pad=8)

                if mode != "waterfall" and x:
                    ax_c.set_xticks(x)
                    ax_c.set_xticklabels(months_lbls, rotation=35, ha="right",
                                         fontsize=8, color=T["TEXT_MUTED"])
                for sp in ["top","right"]:
                    ax_c.spines[sp].set_visible(False)
                for sp in ["left","bottom"]:
                    ax_c.spines[sp].set_color(T["BORDER"])
                ax_c.tick_params(colors=T["TEXT_MUTED"], labelsize=8)
                ax_c.set_ylabel("\u20ac", color=T["TEXT_MUTED"], fontsize=9)
                if mode != "waterfall":
                    ax_c.legend(fontsize=7.5, frameon=False,
                                labelcolor=T["TEXT_LABEL"], ncol=2)
                fig_c.tight_layout(pad=2.0)
                cv = FigureCanvasTkAgg(fig_c, master=chart_host)
                cv.get_tk_widget().pack(fill="both", expand=True)
                cv.draw()
                _add_mwheel_zoom(fig_c, ax_c)
                _active_cv[0] = cv
                _zoom_active[0] = False   # Reset NACH vollem Setup, überschreibt etwaige Spurious-Events
                # matplotlib's plt.close() / widget destroy kann bind_all-Handler entfernen –
                # daher nach jedem Chart-Aufbau neu registrieren:
                win.bind_all("<MouseWheel>", _ov_scroll)
                win.bind_all("<Button-1>", _ov_click_check)
                # Pie-Hover nach Chart-Wechsel neu verbinden
                if _pie_hover_reconnect[0]:
                    win.after(30, _pie_hover_reconnect[0])

            def _switch(mode):
                self.overview_chart = mode
                btn_bar.config(
                    bg=self._cc("income") if mode == "bar"  else T["BG_INPUT"],
                    fg="#FFFFFF"          if mode == "bar"  else T["TEXT_LABEL"])
                btn_line.config(
                    bg=self._cc("income") if mode == "line" else T["BG_INPUT"],
                    fg="#FFFFFF"          if mode == "line" else T["TEXT_LABEL"])
                btn_wfall.config(
                    bg=self._cc("income") if mode == "waterfall" else T["BG_INPUT"],
                    fg="#FFFFFF"          if mode == "waterfall" else T["TEXT_LABEL"])
                _draw_chart(mode)
                # Verzögerter Reset: fängt alle Events ab, die während des Renderings
                # asynchron verarbeitet werden (z.B. interne tkinter Configure-Events)
                win.after(0, lambda: (
                    _zoom_active.__setitem__(0, False),
                    win.bind_all("<MouseWheel>", _ov_scroll),
                    win.bind_all("<Button-1>", _ov_click_check),
                ))

            btn_bar.config(command=lambda: _switch("bar"))
            btn_line.config(command=lambda: _switch("line"))
            btn_wfall.config(command=lambda: _switch("waterfall"))
            _draw_chart(self.overview_chart)

            # Tortendiagramm – grösser
            fig_pie, ax_p = plt.subplots(figsize=(7.2, 6.0), facecolor=T["BG_APP"])
            ax_p.set_facecolor(T["BG_APP"])
            # fix-Anteile je Segment für Schraffur (gleiche Reihenfolge wie p_raw)
            _ov_fix_raw = [
                (total_ess, self._cc("essenz"),      f"{self._cn('essenz')}\n{total_ess:,.0f}\u20ac",      "essenz",       self._cn("essenz"),       total_fix_in_ess),
                (total_fre, self._cc("freizeit"),    f"{self._cn('freizeit')}\n{total_fre:,.0f}\u20ac",    "freizeit",     self._cn("freizeit"),     total_fix_in_fre),
                (total_aut, self._cc("auto"),        f"{self._cn('auto')}\n{total_aut:,.0f}\u20ac",        "auto",         self._cn("auto"),         total_fix_in_aut),
                (total_ver, self._cc("versicherung"),f"{self._cn('versicherung')}\n{total_ver:,.0f}\u20ac","versicherung", self._cn("versicherung"), total_fix_in_ver),
                (total_fix, self._cc("fixkosten"),   f"{self._cn('fixkosten')}\n{total_fix:,.0f}\u20ac",   "fixkosten",    self._cn("fixkosten"),    total_fix),
                (total_sav, self._cc("savings"),     f"{self._cn('savings')}\n{total_sav:,.0f}\u20ac",     "savings",      self._cn("savings"),      0.0),
                *[(total_custom_all[ck], self._cc(ck),
                   f"{self._cn(ck)}\n{total_custom_all[ck]:,.0f}\u20ac", ck, self._cn(ck),
                   total_fix_in_custom.get(ck, 0.0))
                  for ck in self._custom_cat_order if total_custom_all.get(ck, 0) > 0],
            ]
            p_raw = [(s,c,l,k,n,fx) for s,c,l,k,n,fx in _ov_fix_raw if s > 0]
            if p_raw:
                sz, cl, lb, p_keys, p_names, p_fix = zip(*p_raw)
                wp2, _, at2 = ax_p.pie(
                    sz, colors=cl, labels=None,
                    autopct=lambda p: f"{p:.1f}%", startangle=90,
                    pctdistance=0.72,
                    wedgeprops=dict(linewidth=0.5, edgecolor="#777777"),
                    radius=0.92)
                for at in at2:
                    at.set_color("#FFFFFF"); at.set_fontsize(9); at.set_fontweight("bold")
                ax_p.legend(wp2, lb, loc="lower center", bbox_to_anchor=(0.5,-0.30),
                            ncol=3, fontsize=8, frameon=False, labelcolor=T["TEXT_LABEL"])
                # ── Fixkosten-Anteil schraffiert markieren ─────────────────────
                _ov_total_all_fix = sum(p_fix)
                _ov_total_out_pie = sum(s for s in sz if s > 0) - (total_sav if total_sav > 0 else 0)
                _old_hlw2 = matplotlib.rcParams.get('hatch.linewidth', 1.0)
                matplotlib.rcParams['hatch.linewidth'] = 5.0
                for wdg, seg_val, fix_val, clr in zip(wp2, sz, p_fix, cl):
                    if fix_val <= 0 or seg_val <= 0:
                        continue
                    t1, t2 = wdg.theta1, wdg.theta2
                    fix_span = (t2 - t1) * fix_val / seg_val
                    _lclr2 = self._lighten_color(clr, factor=0.28)
                    # Helle Fläche (Zwischenräume ausgefüllt) + Originalfarbe als Linien
                    ax_p.add_patch(matplotlib.patches.Wedge(
                        (0, 0), 0.92, t1, t1 + fix_span,
                        facecolor=_lclr2, hatch='//', edgecolor=clr,
                        linewidth=0, zorder=3))
                    # Dezente Trennlinie (wie Tortenstück-Grenzen)
                    if fix_val < seg_val:
                        _sep_rad2 = math.radians(t1 + fix_span)
                        ax_p.plot(
                            [0, 0.92 * math.cos(_sep_rad2)],
                            [0, 0.92 * math.sin(_sep_rad2)],
                            color=_lclr2, linewidth=0.5, zorder=4)
                matplotlib.rcParams['hatch.linewidth'] = _old_hlw2
                for at in at2:
                    at.set_zorder(6)
                if _ov_total_out_pie > 0 and _ov_total_all_fix > 0:
                    _ov_fix_pct = _ov_total_all_fix / _ov_total_out_pie * 100
                    ax_p.text(0, 1.05, f"Fixkostenanteil: {_ov_fix_pct:.1f}%",
                              ha="center", va="center", fontsize=8.5,
                              color=T["TEXT_MUTED"], transform=ax_p.transData)
                # Drilldown: Klick auf Segment → Kategorie-Monatsverlauf
                for _wdg in wp2:
                    _wdg.set_picker(True)
                _ov_p_keys  = list(p_keys)
                _ov_p_names = list(p_names)
                _ov_wp2     = list(wp2)
                # ── Hover-Tooltip + Drilldown ─────────────────────────────
                _ov_sz = list(sz); _ov_cl = list(cl)
                _ov_nm = max(len(sorted_keys), 1)
                _OV_PIE_R = 0.92
                # Persistent tip window for overview pie
                _ov_tw = tk.Toplevel(self); _ov_tw.overrideredirect(True)
                _ov_tw.attributes("-topmost", True); _ov_tw.geometry("+9999+9999")
                try: _ov_tw.wm_attributes("-disabled", True)
                except Exception: pass
                _ov_tw.configure(bg=T["BORDER"])
                _ov_tw_out = tk.Frame(_ov_tw, bg=T["BG_CARD"]); _ov_tw_out.pack(padx=1, pady=1)
                _ov_stripe = tk.Frame(_ov_tw_out, bg=T["BG_CARD"], height=3); _ov_stripe.pack(fill="x")
                _ov_tw_pad = tk.Frame(_ov_tw_out, bg=T["BG_CARD"]); _ov_tw_pad.pack(fill="x", padx=10, pady=(5,6))
                _ov_tw_name  = tk.Label(_ov_tw_pad, text="", font=("Helvetica Neue", 9, "bold"),
                                        bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]); _ov_tw_name.pack(anchor="w")
                _ov_tw_total = tk.Label(_ov_tw_pad, text="", font=("Helvetica Neue", 8),
                                        bg=T["BG_CARD"], fg=T["TEXT_MUTED"]); _ov_tw_total.pack(anchor="w")
                _ov_tw_val   = tk.Label(_ov_tw_pad, text="", font=("Helvetica Neue", 8),
                                        bg=T["BG_CARD"], fg=T["TEXT_MUTED"]); _ov_tw_val.pack(anchor="w")
                # Destroy tip when overview window closes
                win.bind("<Destroy>", lambda e, t=_ov_tw, w=win: (t.destroy() if t.winfo_exists() and e.widget is w else None), add="+")
                _ov_last_idx = [-1]; _ov_hide_job = [None]
                _ov_sz_total = max(sum(_ov_sz), 1e-9)
                def _ov_cancel_hide():
                    if _ov_hide_job[0]: self.after_cancel(_ov_hide_job[0]); _ov_hide_job[0] = None
                def _ov_do_hide():
                    try:
                        if _ov_tw.winfo_exists():
                            _ov_tw.geometry("+9999+9999")
                    except Exception: pass
                    _ov_last_idx[0] = -1
                def _ov_hide():
                    _ov_cancel_hide(); _ov_hide_job[0] = self.after(60, _ov_do_hide)
                def _ov_update(cat_name, total_val, avg_val, pct, clr, sx, sy):
                    try:
                        if not _ov_tw.winfo_exists(): return
                        _ov_stripe.configure(bg=clr)
                        _ov_tw_name.configure(text=f"{cat_name}  {pct:.1f}\u202f%")
                        _ov_tw_total.configure(text=f"{total_val:,.2f}\u00a0\u20ac")
                        _ov_tw_val.configure(text=f"\u00d8 pro Monat:  {avg_val:,.2f}\u00a0\u20ac")
                        _ov_tw.geometry(f"+{sx + 14}+{sy - 76}")
                    except Exception: pass
                def _ov_idx_at(ev, _w=_ov_wp2, _r=_OV_PIE_R):
                    if ev.xdata is None or ev.ydata is None: return -1
                    if math.sqrt(ev.xdata**2 + ev.ydata**2) > _r: return -1
                    ang = math.degrees(math.atan2(ev.ydata, ev.xdata)) % 360
                    for i, wdg in enumerate(_w):
                        t1, t2 = wdg.theta1 % 360, wdg.theta2 % 360
                        if t1 <= t2:
                            if t1 <= ang <= t2: return i
                        else:
                            if ang >= t1 or ang <= t2: return i
                    return -1
                def _on_ov_pie_hover(ev, _s=_ov_p_names, _sz=_ov_sz, _nm=_ov_nm, _cl=_ov_cl, _stot=_ov_sz_total):
                    if ev.inaxes is None: _ov_hide(); return
                    i = _ov_idx_at(ev)
                    if i >= 0:
                        _ov_cancel_hide(); _ov_last_idx[0] = i
                        _wgt = _cv_pie_ref[0].get_tk_widget()
                        sx = _wgt.winfo_rootx() + int(ev.x) + 2
                        sy = _wgt.winfo_rooty() + _wgt.winfo_height() - int(ev.y) - 2
                        _pct = _sz[i] / _stot * 100
                        _ov_update(_s[i], _sz[i], _sz[i] / _nm, _pct, _cl[i], sx, sy)
                    else:
                        _ov_hide()
                _ov_pie_hover_cid = [fig_pie.canvas.mpl_connect('motion_notify_event', _on_ov_pie_hover)]
                def _reconnect_ov_pie_hover():
                    try: fig_pie.canvas.mpl_disconnect(_ov_pie_hover_cid[0])
                    except Exception: pass
                    _ov_pie_hover_cid[0] = fig_pie.canvas.mpl_connect('motion_notify_event', _on_ov_pie_hover)
                _pie_hover_reconnect[0] = _reconnect_ov_pie_hover
                def _on_ov_pie_pick(event, _k=_ov_p_keys, _n=_ov_p_names, _w=_ov_wp2, _yf=year_filter):
                    if not hasattr(event, 'artist'): return
                    me = getattr(event, 'mouseevent', None)
                    if me is None or me.button not in (1, 3): return
                    try: idx = _w.index(event.artist)
                    except ValueError: return
                    if 0 <= idx < len(_k):
                        _ov_do_hide()
                        self._open_cat_drilldown(_k[idx], _n[idx], year_filter=_yf)
                fig_pie.canvas.mpl_connect('pick_event', _on_ov_pie_pick)
            _cv_pie_ref = [None]
            ax_p.set_title(f"Gesamtaufteilung ({len(sorted_keys)} Monate)",
                           color=T["TEXT_PRIMARY"], fontsize=10, fontweight="bold", pad=8)
            fig_pie.tight_layout(pad=2.5)
            cv_pie = FigureCanvasTkAgg(fig_pie, master=pie_host)
            _cv_pie_ref[0] = cv_pie
            cv_pie.get_tk_widget().pack(fill="both", expand=True)
            cv_pie.draw()
            _open_figs.append(fig_pie)

            # ═══ Analyse & Prognose ═══════════════════════════════════════════════
            tk.Frame(_cp, bg=T["BORDER"], height=1).pack(fill="x", padx=26, pady=(14,6))
            tk.Label(_cp, text="Analyse & Prognose",
                     font=("Helvetica Neue", 14, "bold"),
                     bg=T["BG_APP"], fg=T["TEXT_PRIMARY"]).pack(anchor="w", padx=26, pady=(0,10))

            analyse_row = tk.Frame(_cp, bg=T["BG_APP"])
            analyse_row.pack(fill="x", padx=20, pady=(0,8))

            # ── Heatmap ───────────────────────────────────────────────────────────
            hm_card = tk.Frame(analyse_row, bg=T["BG_CARD"],
                               highlightthickness=1, highlightbackground=T["BORDER"])
            hm_card.pack(side="left", fill="both", expand=True, padx=(0,8))
            tk.Frame(hm_card, bg=NEUTRAL, height=3).pack(fill="x")
            tk.Label(hm_card, text="Heatmap \u2013 Jahres\u00fcbersicht",
                     font=("Helvetica Neue", 11, "bold"),
                     bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(anchor="w", padx=14, pady=(10,4))
            tk.Label(hm_card, text="Gr\u00fcn\u2009=\u2009viel gespart  \u2022  Rot\u2009=\u2009Defizit  \u2022  Grau\u2009=\u2009keine Daten",
                     font=("Helvetica Neue", 7), bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(anchor="w", padx=14)
            tk.Frame(hm_card, bg=T["BORDER_LIGHT"], height=1).pack(fill="x", padx=14, pady=(4,6))

            from collections import defaultdict as _dd
            _ym = _dd(dict)
            for _k, _net_v, _iv in zip(sorted_keys, net_vals, inc_vals):
                _y, _m = _k.split("-")
                _ym[int(_y)][int(_m)] = (_net_v, _iv)  # net can be negative → shows deficit

            def _hm_clr(sav, inc):
                if inc <= 0: return T["BG_INPUT"]
                r = sav / inc
                if r >= 0.30:   return "#047857"
                elif r >= 0.20: return "#059669"
                elif r >= 0.10: return "#10B981"
                elif r > 0:     return "#6EE7B7"
                elif r > -0.10: return "#FCA5A5"
                else:           return "#EF4444"

            MSHORT = ["Jan","Feb","Mär","Apr","Mai","Jun","Jul","Aug","Sep","Okt","Nov","Dez"]
            hm_grid = tk.Frame(hm_card, bg=T["BG_CARD"])
            hm_grid.pack(fill="x", padx=14, pady=(0,10))
            # Header
            tk.Label(hm_grid, text="", width=5, bg=T["BG_CARD"],
                     font=("Helvetica Neue",9)).grid(row=0, column=0)
            for ci, mn in enumerate(MSHORT):
                tk.Label(hm_grid, text=mn, font=("Helvetica Neue",9),
                         bg=T["BG_CARD"], fg=T["TEXT_MUTED"], width=6).grid(row=0, column=ci+1, padx=1)
            tk.Label(hm_grid, text="\u2211 Jahr", font=("Helvetica Neue",9,"bold"),
                     bg=T["BG_CARD"], fg=T["TEXT_MUTED"], width=8).grid(row=0, column=13, padx=(6,1))
            for ri, yr in enumerate(sorted(_ym.keys())):
                tk.Label(hm_grid, text=str(yr), font=("Helvetica Neue",9,"bold"),
                         bg=T["BG_CARD"], fg=T["TEXT_LABEL"], width=5,
                         anchor="w").grid(row=ri+1, column=0, sticky="w", pady=2)
                for m in range(1, 13):
                    if m in _ym[yr]:
                        sv, iv = _ym[yr][m]
                        clr  = _hm_clr(sv, iv)
                        txt  = f"{sv/1000:.1f}k" if abs(sv) >= 1000 else f"{sv:.0f}"
                        lfg  = "#FFFFFF" if clr not in (T["BG_INPUT"], "#6EE7B7") else T["TEXT_MUTED"]
                    else:
                        clr, txt, lfg = T["BG_INPUT"], "", T["TEXT_MUTED"]
                    cell = tk.Frame(hm_grid, bg=clr, width=54, height=36,
                                    highlightthickness=1, highlightbackground=T["BORDER_LIGHT"])
                    cell.grid(row=ri+1, column=m, padx=1, pady=1)
                    cell.pack_propagate(False)
                    if txt:
                        tk.Label(cell, text=txt, font=("Helvetica Neue",9),
                                 bg=clr, fg=lfg).pack(expand=True)
                # Jahressumme (Summe aller Monate des Jahres, inkl. Defizitmonate)
                yr_total = sum(sv for sv, iv in _ym[yr].values())
                if _ym[yr]:
                    yr_txt   = f"{yr_total/1000:.1f}k" if abs(yr_total) >= 1000 else f"{yr_total:.0f}"
                    yr_bg    = "#10B981" if yr_total >= 0 else "#EF4444"
                    yr_fg    = "#FFFFFF"
                else:
                    yr_txt, yr_bg, yr_fg = "—", T["BG_INPUT"], T["TEXT_MUTED"]
                yr_cell = tk.Frame(hm_grid, bg=yr_bg, width=70, height=36,
                                   highlightthickness=1, highlightbackground=T["BORDER_LIGHT"])
                yr_cell.grid(row=ri+1, column=13, padx=(6,1), pady=1)
                yr_cell.pack_propagate(False)
                tk.Label(yr_cell, text=yr_txt, font=("Helvetica Neue",9,"bold"),
                         bg=yr_bg, fg=yr_fg).pack(expand=True)

            # Legende
            lgd = tk.Frame(hm_card, bg=T["BG_CARD"])
            lgd.pack(anchor="w", padx=14, pady=(0,12))
            for clr in ["#6EE7B7","#10B981","#059669","#047857"]:
                tk.Frame(lgd, bg=clr, width=20, height=13).pack(side="left", padx=1)
            tk.Label(lgd, text=" ← Ersparnis   ",
                     font=("Helvetica Neue",9), bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(side="left")
            for clr in ["#FCA5A5","#EF4444"]:
                tk.Frame(lgd, bg=clr, width=20, height=13).pack(side="left", padx=1)
            tk.Label(lgd, text=" ← Defizit",
                     font=("Helvetica Neue",9), bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(side="left")

            # ── Prognose ──────────────────────────────────────────────────────────
            prog_card = tk.Frame(analyse_row, bg=T["BG_CARD"],
                                 highlightthickness=1, highlightbackground=T["BORDER"],
                                 width=320)
            prog_card.pack(side="left", fill="y")
            prog_card.pack_propagate(False)
            tk.Frame(prog_card, bg=self._cc("savings"), height=3).pack(fill="x")
            tk.Label(prog_card, text="Prognose \u2013 Jahresende",
                     font=("Helvetica Neue", 11, "bold"),
                     bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(anchor="w", padx=14, pady=(10,4))
            tk.Frame(prog_card, bg=T["BORDER_LIGHT"], height=1).pack(fill="x", padx=14, pady=(0,6))

            now_dt          = datetime.now()
            cur_yr_str      = year_filter if year_filter else str(now_dt.year)
            cur_yr_keys     = [k for k in sorted_keys if k.startswith(cur_yr_str)]
            cur_yr_savs     = [net_vals[sorted_keys.index(k)] for k in cur_yr_keys]
            cur_yr_incs     = [inc_vals[sorted_keys.index(k)] for k in cur_yr_keys]
            last_n          = min(3, len(net_vals))
            avg_last_3      = sum(net_vals[-last_n:]) / last_n if last_n else 0.0
            avg_last_3_inc  = sum(inc_vals[-last_n:]) / last_n if last_n else 1.0
            months_done     = len(cur_yr_keys)
            remaining_mo    = max(0, 12 - months_done)
            ytd_sav         = sum(cur_yr_savs)
            proj_total      = ytd_sav + remaining_mo * avg_last_3
            proj_rate       = (avg_last_3 / avg_last_3_inc * 100) if avg_last_3_inc > 0 else 0.0

            def _prow(lbl, val, clr=None):
                r = tk.Frame(prog_card, bg=T["BG_CARD"])
                r.pack(fill="x", padx=14, pady=3)
                tk.Label(r, text=lbl, font=("Helvetica Neue",8),
                         bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(side="left")
                tk.Label(r, text=val, font=("Helvetica Neue",9,"bold"),
                         bg=T["BG_CARD"], fg=(clr or T["TEXT_PRIMARY"])).pack(side="right")

            _prow(f"Basis: letzte {last_n} Monate",
                  f"\u00d8 {avg_last_3:,.2f} \u20ac/Mo",
                  self._cc("savings") if avg_last_3 >= 0 else DEFICIT_CLR)
            _prow("Bisher gespart (lfd. Jahr)",
                  f"{ytd_sav:,.2f} \u20ac",
                  self._cc("savings") if ytd_sav >= 0 else DEFICIT_CLR)
            _prow("Noch ausstehend", f"{remaining_mo} Monat(e)")
            tk.Frame(prog_card, bg=T["BORDER_LIGHT"], height=1).pack(fill="x", padx=14, pady=(4,4))
            _proj_clr = self._cc("savings") if proj_total >= 0 else DEFICIT_CLR
            r_p = tk.Frame(prog_card, bg=T["BG_CARD"])
            r_p.pack(fill="x", padx=14, pady=4)
            tk.Label(r_p, text="Prognose Jahresende:",
                     font=("Helvetica Neue",9,"bold"),
                     bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(side="left")
            tk.Label(r_p, text=f"{proj_total:,.2f} \u20ac",
                     font=("Helvetica Neue",12,"bold"),
                     bg=T["BG_CARD"], fg=_proj_clr).pack(side="right")
            _prow("Progn. Sparrate", f"{proj_rate:.1f}\u2009%",
                  self._cc("savings") if proj_rate >= 10 else (DEFICIT_CLR if proj_rate < 0 else T["TEXT_LABEL"]))
            tk.Label(prog_card,
                     text=f"Basiert auf \u00d8 der letzten {last_n} Monate\nmit verf\u00fcgbaren Daten.",
                     font=("Helvetica Neue",7), justify="left",
                     bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(anchor="w", padx=14, pady=(8,10))

            # ── Kumulierter Ersparnis-Verlauf ──────────────────────────────────────
            cum_card = tk.Frame(_cp, bg=T["BG_CARD"],
                                highlightthickness=1, highlightbackground=T["BORDER"])
            cum_card.pack(fill="x", padx=20, pady=(0,8))
            tk.Frame(cum_card, bg=self._cc("savings"), height=3).pack(fill="x")
            _cum_header = tk.Frame(cum_card, bg=T["BG_CARD"])
            _cum_header.pack(fill="x", padx=14, pady=(10, 4))
            tk.Label(_cum_header, text="Kumulierter Ersparnis-Verlauf",
                     font=("Helvetica Neue", 11, "bold"),
                     bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(side="left")

            def _show_cum_info():
                _info = tk.Toplevel(win)
                _info.title("Diagramm-Erklärung")
                _info.configure(bg=T["BG_CARD"])
                _info.resizable(False, False)
                _info.grab_set()
                _TI = T
                _pad = dict(padx=20, pady=6)

                def _row(bold_text, normal_text=None):
                    f = tk.Frame(_info, bg=_TI["BG_CARD"])
                    f.pack(fill="x", padx=20, pady=3)
                    tk.Label(f, text=bold_text,
                             font=("Helvetica Neue", 9, "bold"),
                             bg=_TI["BG_CARD"], fg=_TI["TEXT_PRIMARY"],
                             justify="left", anchor="w").pack(anchor="w")
                    if normal_text:
                        tk.Label(f, text=normal_text,
                                 font=("Helvetica Neue", 9),
                                 bg=_TI["BG_CARD"], fg=_TI["TEXT_LABEL"],
                                 justify="left", wraplength=420, anchor="w").pack(anchor="w")

                tk.Frame(_info, bg=self._cc("savings"), height=3).pack(fill="x")
                tk.Label(_info, text="ⓘ  Kumulierter Ersparnis-Verlauf",
                         font=("Helvetica Neue", 12, "bold"),
                         bg=_TI["BG_CARD"], fg=_TI["TEXT_PRIMARY"]).pack(anchor="w", **_pad)
                tk.Frame(_info, bg=_TI["BORDER_LIGHT"], height=1).pack(fill="x", padx=20, pady=(0, 6))

                _row("Was zeigt die durchgezogene Linie?",
                     "Deine tatsächlich angesammelten Ersparnisse über alle Monate. "
                     "Jeder Datenpunkt = Summe aller Netto-Ersparnisse von Monat 1 bis zu diesem Monat. "
                     "Negative Monate (Defizit) lassen die Linie sinken.")
                _row("Was zeigt die gestrichelte Linie (Prognose)?",
                     "Eine Hochrechnung für die verbleibenden Monate des laufenden Jahres, "
                     "basierend auf dem Durchschnitt der letzten 1–3 Monate.")
                _row("Fadenkreuz beim Hover:",
                     "Fährst du mit der Maus über das Diagramm, erscheint ein Fadenkreuz. "
                     "Ein grüner Punkt springt zum nächsten Datenpunkt, ein Tooltip zeigt "
                     "Monat und kumulierten Betrag. Prognosepunkte sind als '(Prognose)' markiert.")

                if getattr(self, '_savings_goal_var', None):
                    try:
                        _gp = float(self._savings_goal_var.get())
                    except Exception:
                        _gp = 0
                    if _gp > 0:
                        tk.Frame(_info, bg=_TI["BORDER_LIGHT"], height=1).pack(
                            fill="x", padx=20, pady=(4, 6))
                        _row(f"Was zeigt die gepunktete Ziellinie ({_gp:.0f}% Sparquote)?",
                             f"Sie beantwortet: „Wie viel hätte ich kumuliert gespart, wenn ich jeden "
                             f"Monat exakt {_gp:.0f}% meines Einkommens gespart h\u00e4tte?\u201c \u2013 also die ideale "
                             "Ziellinie als Vergleichsma\u00dfstab.")
                        _row("Ziellinie liegt UNTER der tatsächlichen Linie →",
                             "Du übertriffst dein Sparziel insgesamt. ✓  (Auch wenn einzelne Monate "
                             "unter dem Ziel lagen – dein kumulierter Gesamtschnitt liegt darüber.)")
                        _row("Ziellinie liegt ÜBER der tatsächlichen Linie →",
                             "Du liegst hinter deinem Sparziel zurück. Noch aufzuholen: "
                             "Ziellinie − tatsächliche Linie = ausstehender Betrag.")
                        _row("Wichtig zu verstehen:",
                             "Der Chart zeigt das Gesamtbild über alle Monate – nicht ob du "
                             "den Zielwert im letzten Monat erreicht hast. Einzelne schwache Monate "
                             "können durch starke Vormonate kompensiert sein.")

                tk.Frame(_info, bg=_TI["BORDER_LIGHT"], height=1).pack(fill="x", padx=20, pady=(8, 4))
                tk.Button(_info, text="Verstanden",
                          font=("Helvetica Neue", 9, "bold"),
                          bg=self._cc("savings"), fg="#FFFFFF",
                          relief="flat", bd=0, cursor="hand2", padx=16, pady=5,
                          command=_info.destroy).pack(pady=(4, 14))

            tk.Button(_cum_header, text="ⓘ",
                      font=("Helvetica Neue", 11),
                      bg=T["BG_CARD"], fg=T["TEXT_MUTED"],
                      relief="flat", bd=0, cursor="hand2",
                      activebackground=T["BG_CARD"],
                      activeforeground=self._cc("savings"),
                      command=_show_cum_info).pack(side="right", padx=(0, 2))

            tk.Frame(cum_card, bg=T["BORDER_LIGHT"], height=1).pack(fill="x", padx=14)
            cum_host = tk.Frame(cum_card, bg=T["BG_CARD"])
            cum_host.pack(fill="x")

            cumulative, running = [], 0.0
            for s in net_vals:
                running += s
                cumulative.append(running)

            x_idx   = list(range(len(months_lbls)))
            sav_clr = self._cc("savings")
            fig_cum, ax_cum = plt.subplots(figsize=(13.0, 2.8), facecolor=T["BG_CARD"])
            ax_cum.set_facecolor(T["BG_CARD"])

            # Prognose-Verlängerung gestrichelt
            all_x, all_lbl = list(x_idx), list(months_lbls)
            if remaining_mo > 0 and avg_last_3 >= 0 and cumulative:
                base = cumulative[-1]
                proj_x = list(range(len(months_lbls)-1, len(months_lbls)+remaining_mo))
                proj_y = [base] + [base + avg_last_3*(i+1) for i in range(remaining_mo)]
                ax_cum.plot(proj_x, proj_y, color=sav_clr, linewidth=1.5,
                            linestyle="--", alpha=0.55, label="Prognose")
                ax_cum.fill_between(proj_x, proj_y, alpha=0.07, color=sav_clr)
                all_x   += proj_x[1:]
                all_lbl += [f"Mo+{i+1}" for i in range(remaining_mo)]

            if cumulative:
                ax_cum.fill_between(x_idx, cumulative, alpha=0.20, color=sav_clr)
                ax_cum.plot(x_idx, cumulative, color=sav_clr, linewidth=2.5,
                            marker="o", markersize=4,
                            label=f"Kumuliert {self._cn('savings')}")
            if all_x:
                ax_cum.set_xticks(all_x)
                ax_cum.set_xticklabels(all_lbl, rotation=35, ha="right",
                                       fontsize=7, color=T["TEXT_MUTED"])
            for sp in ["top","right"]:
                ax_cum.spines[sp].set_visible(False)
            for sp in ["left","bottom"]:
                ax_cum.spines[sp].set_color(T["BORDER"])
            ax_cum.tick_params(colors=T["TEXT_MUTED"], labelsize=7)
            ax_cum.set_ylabel("\u20ac", color=T["TEXT_MUTED"], fontsize=8)
            ax_cum.legend(fontsize=7.5, frameon=False, labelcolor=T["TEXT_LABEL"])
            ax_cum.set_title(f"Gesamtersparnis kumuliert \u2013 {len(months_lbls)} Monate",
                             color=T["TEXT_PRIMARY"], fontsize=9, pad=4)
            # Sparquoten-Ziel gestrichelte Linie im kumulierten Verlauf
            try:
                _ov_goal_pct = float(self._savings_goal_var.get().replace(",", ".")) / 100.0
            except (ValueError, TypeError):
                _ov_goal_pct = 0.0
            if _ov_goal_pct > 0 and inc_vals and cumulative:
                _goal_cum = [sum(inc_vals[:i+1]) * _ov_goal_pct for i in range(len(inc_vals))]
                ax_cum.plot(x_idx, _goal_cum, color="#F59E0B", linewidth=1.4,
                            linestyle=":", alpha=0.85,
                            label=f"Ziel {_ov_goal_pct*100:.0f}%")
                ax_cum.legend(fontsize=7.5, frameon=False, labelcolor=T["TEXT_LABEL"])
            fig_cum.tight_layout(pad=1.5)
            cv_cum = FigureCanvasTkAgg(fig_cum, master=cum_host)
            cv_cum.get_tk_widget().pack(fill="x")
            cv_cum.draw()

            # ── Crosshair im kumulierten Verlauf ──────────────────────────
            _ch_vline = ax_cum.axvline(x=0, color=T["TEXT_MUTED"], linewidth=0.8,
                                       linestyle="--", alpha=0.65, visible=False)
            _ch_hline = ax_cum.axhline(y=0, color=T["TEXT_MUTED"], linewidth=0.8,
                                       linestyle="--", alpha=0.65, visible=False)
            _ch_dot,  = ax_cum.plot([], [], "o", color=sav_clr, markersize=6,
                                    zorder=5, visible=False)
            _ch_annot = ax_cum.annotate(
                "", xy=(0, 0), xytext=(12, 12), textcoords="offset points",
                bbox=dict(boxstyle="round,pad=0.4", fc=T["BG_CARD"],
                          ec=T["BORDER"], alpha=0.92, linewidth=0.8),
                fontsize=7.5, color=T["TEXT_PRIMARY"], visible=False)

            # Lookup-Tabelle: x-Index → (Monatslabel, y-Wert, ist_Prognose)
            _ch_lookup = {}
            for _ci, _cx in enumerate(x_idx):
                if _ci < len(cumulative):
                    _ch_lookup[_cx] = (months_lbls[_ci], cumulative[_ci], False)
            if remaining_mo > 0 and avg_last_3 >= 0 and cumulative:
                _ch_base = cumulative[-1]
                for _pi in range(remaining_mo):
                    _ch_px = len(months_lbls) + _pi
                    _ch_py = _ch_base + avg_last_3 * (_pi + 1)
                    _ch_lookup[_ch_px] = (f"Mo+{_pi+1}", _ch_py, True)

            def _on_cum_hover(event):
                if not event.inaxes or event.inaxes is not ax_cum or event.xdata is None:
                    _ch_vline.set_visible(False)
                    _ch_hline.set_visible(False)
                    _ch_dot.set_visible(False)
                    _ch_annot.set_visible(False)
                    cv_cum.draw_idle()
                    return
                if not _ch_lookup:
                    return
                # Nächsten gültigen Datenpunkt finden
                xi = int(round(event.xdata))
                if xi not in _ch_lookup:
                    xi = min(_ch_lookup.keys(), key=lambda k: abs(k - xi))
                lbl, yv, is_proj = _ch_lookup[xi]
                _ch_vline.set_xdata([xi])
                _ch_vline.set_visible(True)
                _ch_hline.set_ydata([yv])
                _ch_hline.set_visible(True)
                _ch_dot.set_data([xi], [yv])
                _ch_dot.set_visible(True)
                # Tooltip-Text mit deutschem Zahlenformat
                proj_hint = "  (Prognose)" if is_proj else ""
                yv_fmt = f"{yv:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                _ch_annot.set_text(f"{lbl}{proj_hint}\n{yv_fmt} €")
                _ch_annot.xy = (xi, yv)
                # Tooltip-Seite wechseln je nach Position (links/rechts der Mitte)
                xmin, xmax = ax_cum.get_xlim()
                _ch_annot.xyann = (-80, 12) if xi > (xmin + xmax) / 2 else (12, 12)
                _ch_annot.set_visible(True)
                cv_cum.draw_idle()

            def _on_cum_leave(event):
                _ch_vline.set_visible(False)
                _ch_hline.set_visible(False)
                _ch_dot.set_visible(False)
                _ch_annot.set_visible(False)
                cv_cum.draw_idle()

            fig_cum.canvas.mpl_connect("motion_notify_event", _on_cum_hover)
            fig_cum.canvas.mpl_connect("axes_leave_event",    _on_cum_leave)
            # ──────────────────────────────────────────────────────────────
            _open_figs.append(fig_cum)

            # ── Top-Ausgaben-Ranking ──────────────────────────────────────────────
            tk.Frame(_cp, bg=T["BORDER"], height=1).pack(fill="x", padx=26, pady=(14, 6))
            tk.Label(_cp, text="Top-Ausgaben-Ranking",
                     font=("Helvetica Neue", 14, "bold"),
                     bg=T["BG_APP"], fg=T["TEXT_PRIMARY"]).pack(anchor="w", padx=26, pady=(0, 2))
            tk.Label(_cp, text="Summierung aller gleich betitelten Zeilen über alle Monate – Top 20",
                     font=("Helvetica Neue", 8),
                     bg=T["BG_APP"], fg=T["TEXT_MUTED"]).pack(anchor="w", padx=26, pady=(0, 8))

            from collections import defaultdict as _defdict
            _rank_agg  = _defdict(float)
            # Dominante Kategorie je Titel (nach höchstem Gesamtbetrag)
            _rank_cat_totals = _defdict(lambda: _defdict(float))
            _rank_cats = ["essenz", "freizeit", "auto", "versicherung"] + self._custom_cat_order
            for _rk in sorted_keys:
                _rmd = filled[_rk]
                for _rcat in _rank_cats:
                    for _rrow in _rmd.get(_rcat, []):
                        _ramt = self._parse_amount(_rrow.get("amount", ""))
                        if _ramt > 0:
                            _rtitle = (_rrow.get("title") or "Unbekannt").strip() or "Unbekannt"
                            _rank_agg[_rtitle] += _ramt
                            _rank_cat_totals[_rtitle][_rcat] += _ramt
            # Fixkosten: (Jahresbetrag ÷ 12) je Monat – monatsspezifische Overrides
            # und fixkosten_from_month werden korrekt berücksichtigt (wie in der App-Ansicht).
            for _rk in sorted_keys:
                _r_yr    = int(_rk.split("-")[0])
                _r_mo    = int(_rk.split("-")[1])
                _ryd     = self.data.get(f"year_{_r_yr}", {})
                _rmd     = self.data.get(_rk, {})
                _r_from  = _ryd.get("fixkosten_from_month", 1)
                if _rmd.get("fixkosten_month_only") or "fixkosten" in _rmd:
                    _r_fix_rows = _rmd.get("fixkosten", [])
                elif _r_mo < _r_from:
                    _r_fix_rows = []
                else:
                    _r_fix_rows = _ryd.get("fixkosten", [])
                for _rfr in _r_fix_rows:
                    _ramt = self._parse_amount(_rfr.get("amount", ""))
                    if _ramt > 0:
                        _rtitle = (_rfr.get("title") or "Fixkosten").strip() or "Fixkosten"
                        _contribution = _ramt / 12.0
                        _rank_agg[_rtitle] += _contribution
                        _rfr_cat = _dyn_color_to_cat.get(_rfr.get("color", FIXKOSTEN_CLR), "fixkosten")
                        _rank_cat_totals[_rtitle][_rfr_cat] += _contribution

            def _rank_entry_color(title):
                cats = _rank_cat_totals.get(title, {})
                if cats:
                    return self._cc(max(cats, key=cats.get))
                return NEUTRAL

            # Kategorie-Gesamtbeträge für Prozentberechnung im Tooltip
            _rank_cat_totals_sum = {
                "essenz":       total_ess,
                "freizeit":     total_fre,
                "auto":         total_aut,
                "versicherung": total_ver,
                "fixkosten":    total_fix,
                **{ck: total_custom_all.get(ck, 0.0) for ck in self._custom_cat_order},
            }

            def _rank_entry_cat_info(title):
                """Gibt (cat_display_name, cat_color, cat_total) der dominanten Kategorie zurück."""
                cats = _rank_cat_totals.get(title, {})
                if not cats:
                    return ("", NEUTRAL, 0.0)
                dom = max(cats, key=cats.get)
                return (self._cn(dom), self._cc(dom), _rank_cat_totals_sum.get(dom, 0.0))

            _top20 = sorted(_rank_agg.items(), key=lambda x: x[1], reverse=True)[:20]
            _rank_card = tk.Frame(_cp, bg=T["BG_CARD"],
                                  highlightthickness=1, highlightbackground=T["BORDER"])
            _rank_card.pack(fill="x", padx=20, pady=(0, 8))
            tk.Frame(_rank_card, bg=NEUTRAL, height=3).pack(fill="x")
            _rank_inner = tk.Frame(_rank_card, bg=T["BG_CARD"])
            _rank_inner.pack(fill="x", padx=14, pady=10)

            # ── Hover-Tooltip ──────────────────────────────────────────────────
            _rank_tip     = [None]
            _rank_tip_job = [None]
            _n_months     = max(len(sorted_keys), 1)

            def _show_rank_tip(event, title, avg_val, cat_name, cat_color, cat_pct):
                if _rank_tip_job[0]:
                    try: self.after_cancel(_rank_tip_job[0])
                    except Exception: pass
                    _rank_tip_job[0] = None
                if _rank_tip[0]:
                    try: _rank_tip[0].destroy()
                    except Exception: pass
                tip = tk.Toplevel(win)
                tip.overrideredirect(True)
                tip.attributes("-topmost", True)
                try: tip.wm_attributes("-disabled", True)
                except Exception: pass
                tip.configure(bg=T["BORDER"])
                _tip_out = tk.Frame(tip, bg=T["BG_CARD"]); _tip_out.pack(padx=1, pady=1)
                tk.Frame(_tip_out, bg=cat_color if cat_name else NEUTRAL,
                         height=3).pack(fill="x")
                inner = tk.Frame(_tip_out, bg=T["BG_CARD"], padx=10, pady=7)
                inner.pack(fill="x")
                tk.Label(inner, text=title,
                         font=("Helvetica Neue", 9, "bold"),
                         bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(anchor="w")
                _as = (f"{avg_val:,.2f}\u00a0\u20ac"
                       .replace(",", "X").replace(".", ",").replace("X", "."))
                tk.Label(inner, text=f"\u00d8 pro Monat:  {_as}",
                         font=("Helvetica Neue", 9),
                         bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(anchor="w", pady=(2, 0))
                if cat_name:
                    tk.Label(inner, text=f"{cat_pct:.1f}\u202f% von {cat_name}",
                             font=("Helvetica Neue", 8),
                             bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(anchor="w", pady=(1, 3))
                    _bar_track = tk.Frame(inner, bg=T["BORDER_LIGHT"], height=5, width=120)
                    _bar_track.pack(anchor="w", pady=(0, 1))
                    _bar_track.pack_propagate(False)
                    _fill_w = max(2, int(120 * min(cat_pct, 100) / 100))
                    tk.Frame(_bar_track, bg=cat_color, height=5, width=_fill_w).place(x=0, y=0)
                tip.update_idletasks()
                tip.geometry(f"+{event.x_root + 14}+{event.y_root - tip.winfo_height() - 4}")
                _rank_tip[0] = tip

            def _hide_rank_tip(e=None):
                def _do():
                    if _rank_tip[0]:
                        try: _rank_tip[0].destroy()
                        except Exception: pass
                        _rank_tip[0] = None
                _rank_tip_job[0] = self.after(80, _do)

            def _cancel_hide(e=None):
                if _rank_tip_job[0]:
                    try: self.after_cancel(_rank_tip_job[0])
                    except Exception: pass
                    _rank_tip_job[0] = None

            def _build_rank_col(parent, entries, start_rank, global_max):
                for _ri, (_rtitle, _rval) in enumerate(entries):
                    _abs_rank  = start_rank + _ri
                    _entry_clr = _rank_entry_color(_rtitle)
                    _badge_bg  = _entry_clr if _abs_rank < 3 else NEUTRAL
                    _avg       = _rval / _n_months
                    _cn_tip, _cc_tip, _ctotal = _rank_entry_cat_info(_rtitle)
                    _cpct = _rval / _ctotal * 100 if _ctotal > 0 else 0.0
                    _rrow_f = tk.Frame(parent, bg=T["BG_CARD"])
                    _rrow_f.pack(fill="x", pady=2)
                    _badge = tk.Label(_rrow_f, text=f"{_abs_rank+1:>2}",
                                      font=("Helvetica Neue", 9, "bold"),
                                      bg=_badge_bg, fg="#FFFFFF", width=3, padx=4,
                                      cursor="hand2")
                    _badge.pack(side="left", padx=(0, 8))
                    tk.Label(_rrow_f, text=_rtitle,
                             font=("Helvetica Neue", 9),
                             bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"],
                             anchor="w", width=24).pack(side="left")
                    _bar_w   = max(4, int(120 * _rval / global_max)) if global_max > 0 else 4
                    _bar_clr = _entry_clr if _abs_rank < 3 else NEUTRAL
                    _bar = tk.Frame(_rrow_f, bg=_bar_clr, height=13, width=_bar_w,
                                    cursor="hand2")
                    _bar.pack(side="left", padx=(0, 5))
                    _bar.pack_propagate(False)
                    tk.Label(_rrow_f, text=f"{_rval:,.2f} \u20ac",
                             font=("Helvetica Neue", 9, "bold"),
                             bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(side="left")
                    # Hover-Bindings auf Badge (Platznummer) und Balken
                    for _hw in (_badge, _bar):
                        _hw.bind("<Enter>",
                                 lambda e, t=_rtitle, a=_avg, cn=_cn_tip, cc=_cc_tip, cp=_cpct:
                                     (_cancel_hide(), _show_rank_tip(e, t, a, cn, cc, cp)))
                        _hw.bind("<Leave>", _hide_rank_tip)

            if _top20:
                _rank_max   = _top20[0][1]
                _cols_frame = tk.Frame(_rank_inner, bg=T["BG_CARD"])
                _cols_frame.pack(fill="x")
                _col_left  = tk.Frame(_cols_frame, bg=T["BG_CARD"])
                _col_left.pack(side="left", fill="both", expand=True, padx=(0, 12))
                _col_right = tk.Frame(_cols_frame, bg=T["BG_CARD"])
                _col_right.pack(side="left", fill="both", expand=True)
                _build_rank_col(_col_left,  _top20[:10], 0,  _rank_max)
                _build_rank_col(_col_right, _top20[10:], 10, _rank_max)
            else:
                tk.Label(_rank_inner, text="Keine Ausgabendaten vorhanden.",
                         font=("Helvetica Neue", 9), bg=T["BG_CARD"],
                         fg=T["TEXT_MUTED"]).pack(anchor="w")

            # ── Notizen-Übersicht ─────────────────────────────────────────────────
            _DE_MONTHS = ["", "Januar", "Februar", "März", "April", "Mai", "Juni",
                          "Juli", "August", "September", "Oktober", "November", "Dezember"]
            # Alle Monate im Filter + alle Monate die nur Notizen haben durchsuchen
            _all_note_keys = set(sorted_keys)
            if year_filter is not None:
                _all_note_keys |= {k for k in self.data
                                   if not k.startswith("year_") and k.startswith(year_filter)}
            else:
                _all_note_keys |= {k for k in self.data if not k.startswith("year_")}
            _note_entries = []
            for _nk in sorted(_all_note_keys):
                _ntxt = self.data.get(_nk, {}).get("notes", "").strip()
                if _ntxt:
                    _nparts = _nk.split("-")
                    _nyear, _nmon = int(_nparts[0]), int(_nparts[1])
                    _note_entries.append((_nk, _DE_MONTHS[_nmon], _nyear, _ntxt))

            if _note_entries:
                tk.Frame(_cp, bg=T["BORDER"], height=1).pack(fill="x", padx=26, pady=(14, 6))
                tk.Label(_cp, text="📝  Notizen",
                         font=("Helvetica Neue", 14, "bold"),
                         bg=T["BG_APP"], fg=T["TEXT_PRIMARY"]).pack(anchor="w", padx=26, pady=(0, 2))
                tk.Label(_cp,
                         text=f"{len(_note_entries)} Notiz{'en' if len(_note_entries) != 1 else ''} im gewählten Zeitraum",
                         font=("Helvetica Neue", 8),
                         bg=T["BG_APP"], fg=T["TEXT_MUTED"]).pack(anchor="w", padx=26, pady=(0, 8))

                _notes_card = tk.Frame(_cp, bg=T["BG_CARD"],
                                       highlightthickness=1, highlightbackground=T["BORDER"])
                _notes_card.pack(fill="x", padx=20, pady=(0, 16))
                tk.Frame(_notes_card, bg=NEUTRAL, height=3).pack(fill="x")

                _notes_inner = tk.Frame(_notes_card, bg=T["BG_CARD"])
                _notes_inner.pack(fill="x", padx=16, pady=12)

                _hdr_row = tk.Frame(_notes_inner, bg=T["BG_CARD"])
                _hdr_row.pack(fill="x", pady=(0, 6))
                tk.Label(_hdr_row, text="Notizen",
                         font=("Helvetica Neue", 13, "bold"),
                         bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(side="left")
                tk.Label(_hdr_row, text=f"  {len(_note_entries)} Einträge",
                         font=("Helvetica Neue", 9),
                         bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(side="left")
                tk.Frame(_notes_inner, bg=T["BORDER_LIGHT"], height=1).pack(fill="x", pady=(0, 10))

                # Kacheln: volle Breite, 3 Spalten gleichmäßig verteilt
                _TILE_H   = 72
                _TILE_GAP = 8
                _COLS     = 3

                _tiles_wrap = tk.Frame(_notes_inner, bg=T["BG_CARD"])
                _tiles_wrap.pack(fill="x", pady=(4, 0))

                _shown = [0]

                def _open_note_popup(nname, nyear, ntxt):
                    _nw = tk.Toplevel(self)
                    _nw.title(f"Notiz – {nname} {nyear}")
                    _nw.configure(bg=T["BG_CARD"])
                    _nw.resizable(True, True)
                    _nw.grab_set()
                    try:
                        _nx = self.winfo_rootx() + (self.winfo_width()  - 520) // 2
                        _ny = self.winfo_rooty() + (self.winfo_height() - 380) // 2
                        _nw.geometry(f"520x380+{_nx}+{_ny}")
                    except Exception:
                        _nw.geometry("520x380")
                    _phdr = tk.Frame(_nw, bg=T["BG_CARD"])
                    _phdr.pack(fill="x", padx=16, pady=(14, 6))
                    tk.Label(_phdr, text=f"{nname} {nyear}",
                             font=("Helvetica Neue", 13, "bold"),
                             bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(anchor="w")
                    tk.Frame(_nw, bg=T["BORDER_LIGHT"], height=1).pack(
                        fill="x", padx=16, pady=(0, 8))
                    _ptxt = tk.Text(_nw, font=("Helvetica Neue", 10),
                                    bg=T["BG_INPUT"], fg=T["TEXT_PRIMARY"],
                                    relief="flat", wrap="word", padx=10, pady=8)
                    _ptxt.pack(fill="both", expand=True, padx=16, pady=(0, 8))
                    _ptxt.insert("1.0", ntxt)
                    _ptxt.config(state="disabled")
                    _pb = tk.Frame(_nw, bg=T["BG_CARD"])
                    _pb.pack(fill="x", padx=16, pady=(0, 12))
                    tk.Button(_pb, text="Schliessen",
                              bg=T["BG_INPUT"], fg=T["TEXT_LABEL"], relief="flat",
                              padx=12, pady=4, command=_nw.destroy).pack(side="right")

                def _make_tile(row_frame, col_idx, nm2, ny2, nt2):
                    _tile = tk.Frame(row_frame, bg=T["BG_INPUT"],
                                     highlightthickness=1, highlightbackground=T["BORDER"],
                                     cursor="hand2",
                                     width=1, height=_TILE_H)
                    _tile.pack_propagate(False)
                    _tile.grid(row=0, column=col_idx, sticky="nsew",
                               padx=_TILE_GAP // 2, pady=_TILE_GAP // 2)
                    _ml = tk.Label(_tile, text=f"{nm2} {ny2}",
                                   font=("Helvetica Neue", 9, "bold"),
                                   bg=T["BG_INPUT"], fg=T["TEXT_PRIMARY"], anchor="w")
                    _ml.pack(fill="x", padx=10, pady=(10, 2))
                    _prev = (nt2.split("\n")[0])[:55]
                    if len(nt2.split("\n")[0]) > 55:
                        _prev += "…"
                    _pl = tk.Label(_tile, text=_prev,
                                   font=("Helvetica Neue", 9),
                                   bg=T["BG_INPUT"], fg=T["TEXT_MUTED"],
                                   anchor="w", justify="left")
                    _pl.pack(fill="x", padx=10)
                    _tws = [_tile, _ml, _pl]
                    def _enter(ev, ws=_tws, bh=T["BG_HOVER"]):
                        for w in ws:
                            try: w.config(bg=bh)
                            except Exception: pass
                    def _leave(ev, ws=_tws, bn=T["BG_INPUT"]):
                        for w in ws:
                            try: w.config(bg=bn)
                            except Exception: pass
                    for w in _tws:
                        w.bind("<Enter>", _enter)
                        w.bind("<Leave>", _leave)
                        w.bind("<Button-1>", lambda ev, n=nm2, y=ny2, t=nt2:
                               _open_note_popup(n, y, t))

                def _render_next_batch(count):
                    start  = _shown[0]
                    actual = min(count, len(_note_entries) - start)
                    for batch_start in range(0, actual, _COLS):
                        batch = _note_entries[start + batch_start :
                                              start + batch_start + _COLS]
                        _row_f = tk.Frame(_tiles_wrap, bg=T["BG_CARD"])
                        _row_f.pack(fill="x", pady=(_TILE_GAP // 2, 0))
                        for c in range(_COLS):
                            _row_f.columnconfigure(c, weight=1, minsize=1)
                        for col_i, (_nk2, _nm2, _ny2, _nt2) in enumerate(batch):
                            _make_tile(_row_f, col_i, _nm2, _ny2, _nt2)
                        # Leere Slots mit unsichtbaren Platzhaltern füllen
                        for empty_col in range(len(batch), _COLS):
                            _ph = tk.Frame(_row_f, bg=T["BG_CARD"], width=1, height=1)
                            _ph.pack_propagate(False)
                            _ph.grid(row=0, column=empty_col, sticky="nsew",
                                     padx=_TILE_GAP // 2, pady=_TILE_GAP // 2)
                    _shown[0] = start + actual

                _render_next_batch(6)

                # ▼-Button
                _more_cont = [None]

                def _refresh_more_btn():
                    if _more_cont[0]:
                        try: _more_cont[0].destroy()
                        except Exception: pass
                        _more_cont[0] = None
                    if _shown[0] < len(_note_entries):
                        _mc = tk.Frame(_notes_inner, bg=T["BG_CARD"])
                        _mc.pack(pady=(8, 0))
                        _more_cont[0] = _mc
                        def _show_more():
                            _render_next_batch(6)
                            _refresh_more_btn()
                        tk.Button(_mc, text="▼  Weitere anzeigen",
                                  font=("Helvetica Neue", 10, "bold"),
                                  bg=T["BG_INPUT"], fg=T["TEXT_MUTED"],
                                  relief="flat", cursor="hand2",
                                  activebackground=T["BG_HOVER"],
                                  padx=20, pady=6,
                                  command=_show_more).pack()

                _refresh_more_btn()

            # ── Ausgaben-Treemap ──────────────────────────────────────────────────
            tk.Frame(_cp, bg=T["BORDER"], height=1).pack(fill="x", padx=26, pady=(14, 6))
            tk.Label(_cp, text="Ausgaben-Treemap",
                     font=("Helvetica Neue", 14, "bold"),
                     bg=T["BG_APP"], fg=T["TEXT_PRIMARY"]).pack(anchor="w", padx=26, pady=(0, 2))
            tk.Label(_cp,
                     text="Rechteckgröße = Gesamtbetrag  \u2022  Je größer das Feld, desto dominanter die Kategorie",
                     font=("Helvetica Neue", 8),
                     bg=T["BG_APP"], fg=T["TEXT_MUTED"]).pack(anchor="w", padx=26, pady=(0, 8))

            tree_card = tk.Frame(_cp, bg=T["BG_CARD"],
                                 highlightthickness=1, highlightbackground=T["BORDER"])
            tree_card.pack(fill="x", padx=20, pady=(0, 8))
            tk.Frame(tree_card, bg=NEUTRAL, height=3).pack(fill="x")
            tree_host = tk.Frame(tree_card, bg=T["BG_CARD"])
            tree_host.pack(fill="x", padx=4, pady=4)

            _tree_items = [
                (total_ess, self._cc("essenz"),       self._cn("essenz"),       "essenz"),
                (total_fre, self._cc("freizeit"),     self._cn("freizeit"),     "freizeit"),
                (total_aut, self._cc("auto"),         self._cn("auto"),         "auto"),
                (total_ver, self._cc("versicherung"), self._cn("versicherung"), "versicherung"),
                (total_fix, self._cc("fixkosten"),    self._cn("fixkosten"),    "fixkosten"),
                *[(total_custom_all[ck], self._cc(ck), self._cn(ck), ck)
                  for ck in self._custom_cat_order if total_custom_all.get(ck, 0) > 0],
            ]
            _tree_items = sorted([(v, c, n, k) for v, c, n, k in _tree_items if v > 0],
                                 key=lambda x: x[0], reverse=True)

            fig_tree = None
            if _tree_items:
                _total_tree = sum(v for v, *_ in _tree_items)

                def _sq(items, x, y, w, h):
                    """Binärer Split-Treemap-Algorithmus."""
                    if not items:
                        return []
                    if len(items) == 1:
                        return [(x, y, w, h, items[0])]
                    total = sum(v for v, *_ in items)
                    if total == 0:
                        return []
                    s, split = 0, 0
                    half = total / 2
                    for i, item in enumerate(items):
                        s += item[0]
                        split = i + 1
                        if s >= half:
                            break
                    left, right = items[:split], items[split:]
                    ls = sum(v for v, *_ in left)
                    result = []
                    if w >= h:
                        lw = w * ls / total
                        result += _sq(left, x, y, lw, h)
                        if right:
                            result += _sq(right, x + lw, y, w - lw, h)
                    else:
                        lh = h * ls / total
                        result += _sq(left, x, y, w, lh)
                        if right:
                            result += _sq(right, x, y + lh, w, h - lh)
                    return result

                rects = _sq(_tree_items, 0.0, 0.0, 1.0, 1.0)

                fig_tree, ax_tree = plt.subplots(figsize=(13.5, 3.8), facecolor=T["BG_CARD"])
                ax_tree.set_facecolor(T["BG_CARD"])
                ax_tree.set_xlim(0, 1)
                ax_tree.set_ylim(0, 1)
                ax_tree.axis("off")
                PAD = 0.003
                for rx, ry, rw, rh, (val, clr, name, key) in rects:
                    ix, iy = rx + PAD, ry + PAD
                    iw, ih = max(0, rw - 2*PAD), max(0, rh - 2*PAD)
                    # Hauptkachel – keine Umrandung, volle Deckkraft
                    ax_tree.add_patch(matplotlib.patches.Rectangle(
                        (ix, iy), iw, ih,
                        facecolor=clr, edgecolor='none', linewidth=0, zorder=1))
                    pct = val / _total_tree * 100
                    if rw > 0.07 and rh > 0.06:
                        # Heller Glanzstreifen oben
                        ax_tree.add_patch(matplotlib.patches.Rectangle(
                            (ix, iy + ih * 0.83), iw, ih * 0.17,
                            facecolor='#FFFFFF', edgecolor='none', alpha=0.10, zorder=2))
                        # Dunkler Streifen unten (Textbereich)
                        ax_tree.add_patch(matplotlib.patches.Rectangle(
                            (ix, iy), iw, ih * 0.44,
                            facecolor='#000000', edgecolor='none', alpha=0.18, zorder=2))
                        fs_n = max(7, min(13, int(rw * 64)))
                        fs_v = max(6, min(10, int(rw * 46)))
                        ax_tree.text(rx + rw/2, ry + rh * 0.64, name,
                                     ha="center", va="center", fontsize=fs_n,
                                     color="#FFFFFF", fontweight="bold",
                                     clip_on=True, zorder=3)
                        ax_tree.text(rx + rw/2, ry + rh * 0.33,
                                     f"{val:,.0f}\u20ac",
                                     ha="center", va="center", fontsize=fs_v,
                                     color="#FFFFFF", alpha=0.93, clip_on=True, zorder=3)
                        ax_tree.text(rx + rw/2, ry + rh * 0.13,
                                     f"{pct:.1f}%",
                                     ha="center", va="center",
                                     fontsize=max(5, fs_v - 1),
                                     color="#FFFFFF", alpha=0.75, clip_on=True, zorder=3)
                    elif rw > 0.035 and rh > 0.035:
                        ax_tree.text(rx + rw/2, ry + rh * 0.60, name,
                                     ha="center", va="center",
                                     fontsize=max(6, int(rw * 48)),
                                     color="#FFFFFF", fontweight="bold",
                                     clip_on=True, zorder=3)
                        ax_tree.text(rx + rw/2, ry + rh * 0.24,
                                     f"{pct:.0f}%",
                                     ha="center", va="center",
                                     fontsize=max(5, int(rw * 36)),
                                     color="#FFFFFF", alpha=0.80, clip_on=True, zorder=3)
                    elif rw > 0.018 and rh > 0.018:
                        ax_tree.text(rx + rw/2, ry + rh/2, name,
                                     ha="center", va="center",
                                     fontsize=max(5, int(rw * 40)),
                                     color="#FFFFFF", fontweight="bold",
                                     clip_on=True, zorder=3)
                fig_tree.tight_layout(pad=0.0)
                cv_tree = FigureCanvasTkAgg(fig_tree, master=tree_host)
                cv_tree.get_tk_widget().pack(fill="x")
                cv_tree.draw()
                _open_figs.append(fig_tree)

            win.after(50, lambda: _ov_canvas.yview_moveto(0.0))

        # ── Jahresfilter-Schaltflächen verdrahten ─────────────────────────────
        def _switch_year(yf):
            _render_content(yf)

        _yf_btns["all"].config(command=lambda: _switch_year(None))
        for _yr in all_years:
            _yf_btns[_yr].config(command=lambda y=_yr: _switch_year(y))

        _render_content(_active_yf[0])

        # ── Cleanup und Schliessen-Schaltfläche ───────────────────────────────
        def _cleanup(e=None):
            if _active_cv[0] is not None:
                try: plt.close(_active_cv[0].figure)
                except Exception: pass
            for _fig in _open_figs:
                try: plt.close(_fig)
                except Exception: pass
        win.bind("<Destroy>", _cleanup, add=True)

        tk.Button(_ov_inner, text="Schliessen",
                  font=("Helvetica Neue", 10),
                  bg=T["BG_INPUT"], fg=T["TEXT_LABEL"],
                  relief="flat", bd=0, cursor="hand2", padx=18, pady=6,
                  command=win.destroy).pack(pady=10)

    # ── Kategorie-Drilldown (Klick auf Tortenstück) ───────────────────────────
    def _open_cat_drilldown(self, cat_key, cat_name, year_filter=None):
        T = self._T()
        all_keys = sorted(k for k in self.data if not k.startswith("year_"))
        if year_filter:
            all_keys = [k for k in all_keys if k.startswith(year_filter)]
        months_lbl, values = [], []

        def _has_real_data(md):
            for cat in (["income", "essenz", "freizeit", "auto", "versicherung"]
                        + self._custom_cat_order):
                for row in md.get(cat, []):
                    if self._parse_amount(row.get("amount", "")) > 0:
                        return True
            return False

        for key in all_keys:
            md   = self.data[key]
            if not _has_real_data(md):
                continue
            year = int(key.split("-")[0])
            yd   = self.data.get(f"year_{year}", {})
            month_num = int(key.split("-")[1])
            year_from_mo = yd.get("fixkosten_from_month", 1)
            # Month-specific fixkosten override (set via "nur diesen Monat")
            if md.get("fixkosten_month_only") or "fixkosten" in md:
                fix_rows = md.get("fixkosten", [])
            elif month_num < year_from_mo:
                # Monat liegt vor dem Gültigkeitsdatum → keine Fixkosten aus year_key
                fix_rows = []
            else:
                fix_rows = yd.get("fixkosten", [])
            _dd_color_to_cat = self._build_fix_color_to_cat()
            fix_by_cat = {cat: 0.0 for cat in list(FIX_COLOR_TO_CAT.values()) + self._custom_cat_order}
            for fr in fix_rows:
                amt = self._parse_amount(fr["amount"]) / 12.0
                clr = fr.get("color", FIXKOSTEN_CLR)
                cat = _dd_color_to_cat.get(clr, "fixkosten")
                fix_by_cat[cat] += amt
            try:
                y, m = key.split("-")
                lbl = f"{MONTHS_DE[int(m)-1][:3]} {y[2:]}"
            except Exception:
                lbl = key

            if cat_key == "savings":
                inc = sum(self._parse_amount(r["amount"]) for r in md.get("income", []))
                out = sum(
                    sum(self._parse_amount(r["amount"]) for r in md.get(c, []))
                    for c in ["essenz", "freizeit", "auto", "versicherung"]
                ) + sum(fix_by_cat.values())
                for ck in self._custom_cat_order:
                    out += sum(self._parse_amount(r["amount"]) for r in md.get(ck, []))
                val = max(0.0, inc - out)
            elif cat_key == "fixkosten":
                val = fix_by_cat.get("fixkosten", 0.0)
            elif cat_key in ("essenz", "freizeit", "auto", "versicherung"):
                val = (sum(self._parse_amount(r["amount"]) for r in md.get(cat_key, []))
                       + fix_by_cat.get(cat_key, 0.0))
            else:
                val = (sum(self._parse_amount(r["amount"])
                           for r in md.get(cat_key, [])
                           if self._parse_amount(r["amount"]) > 0)
                       + fix_by_cat.get(cat_key, 0.0))

            months_lbl.append(lbl)
            values.append(val)

        if not any(v > 0 for v in values):
            tk.messagebox.showinfo(cat_name, "Keine Daten für diese Kategorie vorhanden.")
            return

        # ── Bestehendes Fenster wiederverwenden oder neues öffnen ─────────────
        pop_exists = (hasattr(self, '_drilldown_pop') and
                      self._drilldown_pop is not None and
                      self._drilldown_pop.winfo_exists())

        if pop_exists:
            pop = self._drilldown_pop
            pop.title(f"{cat_name} \u2013 Monatsverlauf")
            # Altes Diagramm schließen und Chart-Frame leeren
            if getattr(self, '_drilldown_fig', None) is not None:
                try:
                    plt.close(self._drilldown_fig)
                except Exception:
                    pass
                self._drilldown_fig = None
            for w in self._drilldown_chart_frame.winfo_children():
                w.destroy()
        else:
            pop = tk.Toplevel(self)
            self._drilldown_pop = pop
            pop.title(f"{cat_name} \u2013 Monatsverlauf")
            try:
                pop.geometry(self._drilldown_geometry or "560x360")
            except Exception:
                self._drilldown_geometry = None
                pop.geometry("560x360")
            pop.configure(bg=T["BG_CARD"])
            # Kein grab_set() – damit Klicks auf neue Kategorien möglich bleiben

            def _track_geometry(e=None):
                try:
                    geom = pop.geometry()
                    if geom and "x" in geom:
                        self._drilldown_geometry = geom
                except Exception:
                    pass
            pop.bind("<Configure>", _track_geometry)

            # Chart-Frame (wird bei Kategorie-Wechsel geleert und neu befüllt)
            self._drilldown_chart_frame = tk.Frame(pop, bg=T["BG_CARD"])
            self._drilldown_chart_frame.pack(fill="both", expand=True, padx=6, pady=(6, 0))

            tk.Button(pop, text="Schliessen", font=("Helvetica Neue", 9),
                      bg=T["BG_INPUT"], fg=T["TEXT_LABEL"],
                      relief="flat", bd=0, cursor="hand2", padx=12, pady=4,
                      command=pop.destroy).pack(pady=(4, 8))

            def _on_destroy(e=None):
                if e is not None and e.widget is not pop:
                    return
                if getattr(self, '_drilldown_fig', None) is not None:
                    try:
                        plt.close(self._drilldown_fig)
                    except Exception:
                        pass
                    self._drilldown_fig = None
                self._drilldown_pop = None
            pop.bind("<Destroy>", _on_destroy)

        # ── Neues Diagramm erzeugen und in chart_frame einbetten ──────────────
        clr = self._cc(cat_key)
        fig, ax = plt.subplots(figsize=(5.8, 3.2), facecolor=T["BG_CARD"])
        self._drilldown_fig = fig
        ax.set_facecolor(T["BG_CARD"])

        x = list(range(len(months_lbl)))
        ax.bar(x, values, color=clr, alpha=0.88, edgecolor="none", width=0.65)
        ax.set_xticks(x)
        ax.set_xticklabels(months_lbl, rotation=35, ha="right",
                           fontsize=8, color=T["TEXT_MUTED"])
        ax.set_title(f"{cat_name} \u2013 Monatsverlauf",
                     color=T["TEXT_PRIMARY"], fontsize=10, fontweight="bold", pad=8)
        ax.set_ylabel("\u20ac", color=T["TEXT_MUTED"], fontsize=9)

        max_v = max(values) if values else 1
        for xi, v in enumerate(values):
            if v > 0:
                ax.text(xi, v + max_v * 0.025, f"{v:,.0f}\u20ac",
                        ha="center", va="bottom", fontsize=6.5,
                        color=T["TEXT_PRIMARY"], fontweight="bold")

        nonzero = [v for v in values if v > 0]
        total_sum = sum(nonzero)
        if nonzero:
            avg = total_sum / len(nonzero)
            ax.axhline(avg, color=clr, linewidth=1.3, linestyle="--",
                       alpha=0.65, label=f"\u00d8 {avg:,.0f}\u20ac / Monat")
            ax.legend(fontsize=8, frameon=False, labelcolor=T["TEXT_LABEL"])
            ax.text(0.99, 0.98, f"Gesamt: {total_sum:,.0f}\u20ac",
                    transform=ax.transAxes, ha="right", va="top",
                    fontsize=9, color="#FFFFFF", fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.4",
                              facecolor=clr, alpha=0.82, edgecolor="none"))

        for sp in ["top", "right"]:
            ax.spines[sp].set_visible(False)
        for sp in ["left", "bottom"]:
            ax.spines[sp].set_color(T["BORDER"])
        ax.tick_params(colors=T["TEXT_MUTED"])
        fig.tight_layout(pad=1.8)

        cv = FigureCanvasTkAgg(fig, master=self._drilldown_chart_frame)
        cv.get_tk_widget().pack(fill="both", expand=True)
        cv.draw()

    # ── CSV-Export ────────────────────────────────────────────────────────────
    def _export_csv(self):
        import csv
        import tkinter.filedialog as fd

        filepath = fd.asksaveasfilename(
            title="CSV-Export speichern",
            defaultextension=".csv",
            filetypes=[("CSV-Datei", "*.csv"), ("Alle Dateien", "*.*")],
            initialfile="finanz_export.csv",
        )
        if not filepath:
            return

        def _n(v):
            """Betrag als deutsche Dezimalzahl, z.B. 1234,56"""
            return f"{v:.2f}".replace(".", ",")

        def _pct(v):
            return f"{v:.1f}".replace(".", ",") + " %"

        # Ausgabe-Kategorien in gleicher Reihenfolge wie im Programm.
        # Neue benutzerdefinierte Kategorien hängen sich automatisch ans Ende.
        exp_cats = ["essenz", "freizeit", "auto", "versicherung", "fixkosten"] \
                   + self._custom_cat_order

        try:
            with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")

                # Spaltenkopfzeile – bleibt immer gleich, egal wie viele
                # Kategorien oder Monate hinzukommen.
                w.writerow(["Abschnitt", "Kategorie", "Bezeichnung",
                            "Betrag (EUR)", "Summe (EUR)"])
                w.writerow([])

                # ══════════════════════════════════════════════════════════
                # MONATSDATEN  –  ein Block pro Monat, Aufbau wie im Programm
                # ══════════════════════════════════════════════════════════
                for key in sorted(k for k in self.data if not k.startswith("year_")):
                    try:
                        year_str, month_str = key.split("-")
                    except ValueError:
                        continue
                    md         = self.data[key]
                    month_name = f"{MONTHS_DE[int(month_str)-1]} {year_str}"

                    # Fixkosten-Monatsanteile berechnen – identisch zur App-Logik:
                    # month_only und fixkosten_from_month werden berücksichtigt.
                    yd          = self.data.get(f"year_{year_str}", {})
                    _csv_ctc    = self._build_fix_color_to_cat()
                    _mo_num     = int(month_str)
                    _yr_from_mo = yd.get("fixkosten_from_month", 1)
                    if md.get("fixkosten_month_only") or "fixkosten" in md:
                        _csv_fix_rows = md.get("fixkosten", [])
                    elif _mo_num < _yr_from_mo:
                        _csv_fix_rows = []
                    else:
                        _csv_fix_rows = yd.get("fixkosten", [])
                    fix_by_cat = {cat: [] for cat in list(FIX_COLOR_TO_CAT.values()) + self._custom_cat_order}
                    for fr in _csv_fix_rows:
                        amt = self._parse_amount(fr["amount"]) / 12.0
                        clr = fr.get("color", FIXKOSTEN_CLR)
                        cat = _csv_ctc.get(clr, "fixkosten")
                        if cat not in fix_by_cat:
                            fix_by_cat[cat] = []
                        fix_by_cat[cat].append((fr.get("title", ""), amt))

                    # ── Monats-Header ──────────────────────────────────────
                    w.writerow([f"=== {month_name.upper()} ===", "", "", "", ""])

                    # ── Einkommen ──────────────────────────────────────────
                    inc_rows  = [(r.get("title", ""),
                                  self._parse_amount(r.get("amount", 0)))
                                 for r in md.get("income", [])
                                 if self._parse_amount(r.get("amount", 0)) != 0]
                    inc_total = 0.0
                    if inc_rows:
                        w.writerow(["", self._cn("income"), "", "", ""])
                        for title, amt in inc_rows:
                            w.writerow(["", "", title, _n(amt), ""])
                            inc_total += amt
                        w.writerow(["", "", "Summe", "", _n(inc_total)])
                        w.writerow([])

                    # ── Ausgabe-Kategorien ─────────────────────────────────
                    out_total = 0.0
                    for cat_key in exp_cats:
                        mo_entries  = [(r.get("title", ""),
                                        self._parse_amount(r.get("amount", 0)))
                                       for r in md.get(cat_key, [])
                                       if self._parse_amount(r.get("amount", 0)) != 0]
                        fix_entries = fix_by_cat.get(cat_key, [])
                        if not mo_entries and not fix_entries:
                            continue

                        w.writerow(["", self._cn(cat_key), "", "", ""])
                        cat_total = 0.0
                        for title, amt in mo_entries:
                            w.writerow(["", "", title, _n(amt), ""])
                            cat_total += amt
                        for title, amt in fix_entries:
                            # Fixkosten-Anteil klar kennzeichnen
                            w.writerow(["", "", f"{title}  [Fixkostenanteil]",
                                        _n(amt), ""])
                            cat_total += amt
                        w.writerow(["", "", "Summe", "", _n(cat_total)])
                        w.writerow([])
                        out_total += cat_total

                    # ── Monatszusammenfassung (spiegelt die App-Ansicht) ───
                    savings = inc_total - out_total
                    w.writerow(["", f"--- Zusammenfassung {month_name} ---",
                                "", "", ""])
                    w.writerow(["", "", self._cn("income"),    "", _n(inc_total)])
                    w.writerow(["", "", "Gesamtausgaben",      "", _n(out_total)])
                    if savings >= 0:
                        w.writerow(["", "", self._cn("savings"), "", _n(savings)])
                        if inc_total > 0:
                            w.writerow(["", "", "Sparquote", "",
                                        _pct(savings / inc_total * 100)])
                    else:
                        w.writerow(["", "", "Defizit", "", _n(abs(savings))])

                    w.writerow([])
                    w.writerow([])   # Leerzeile als Monatstrennlinie

                # ══════════════════════════════════════════════════════════
                # FIXKOSTEN (JÄHRLICH)  –  Rohdaten der Jahrestabelle
                # ══════════════════════════════════════════════════════════
                w.writerow(["=== FIXKOSTEN (JÄHRLICH) ===", "", "", "", ""])
                w.writerow(["", "Kategorie", "Bezeichnung",
                            "Jahresbetrag (EUR)", "Monatlich (EUR, /12)"])

                _ann_ctc = self._build_fix_color_to_cat()
                for key in sorted(k for k in self.data if k.startswith("year_")):
                    year_str = key.replace("year_", "")
                    fix_rows = self.data[key].get("fixkosten", [])
                    if not fix_rows:
                        continue
                    w.writerow([])
                    w.writerow(["", f"--- {year_str} ---", "", "", ""])
                    year_total = 0.0
                    for row in fix_rows:
                        amt = self._parse_amount(row.get("amount", 0))
                        if amt == 0:
                            continue
                        fix_clr  = row.get("color", FIXKOSTEN_CLR)
                        cat_key  = _ann_ctc.get(fix_clr, "fixkosten")
                        w.writerow(["", self._cn(cat_key), row.get("title", ""),
                                    _n(amt), _n(amt / 12)])
                        year_total += amt
                    w.writerow(["", "", "Jahresgesamtbetrag",
                                _n(year_total), _n(year_total / 12)])

            tk.messagebox.showinfo(
                "CSV-Export",
                f"Export erfolgreich gespeichert:\n{filepath}\n\n"
                "Tipp: In Excel \u2192 Daten \u2192 Aus Text/CSV importieren\n"
                "(Trennzeichen: Semikolon, Kodierung: UTF-8)"
            )
        except Exception as exc:
            tk.messagebox.showerror("CSV-Export Fehler", str(exc))

    # ── Backup-System ─────────────────────────────────────────────────────────
    def _get_current_settings_dict(self):
        """Sammelt alle aktuellen Settings als Dict (wie destroy es tut)."""
        try:
            _goal = float(self._savings_goal_var.get())
        except (ValueError, TypeError):
            _goal = 0
        return {
            "dark_mode":           self.dark_mode,
            "last_year":           self.current_year.get(),
            "last_month":          self.current_month.get(),
            "overview_chart":      self.overview_chart,
            "cat_settings":        self._cat_settings,
            "custom_cat_order":    self._custom_cat_order,
            "savings_goal_pct":    _goal,
            "drilldown_geometry":  self._drilldown_geometry,
            "overview_geometry":   self._overview_geometry,
            "main_geometry":       self._main_geometry,
            "search_geometry":     self._search_geometry,
            "search_exact_amount": self._search_exact_amount,
            "search_hide_empty":   self._search_hide_empty,
        }

    def _create_backup(self, btype="manual", filepath=None):
        """Erstellt ein Backup-Bundle (Daten + Einstellungen) als eine JSON-Datei.

        btype:    "auto" oder "manual"
        filepath: wenn angegeben, wird dort gespeichert (Speichern unter);
                  sonst im backups/-Ordner neben der .py-Datei.
        Gibt den Dateipfad zurück oder None bei Fehler.
        """
        try:
            bundle = {
                "created":  datetime.now().isoformat(timespec="seconds"),
                "type":     btype,
                "data":     self.data,
                "settings": self._get_current_settings_dict(),
            }
            if filepath is None:
                # Backups-Ordner anlegen
                backup_dir = BACKUP_DIR
                os.makedirs(backup_dir, exist_ok=True)

                ts   = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                name = f"{ts}_{btype}.json"
                filepath = os.path.join(backup_dir, name)

                # Rotation: max. MAX_AUTO_BACKUPS Auto-Backups behalten
                if btype == "auto":
                    self._rotate_auto_backups(backup_dir)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(bundle, f, ensure_ascii=False, indent=2)
            return filepath
        except Exception as exc:
            print(f"[Backup] Fehler beim Erstellen: {exc}")
            return None

    def _rotate_auto_backups(self, backup_dir):
        """Löscht älteste Auto-Backups wenn MAX_AUTO_BACKUPS überschritten wird."""
        try:
            auto_files = sorted([
                os.path.join(backup_dir, f)
                for f in os.listdir(backup_dir)
                if f.endswith("_auto.json")
            ])
            while len(auto_files) >= MAX_AUTO_BACKUPS:
                os.remove(auto_files.pop(0))
        except Exception as exc:
            print(f"[Backup] Rotation fehlgeschlagen: {exc}")

    def _load_backup_bundle(self, filepath):
        """Lädt ein Backup-Bundle und stellt Daten + Einstellungen wieder her."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                bundle = json.load(f)
        except Exception as exc:
            tk.messagebox.showerror("Backup laden",
                                    f"Datei konnte nicht gelesen werden:\n{exc}")
            return

        # Format erkennen: Bundle (mit 'data'-Wrapper) oder rohe Datendatei
        if "data" in bundle and isinstance(bundle["data"], dict):
            data_dict = bundle["data"]
            created   = bundle.get("created", "unbekannt")
        else:
            data_dict = bundle
            created   = "extern / umbenannte Datei"

        months = len([k for k in data_dict if not k.startswith("year_")])
        answer = tk.messagebox.askyesnocancel(
            "Backup wiederherstellen",
            f"Backup vom {created}\n({months} Monate mit Daten)\n\n"
            "Vor dem Laden wird automatisch ein Backup der aktuellen Daten erstellt.\n\n"
            "Jetzt wiederherstellen?"
        )
        if not answer:
            return

        # Aktuellen Stand sichern bevor überschrieben wird
        self._save_month()
        self._create_backup("auto")

        # Daten übernehmen
        self.data = data_dict

        # Alle year_-Keys mit Default-Platzhaltern bereinigen
        for yk in list(self.data.keys()):
            if yk.startswith("year_"):
                fix = self.data[yk].get("fixkosten", [])
                if fix and all(
                    re.match(r'^Fixkosten \d+$', r.get("title", "")) and
                    r.get("amount", "") == "" and
                    r.get("color", FIXKOSTEN_CLR) == FIXKOSTEN_CLR
                    for r in fix
                ):
                    del self.data[yk]["fixkosten"]
                    if not self.data[yk]:
                        del self.data[yk]

        # Zeilennamen aus dem letzten importierten Monat auf alle späteren
        # Monate im Datensatz übertragen (Beträge bleiben erhalten).
        all_month_keys = sorted(k for k in self.data if not k.startswith("year_"))
        if all_month_keys:
            src_key = all_month_keys[-1]          # letzter Monat im Backup
            src     = self.data[src_key]
            for key in all_month_keys:
                if key <= src_key:
                    continue                       # nur Monate NACH dem letzten Backup-Monat
                month_data = self.data[key]
                for cat in list(src.keys()):
                    if cat in ("notes", "fixkosten_month_only"):
                        continue
                    src_rows = src.get(cat, [])
                    if not src_rows:
                        continue
                    existing = month_data.get(cat, [])
                    if cat == "fixkosten":
                        # Fixkosten separat behandeln: Farbe aus Quelldaten mitübernehmen,
                        # damit Kategorie-Zuordnungen nach Backup-Restore erhalten bleiben.
                        month_data[cat] = [
                            {"title":  src_rows[i]["title"],
                             "amount": existing[i].get("amount", "") if i < len(existing) else "",
                             "color":  src_rows[i].get("color", FIXKOSTEN_CLR)}
                            for i in range(len(src_rows))
                        ]
                    else:
                        month_data[cat] = [
                            {"title": src_rows[i]["title"],
                             "amount": existing[i]["amount"] if i < len(existing) else ""}
                            for i in range(len(src_rows))
                        ]

        save_data(self.data)

        # Einstellungen übernehmen
        s = bundle.get("settings", {})
        self.dark_mode      = s.get("dark_mode", False)
        self.overview_chart = s.get("overview_chart", "bar")
        for key, defaults in DEFAULT_CAT_SETTINGS.items():
            cat = s.setdefault("cat_settings", {}).setdefault(key, {})
            for field, val in defaults.items():
                cat.setdefault(field, val)
        self._cat_settings      = s.get("cat_settings", {})
        self._custom_cat_order  = s.get("custom_cat_order", [])
        self._custom_cat_order  = [k for k in self._custom_cat_order
                                   if k in self._cat_settings]
        try:
            goal = float(s.get("savings_goal_pct", 0))
        except (ValueError, TypeError):
            goal = 0
        self._savings_goal_var.set(str(int(goal)))
        ly = s.get("last_year");  lm = s.get("last_month")
        if ly is not None:
            self.current_year.set(int(ly))
        if lm is not None:
            self.current_month.set(int(lm))
        save_settings(s)

        # UI neu aufbauen
        plt.close("all")
        for w in self.winfo_children():
            w.destroy()
        self._custom_cards = {}
        self._build_ui()
        self._load_month()

    def _list_backups(self):
        """Gibt Liste von Backup-Infos zurück: [(filepath, created, type, months, size_kb)].
        Erkennt sowohl Bundle-Format (mit 'data'-Wrapper) als auch rohe finanz_daten.json-Dateien."""
        backup_dir = BACKUP_DIR
        if not os.path.isdir(backup_dir):
            return []
        result = []
        for fname in sorted(os.listdir(backup_dir), reverse=True):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(backup_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    b = json.load(f)
                if "data" in b and isinstance(b["data"], dict):
                    # Standard-Backup-Bundle
                    created = b.get("created", "?")
                    btype   = b.get("type", "manuell")
                    months  = len([k for k in b["data"]
                                   if not k.startswith("year_")])
                else:
                    # Rohe Datendatei (finanz_daten.json-Format, extern abgelegt)
                    mtime   = os.path.getmtime(fpath)
                    created = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                    btype   = "extern"
                    months  = len([k for k in b
                                   if not k.startswith("year_")])
                size_kb = max(1, os.path.getsize(fpath) // 1024)
                result.append((fpath, created, btype, months, size_kb))
            except Exception:
                continue
        return result

    def _open_backup_manager(self):
        """Öffnet den Backup-Manager als modales Popup."""
        T   = self._T()
        win = tk.Toplevel(self)
        win.title("Backup-Manager")
        win.geometry("720x480")
        win.resizable(False, True)
        win.configure(bg=T["BG_APP"])
        win.grab_set()

        # ── Kopfzeile ─────────────────────────────────────────────────────────
        hdr = tk.Frame(win, bg=T["BG_CARD"],
                       highlightthickness=1, highlightbackground=T["BORDER"])
        hdr.pack(fill="x")
        tk.Frame(hdr, bg=SAVINGS_CLR, height=3).pack(fill="x")
        hdr_inner = tk.Frame(hdr, bg=T["BG_CARD"])
        hdr_inner.pack(fill="x", padx=16, pady=10)
        tk.Label(hdr_inner, text="\U0001f4be  Backup-Manager",
                 font=("Helvetica Neue", 13, "bold"),
                 bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(side="left")

        backup_dir = BACKUP_DIR
        tk.Label(hdr_inner,
                 text=f"Ordner: {backup_dir}",
                 font=("Helvetica Neue", 8),
                 bg=T["BG_CARD"], fg=T["TEXT_MUTED"]).pack(side="left", padx=(14,0))

        # ── Aktionsleiste ─────────────────────────────────────────────────────
        act = tk.Frame(win, bg=T["BG_APP"])
        act.pack(fill="x", padx=16, pady=10)

        def _btn(parent, text, cmd, primary=False):
            bg = SAVINGS_CLR if primary else T["BG_INPUT"]
            fg = "#FFFFFF"   if primary else T["TEXT_LABEL"]
            return tk.Button(parent, text=text,
                             font=("Helvetica Neue", 9, "bold" if primary else ""),
                             bg=bg, fg=fg, relief="flat", bd=0, cursor="hand2",
                             padx=12, pady=5,
                             activebackground=T["BG_HOVER"],
                             activeforeground=T["TEXT_PRIMARY"],
                             command=cmd)

        def _do_manual_backup():
            self._save_month()
            path = self._create_backup("manual")
            if path:
                tk.messagebox.showinfo("Backup erstellt",
                                       f"Manuelles Backup gespeichert:\n{os.path.basename(path)}")
                _refresh_list()

        def _do_save_as():
            self._save_month()
            path = fd.asksaveasfilename(
                parent=win,
                title="Backup speichern unter …",
                defaultextension=".json",
                filetypes=[("JSON Backup", "*.json"), ("Alle Dateien", "*.*")],
                initialfile=f"finanz_backup_{datetime.now().strftime('%Y-%m-%d')}.json"
            )
            if path:
                result = self._create_backup("manual", filepath=path)
                if result:
                    tk.messagebox.showinfo("Gespeichert",
                                           f"Backup gespeichert:\n{path}")

        def _do_open_extern():
            path = fd.askopenfilename(
                parent=win,
                title="Backup laden …",
                filetypes=[("JSON Backup", "*.json"), ("Alle Dateien", "*.*")]
            )
            if path:
                win.destroy()
                self._load_backup_bundle(path)

        _btn(act, "+ Manuelles Backup",        _do_manual_backup, primary=True).pack(side="left", padx=(0,8))
        _btn(act, "\U0001f4c2 Speichern unter …", _do_save_as).pack(side="left", padx=(0,8))
        _btn(act, "\U0001f4c1 Extern laden …",    _do_open_extern).pack(side="left", padx=(0,8))
        tk.Frame(act, bg=T["BORDER"], width=1).pack(side="left", fill="y", padx=(4,8))
        _btn(act, "\U0001f4e4 CSV-Export …",      self._export_csv).pack(side="left")

        # ── Backup-Liste ──────────────────────────────────────────────────────
        tk.Frame(win, bg=T["BORDER"], height=1).pack(fill="x", padx=16)

        # Spalten-Header
        col_hdr = tk.Frame(win, bg=T["BG_INPUT"])
        col_hdr.pack(fill="x", padx=16, pady=(6,0))
        for text, w in [("Datum / Uhrzeit", 200), ("Typ", 70),
                        ("Monate", 60), ("Größe", 60), ("Aktionen", 200)]:
            tk.Label(col_hdr, text=text,
                     font=("Helvetica Neue", 8, "bold"),
                     bg=T["BG_INPUT"], fg=T["TEXT_MUTED"],
                     width=w//8, anchor="w").pack(side="left", padx=6, pady=4)

        # Scrollbare Liste
        list_outer = tk.Frame(win, bg=T["BG_APP"])
        list_outer.pack(fill="both", expand=True, padx=16, pady=(4,0))
        list_vsb = tk.Scrollbar(list_outer, orient="vertical", bg=T["BG_APP"])
        list_vsb.pack(side="right", fill="y")
        list_canvas = tk.Canvas(list_outer, bg=T["BG_APP"],
                                highlightthickness=0,
                                yscrollcommand=list_vsb.set)
        list_canvas.pack(side="left", fill="both", expand=True)
        list_vsb.config(command=list_canvas.yview)
        list_frame = tk.Frame(list_canvas, bg=T["BG_APP"])
        _lfw = list_canvas.create_window((0,0), window=list_frame, anchor="nw")
        list_frame.bind("<Configure>",
            lambda e: list_canvas.configure(scrollregion=list_canvas.bbox("all")))
        list_canvas.bind("<Configure>",
            lambda e: list_canvas.itemconfig(_lfw, width=e.width))
        def _bm_scroll(e):
            try:
                list_canvas.yview_scroll(int(-1*(e.delta/120)), "units")
            except Exception:
                pass
        win.bind_all("<MouseWheel>", _bm_scroll)

        def _restore_bm_mwheel(e=None):
            if e is not None and e.widget is not win:
                return
            try:
                if hasattr(self, "_global_mousewheel_fn"):
                    self.bind_all("<MouseWheel>", self._global_mousewheel_fn)
            except Exception:
                pass
        win.bind("<Destroy>", _restore_bm_mwheel)

        selected_row = [None]  # halten der aktuell markierten Zeile

        def _refresh_list():
            for w in list_frame.winfo_children():
                w.destroy()
            backups = self._list_backups()
            if not backups:
                tk.Label(list_frame,
                         text="Noch keine Backups vorhanden.",
                         font=("Helvetica Neue", 10),
                         bg=T["BG_APP"], fg=T["TEXT_MUTED"]).pack(pady=30)
                return

            def _sort_key(item):
                return item[1].replace("T", " ")

            manual = sorted(
                [(fp,cr,bt,mo,sz) for fp,cr,bt,mo,sz in backups if bt != "auto"],
                key=_sort_key, reverse=True)
            auto   = sorted(
                [(fp,cr,bt,mo,sz) for fp,cr,bt,mo,sz in backups if bt == "auto"],
                key=_sort_key, reverse=True)

            groups = []
            if manual: groups.append(("⭐  Manuell / Extern", manual))
            if auto:   groups.append(("🔄  Automatisch",      auto))

            for grp_title, grp_items in groups:
                hdr_f = tk.Frame(list_frame, bg=T["BG_APP"])
                hdr_f.pack(fill="x", pady=(8,2))
                tk.Label(hdr_f, text=grp_title,
                         font=("Helvetica Neue", 8, "bold"),
                         bg=T["BG_APP"], fg=T["TEXT_MUTED"]).pack(side="left", padx=4)
                tk.Frame(hdr_f, bg=T["BORDER_LIGHT"], height=1).pack(
                    side="left", fill="x", expand=True, padx=(4,0))

                for (fpath, created, btype, months, size_kb) in grp_items:
                    is_auto   = (btype == "auto")
                    is_extern = (btype == "extern")
                    icon      = "🔄" if is_auto else ("📁" if is_extern else "⭐")
                    type_lbl  = "Auto" if is_auto else ("Extern" if is_extern else "Manuell")
                    type_clr  = T["TEXT_MUTED"] if is_auto else (INCOME_CLR if is_extern else SAVINGS_CLR)

                    row = tk.Frame(list_frame, bg=T["BG_CARD"],
                                   highlightthickness=1,
                                   highlightbackground=T["BORDER_LIGHT"])
                    row.pack(fill="x", pady=2)

                    fname_stem = os.path.splitext(os.path.basename(fpath))[0]
                    cell = tk.Frame(row, bg=T["BG_CARD"])
                    cell.pack(side="left", padx=(10,0), pady=6)
                    tk.Label(cell, text=f"{icon}  {fname_stem}",
                             font=("Helvetica Neue", 9),
                             bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"],
                             anchor="w").pack(anchor="w")
                    tk.Label(cell, text=created,
                             font=("Helvetica Neue", 7),
                             bg=T["BG_CARD"], fg=T["TEXT_MUTED"],
                             anchor="w").pack(anchor="w")
                    tk.Label(row, text=type_lbl,
                             font=("Helvetica Neue", 9, "bold"),
                             bg=T["BG_CARD"], fg=type_clr,
                             width=8, anchor="w").pack(side="left", padx=4)
                    tk.Label(row, text=f"{months} Mo.",
                             font=("Helvetica Neue", 9),
                             bg=T["BG_CARD"], fg=T["TEXT_MUTED"],
                             width=7, anchor="w").pack(side="left", padx=4)
                    tk.Label(row, text=f"{size_kb} KB",
                             font=("Helvetica Neue", 9),
                             bg=T["BG_CARD"], fg=T["TEXT_MUTED"],
                             width=7, anchor="w").pack(side="left", padx=4)

                    # Aktionsbuttons
                    act_fr = tk.Frame(row, bg=T["BG_CARD"])
                    act_fr.pack(side="right", padx=8, pady=4)

                    def _load(p=fpath):
                        win.destroy()
                        self._load_backup_bundle(p)

                    def _preview(p=fpath, c=created, m=months):
                        self._preview_backup(p, c, m, T)

                    def _delete(p=fpath, r=row):
                        if tk.messagebox.askyesno("Backup löschen",
                                                  f"Backup löschen?\n{os.path.basename(p)}"):
                            try:
                                os.remove(p)
                                r.destroy()
                            except Exception as exc:
                                tk.messagebox.showerror("Fehler", str(exc))

                    for txt, cmd, fg_c in [
                        ("Laden",    _load,    INCOME_CLR),
                        ("Vorschau", _preview, T["TEXT_LABEL"]),
                        ("Löschen",  _delete,  DEFICIT_CLR),
                    ]:
                        tk.Button(act_fr, text=txt,
                                  font=("Helvetica Neue", 8),
                                  bg=T["BG_INPUT"], fg=fg_c,
                                  relief="flat", bd=0, cursor="hand2",
                                  padx=8, pady=6,
                                  activebackground=T["BG_HOVER"],
                                  activeforeground=fg_c,
                                  command=cmd).pack(side="left", padx=2)

        _refresh_list()

        # ── Fusszeile ─────────────────────────────────────────────────────────
        foot = tk.Frame(win, bg=T["BG_APP"])
        foot.pack(fill="x", padx=16, pady=10)
        tk.Label(foot,
                 text=f"Max. {MAX_AUTO_BACKUPS} Auto-Backups werden aufbewahrt. "
                      "Manuelle Backups bleiben dauerhaft erhalten.",
                 font=("Helvetica Neue", 8),
                 bg=T["BG_APP"], fg=T["TEXT_MUTED"]).pack(side="left")
        tk.Button(foot, text="Schliessen",
                  font=("Helvetica Neue", 9),
                  bg=T["BG_INPUT"], fg=T["TEXT_LABEL"],
                  relief="flat", bd=0, cursor="hand2", padx=14, pady=5,
                  command=win.destroy).pack(side="right")

    def _preview_backup(self, fpath, created, months, T):
        """Kleines Vorschau-Popup für ein Backup ohne es zu laden."""
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                bundle = json.load(f)
        except Exception as exc:
            tk.messagebox.showerror("Vorschau", str(exc))
            return

        pop = tk.Toplevel(self)
        pop.title("Backup-Vorschau")
        pop.resizable(False, False)
        pop.configure(bg=T["BG_CARD"])
        pop.attributes("-topmost", True)
        pop.grab_set()

        outer = tk.Frame(pop, bg=T["BORDER"], padx=1, pady=1)
        outer.pack(fill="both", expand=True)
        inner = tk.Frame(outer, bg=T["BG_CARD"], padx=20, pady=16)
        inner.pack(fill="both", expand=True)

        tk.Label(inner, text="Backup-Vorschau",
                 font=("Helvetica Neue", 12, "bold"),
                 bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"]).pack(anchor="w", pady=(0,10))
        tk.Frame(inner, bg=T["BORDER_LIGHT"], height=1).pack(fill="x", pady=(0,10))

        if "data" in bundle and isinstance(bundle["data"], dict):
            data = bundle["data"]
            sett = bundle.get("settings", {})
            type_str = bundle.get("type", "?").capitalize()
        else:
            data = bundle
            sett = {}
            type_str = "Extern"

        # Gesamtdaten berechnen
        month_keys = sorted(k for k in data if not k.startswith("year_"))
        total_inc, total_sav = 0.0, 0.0
        for mk in month_keys:
            md  = data[mk]
            inc = sum(self._parse_amount(r.get("amount",0))
                      for r in md.get("income", []))
            out = sum(self._parse_amount(r.get("amount",0))
                      for cat in ("essenz","freizeit","auto","versicherung")
                      for r in md.get(cat, []))
            # Fixkosten /12
            yr  = int(mk.split("-")[0])
            fix = sum(self._parse_amount(r.get("amount",0))
                      for r in data.get(f"year_{yr}", {}).get("fixkosten", [])) / 12.0
            total_inc += inc
            total_sav += max(0.0, inc - out - fix)

        rows = [
            ("Erstellt am",        created),
            ("Typ",                type_str),
            ("Monate mit Daten",   f"{months}"),
            ("Zeitraum",           f"{month_keys[0]} – {month_keys[-1]}"
                                   if month_keys else "–"),
            ("Gesamteinnahmen",    f"{total_inc:,.2f} €"),
            ("Gesamtersparnis",    f"{total_sav:,.2f} €"),
            ("Dark-Mode",          "Ja" if sett.get("dark_mode") else "Nein"),
            ("Sparziel",           f"{sett.get('savings_goal_pct', 0):.0f} %"),
            ("Dateipfad",          os.path.basename(fpath)),
        ]
        for lbl, val in rows:
            r = tk.Frame(inner, bg=T["BG_CARD"])
            r.pack(fill="x", pady=2)
            tk.Label(r, text=lbl + ":",
                     font=("Helvetica Neue", 9),
                     bg=T["BG_CARD"], fg=T["TEXT_MUTED"],
                     width=18, anchor="w").pack(side="left")
            tk.Label(r, text=val,
                     font=("Helvetica Neue", 9, "bold"),
                     bg=T["BG_CARD"], fg=T["TEXT_PRIMARY"],
                     anchor="w").pack(side="left")

        tk.Frame(inner, bg=T["BORDER_LIGHT"], height=1).pack(fill="x", pady=(12,8))
        tk.Button(inner, text="Schliessen",
                  font=("Helvetica Neue", 9),
                  bg=T["BG_INPUT"], fg=T["TEXT_LABEL"],
                  relief="flat", bd=0, cursor="hand2", padx=14, pady=5,
                  command=pop.destroy).pack(anchor="e")

    # ── Hilfsmethoden ─────────────────────────────────────────────────────────
    @staticmethod
    def _parse_amount(s):
        try:
            return float(str(s).replace(",", "."))
        except (ValueError, TypeError):
            return 0.0

    @staticmethod
    def _eval_expr(text):
        """Berechne einfache +-*/ Ausdrücke im Betragsfeld.
        Gibt formatierten Ergebnis-String zurück oder None wenn kein Ausdruck."""
        t = text.replace(",", ".").strip()
        if not t:
            return None
        # Nur auswerten wenn Rechenzeichen vorhanden (sonst normale Zahl lassen)
        if not any(op in t for op in ("+", "-", "*", "/")):
            return None
        # Potenzoperator blockieren – könnte UI einfrieren (z. B. 1**1000000)
        if "**" in t:
            return None
        # Sicherheitscheck: nur Ziffern, Dezimalpunkt und Rechenoperatoren
        if not re.match(r'^[\d\s\.\+\-\*\/\(\)]+$', t):
            return None
        try:
            result = eval(t)  # noqa: S307
            if not isinstance(result, (int, float)) or result < 0:
                return None
            return str(int(result)) if result == int(result) else f"{result:.2f}"
        except Exception:
            return None

    def destroy(self):
        self._app_closing = True
        if self._refresh_pending is not None:
            try:
                self.after_cancel(self._refresh_pending)
            except Exception:
                pass
            self._refresh_pending = None
        if getattr(self, '_cats_scroll_after_id', None):
            try:
                self.after_cancel(self._cats_scroll_after_id)
            except Exception:
                pass
            self._cats_scroll_after_id = None
        self._save_month()
        self._create_backup("auto")
        try:
            _goal_pct_save = float(self._savings_goal_var.get())
        except (ValueError, TypeError):
            _goal_pct_save = 0
        save_settings({
            "dark_mode":          self.dark_mode,
            "last_year":          self.current_year.get(),
            "last_month":         self.current_month.get(),
            "overview_chart":     self.overview_chart,
            "cat_settings":       self._cat_settings,
            "custom_cat_order":   self._custom_cat_order,
            "savings_goal_pct":   _goal_pct_save,
            "drilldown_geometry": self._drilldown_geometry,
            "overview_geometry":  self._overview_geometry,
            "main_geometry":      self._main_geometry,
            "search_geometry":    self._search_geometry,
            "search_exact_amount": self._search_exact_amount,
            "search_hide_empty":   self._search_hide_empty,
        })
        plt.close("all")
        super().destroy()


if __name__ == "__main__":
    app = FinanzApp()
    app.mainloop()
    sys.exit(0)



