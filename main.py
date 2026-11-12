import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import numpy as np

import matplotlib

matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from transient_solver import simulate_transient

BG_COLOUR = "#F4F6F9"
FRAME_BG = "#FFFFFF"
ACCENT = "#1565C0"
ACCENT_HOVER = "#0D47A1"
CAP_COLOUR = "#C62828"
TEXT_COLOUR = "#212121"
LABEL_COLOUR = "#424242"
ENTRY_BG = "#FAFAFA"
SUCCESS_GREEN = "#2E7D32"

FONT_TITLE = ("Segoe UI", 14, "bold")
FONT_SECTION = ("Segoe UI", 10, "bold")
FONT_LABEL = ("Segoe UI", 10)
FONT_ENTRY = ("Segoe UI", 10)
FONT_BUTTON = ("Segoe UI", 10, "bold")
FONT_PARAM = ("Consolas", 9)
FONT_STATUS = ("Segoe UI", 9)


def _parse_float(entry_widget, name, positive=True, allow_zero=False):
    raw = entry_widget.get().strip()
    if not raw:
        raise ValueError(f"'{name}' is empty. Please enter a value.")
    try:
        val = float(raw)
    except ValueError:
        raise ValueError(f"'{name}' = '{raw}' is not a valid number.")
    if not np.isfinite(val):
        raise ValueError(f"'{name}' must be a finite number.")
    if positive and not allow_zero and val <= 0:
        raise ValueError(f"'{name}' must be > 0 (got {val}).")
    if positive and allow_zero and val < 0:
        raise ValueError(f"'{name}' must be >= 0 (got {val}).")
    return val


class TransientApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("EE305 Project 9 — Transmission Line Transient Voltage")
        self.configure(bg=BG_COLOUR)
        try:
            self.state("zoomed")
        except tk.TclError:
            self.geometry("1200x720")
        self.minsize(980, 600)

        self._t_norm = None
        self._V_input = None
        self._last_T = None
        self._crosshair_v = None
        self._crosshair_h = None
        self._trace_dot = None
        self._trace_annot = None

        self._configure_styles()
        self._build_ui()
        self.after(150, self._on_compute)

    def _configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG_COLOUR)
        style.configure("Card.TFrame", background=FRAME_BG, relief="solid", borderwidth=1)
        style.configure("Inner.TFrame", background=FRAME_BG)
        style.configure("TLabel", background=FRAME_BG, foreground=TEXT_COLOUR, font=FONT_LABEL)
        style.configure("Section.TLabel", background=FRAME_BG, foreground=ACCENT, font=FONT_SECTION)
        style.configure("Title.TLabel", background=BG_COLOUR, foreground=ACCENT, font=FONT_TITLE)
        style.configure("Param.TLabel", background=FRAME_BG, foreground=TEXT_COLOUR, font=FONT_PARAM)
        style.configure("Status.TLabel", background=BG_COLOUR, foreground=LABEL_COLOUR, font=FONT_STATUS)
        style.configure("TRadiobutton", background=FRAME_BG, foreground=TEXT_COLOUR, font=FONT_LABEL)

    def _build_ui(self):
        title_frame = ttk.Frame(self, style="TFrame")
        title_frame.pack(fill="x", padx=15, pady=(10, 4))
        ttk.Label(
            title_frame,
            text="Project 9: Transient Voltage V(0, t) at Input Terminal of Transmission Line",
            style="Title.TLabel",
        ).pack(side="left", anchor="w")

        body = ttk.Frame(self, style="TFrame")
        body.pack(fill="both", expand=True, padx=15, pady=(4, 6))
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        left = ttk.Frame(body, style="Card.TFrame", width=340)
        left.grid(row=0, column=0, sticky="ns", padx=(0, 10))
        left.grid_propagate(False)

        self._build_input_fields(left)

        right = ttk.Frame(body, style="Card.TFrame")
        right.grid(row=0, column=1, sticky="nsew")
        self._build_plot_panel(right)

        self._status_var = tk.StringVar(value="Ready.")
        ttk.Label(self, textvariable=self._status_var, style="Status.TLabel", anchor="w").pack(
            fill="x", padx=15, pady=(0, 8)
        )

    def _build_input_fields(self, parent):
        px = 14
        row = 0

        ttk.Label(parent, text="Source Parameters", style="Section.TLabel").grid(
            row=row, column=0, columnspan=2, sticky="w", padx=px, pady=(12, 4)
        )
        row += 1

        self.ent_V0, row = self._add_entry(parent, row, "V₀ (V)", "10", px)
        self.ent_Rg, row = self._add_entry(parent, row, "Rg (Ω)", "75", px)

        ttk.Label(parent, text="Transmission Line (Z₀ = R₀ + jX₀)", style="Section.TLabel").grid(
            row=row, column=0, columnspan=2, sticky="w", padx=px, pady=(12, 4)
        )
        row += 1

        self.ent_l, row = self._add_entry(parent, row, "l (m)", "100", px)
        self.ent_u, row = self._add_entry(parent, row, "u (m/s)", "2e8", px)
        self.ent_R0, row = self._add_entry(parent, row, "R₀ (Ω)", "50", px)
        self.ent_X0, row = self._add_entry(parent, row, "X₀ (Ω)", "0", px)

        ttk.Label(parent, text="Load Termination", style="Section.TLabel").grid(
            row=row, column=0, columnspan=2, sticky="w", padx=px, pady=(12, 4)
        )
        row += 1

        self.load_var = tk.StringVar(value="inductive")
        rb_frame = ttk.Frame(parent, style="Inner.TFrame")
        rb_frame.grid(row=row, column=0, columnspan=2, sticky="w", padx=px, pady=4)
        ttk.Radiobutton(
            rb_frame,
            text="Inductive (LL)",
            variable=self.load_var,
            value="inductive",
            command=self._on_load_type_change,
        ).pack(side="left", padx=(0, 14))
        ttk.Radiobutton(
            rb_frame,
            text="Capacitive (CL)",
            variable=self.load_var,
            value="capacitive",
            command=self._on_load_type_change,
        ).pack(side="left")
        row += 1

        self.ent_LL, row = self._add_entry(parent, row, "LL (H)", "25e-6", px)
        self.ent_CL, row = self._add_entry(parent, row, "CL (F)", "10e-9", px)
        self.ent_CL.configure(state="disabled")

        self.ent_tmax, row = self._add_entry(parent, row, "Time span (× T)", "20", px)

        btn_frame = ttk.Frame(parent, style="Inner.TFrame")
        btn_frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=px, pady=(14, 6))
        row += 1

        tk.Button(
            btn_frame,
            text="Plot V(0, t)",
            font=FONT_BUTTON,
            bg=ACCENT,
            fg="white",
            activebackground=ACCENT_HOVER,
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            pady=6,
            command=self._on_compute,
        ).pack(fill="x", pady=(0, 6))

        tk.Button(
            btn_frame,
            text="Save Plot PNG",
            font=FONT_LABEL,
            bg="#E0E0E0",
            fg=TEXT_COLOUR,
            activebackground="#BDBDBD",
            relief="flat",
            cursor="hand2",
            pady=4,
            command=self._on_save,
        ).pack(fill="x")

        ttk.Label(parent, text="Derived Quantities", style="Section.TLabel").grid(
            row=row, column=0, columnspan=2, sticky="w", padx=px, pady=(12, 4)
        )
        row += 1

        self._param_var = tk.StringVar(value="")
        ttk.Label(
            parent,
            textvariable=self._param_var,
            style="Param.TLabel",
            justify="left",
        ).grid(row=row, column=0, columnspan=2, sticky="w", padx=px, pady=(0, 10))

    def _add_entry(self, parent, row, label_text, default, px):
        ttk.Label(parent, text=label_text).grid(row=row, column=0, sticky="w", padx=(px, 8), pady=3)
        ent = tk.Entry(
            parent,
            font=FONT_ENTRY,
            width=16,
            bg=ENTRY_BG,
            relief="solid",
            bd=1,
            highlightcolor=ACCENT,
            highlightthickness=1,
        )
        ent.insert(0, default)
        ent.bind("<Return>", lambda e: self._on_compute())
        ent.grid(row=row, column=1, sticky="ew", padx=(0, px), pady=3)
        return ent, row + 1

    def _build_plot_panel(self, parent):
        self.fig = Figure(figsize=(8.0, 5.4), dpi=100, facecolor=FRAME_BG)
        self.ax = self.fig.add_subplot(111)
        self._style_axes()

        self.canvas_mpl = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas_mpl.draw()
        self.canvas_mpl.get_tk_widget().pack(fill="both", expand=True, padx=6, pady=(6, 0))
        self.canvas_mpl.mpl_connect("motion_notify_event", self._on_plot_hover)
        self.canvas_mpl.mpl_connect("axes_leave_event", self._on_plot_leave)

        toolbar = NavigationToolbar2Tk(self.canvas_mpl, parent)
        toolbar.update()
        toolbar.pack(fill="x", padx=6, pady=(0, 4))

    def _style_axes(self):
        self.ax.set_xlabel("Time  t  (multiples of T = l / u)", fontsize=11, fontweight="bold")
        self.ax.set_ylabel("Input Voltage  V(0, t)  [V]", fontsize=11, fontweight="bold")
        self.ax.set_title(
            "Transient Voltage at Input Terminal V(0, t)",
            fontsize=12,
            fontweight="bold",
            color=ACCENT,
            pad=10,
        )
        self.ax.grid(True, linestyle="--", alpha=0.45)

    def _on_load_type_change(self):
        if self.load_var.get() == "inductive":
            self.ent_LL.configure(state="normal")
            self.ent_CL.configure(state="disabled")
        else:
            self.ent_LL.configure(state="disabled")
            self.ent_CL.configure(state="normal")

    def _on_compute(self):
        try:
            V0 = _parse_float(self.ent_V0, "V₀", positive=False)
            Rg = _parse_float(self.ent_Rg, "Rg", allow_zero=True)
            l = _parse_float(self.ent_l, "l")
            u = _parse_float(self.ent_u, "u")
            R0 = _parse_float(self.ent_R0, "R₀", allow_zero=True)
            X0 = _parse_float(self.ent_X0, "X₀", positive=False)
            if R0 == 0 and X0 == 0:
                raise ValueError("|Z₀| = sqrt(R₀² + X₀²) must be > 0.")

            load_type = self.load_var.get()
            LL = _parse_float(self.ent_LL, "LL", allow_zero=True) if load_type == "inductive" else None
            CL = _parse_float(self.ent_CL, "CL", allow_zero=True) if load_type == "capacitive" else None
            t_max_T = _parse_float(self.ent_tmax, "Time span (× T)")
            if t_max_T > 200:
                raise ValueError("Time span (× T) must be <= 200.")

            points_per_T = 500 if t_max_T <= 20 else max(80, int(10000 / t_max_T))
            t_norm, V_input, p = simulate_transient(
                V0=V0,
                Rg=Rg,
                l=l,
                u=u,
                R0=R0,
                X0=X0,
                load_type=load_type,
                LL=LL,
                CL=CL,
                t_max_T=t_max_T,
                points_per_T=points_per_T,
            )
        except ValueError as exc:
            messagebox.showerror("Input Error", str(exc))
            self._status_var.set(f"Input error: {exc}")
            return

        self.ax.clear()
        self._style_axes()

        color = ACCENT if load_type == "inductive" else CAP_COLOUR
        self.ax.plot(t_norm, V_input, color=color, linewidth=1.9, label="V(0, t)")
        self.ax.axhline(
            p["V1_plus"],
            color="#EF6C00",
            linestyle="--",
            linewidth=1.1,
            label=f"V₁⁺ = {p['V1_plus']:.3f} V",
        )
        self.ax.axhline(
            p["V_steady"],
            color=SUCCESS_GREEN,
            linestyle=":",
            linewidth=1.3,
            label=f"V(0, ∞) = {p['V_steady']:.3f} V",
        )

        if 2 <= t_max_T <= 40:
            for k in range(2, int(t_max_T) + 1, 2):
                self.ax.axvline(k, color="#9E9E9E", linestyle=":", linewidth=0.8, alpha=0.55)

        load_label = f"LL = {LL:.3e} H" if load_type == "inductive" else f"CL = {CL:.3e} F"
        self.ax.set_title(
            f"Transient Voltage at Input Terminal V(0, t) — {load_type.capitalize()} Load ({load_label})",
            fontsize=12,
            fontweight="bold",
            color=ACCENT,
            pad=10,
        )
        self.ax.set_xlim(0, t_max_T)
        self.ax.legend(loc="best", fontsize=9)
        self.fig.tight_layout()

        self._t_norm = t_norm
        self._V_input = V_input
        self._last_T = p["T"]
        self._init_trace_artists()
        self.canvas_mpl.draw()

        self._param_var.set(
            f"T = l/u   = {p['T']:.4e} s\n"
            f"|Z₀|      = {p['Zeff']:.4f} Ω\n"
            f"Γ_S       = {p['GammaS']:+.6f}\n"
            f"V₁⁺       = {p['V1_plus']:.4f} V\n"
            f"τ         = {p['tau']:.4e} s\n"
            f"V(0, ∞)   = {p['V_steady']:.4f} V"
        )
        self._status_var.set(
            f"Plotted {load_type} load for t ∈ [0, {t_max_T:g}T]. Move cursor over graph to trace values."
        )

    def _init_trace_artists(self):
        self._crosshair_v = self.ax.axvline(0, color="#64748B", linestyle="--", linewidth=0.9, visible=False)
        self._crosshair_h = self.ax.axhline(0, color="#64748B", linestyle="--", linewidth=0.9, visible=False)
        (self._trace_dot,) = self.ax.plot([], [], "o", color="#111827", markersize=6, zorder=5, visible=False)
        self._trace_annot = self.ax.annotate(
            "",
            xy=(0, 0),
            xytext=(12, 12),
            textcoords="offset points",
            bbox=dict(boxstyle="round,pad=0.35", fc="#1B2430", ec="none", alpha=0.92),
            color="white",
            fontsize=8.5,
            fontfamily="Consolas",
            zorder=6,
            visible=False,
        )

    def _hide_trace(self, redraw=True):
        if self._trace_annot is None:
            return
        changed = self._trace_annot.get_visible()
        for artist in (self._crosshair_v, self._crosshair_h, self._trace_dot, self._trace_annot):
            if artist is not None:
                artist.set_visible(False)
        if changed and redraw:
            self.canvas_mpl.draw_idle()

    def _on_plot_hover(self, event):
        if self._t_norm is None or event.inaxes != self.ax or event.xdata is None:
            self._hide_trace()
            return

        n = len(self._t_norm)
        idx = int(np.searchsorted(self._t_norm, event.xdata))
        if idx <= 0:
            idx = 0
        elif idx >= n:
            idx = n - 1
        elif abs(event.xdata - self._t_norm[idx - 1]) <= abs(self._t_norm[idx] - event.xdata):
            idx = idx - 1

        x = float(self._t_norm[idx])
        y = float(self._V_input[idx])
        t_sec = x * self._last_T

        self._crosshair_v.set_xdata([x, x])
        self._crosshair_h.set_ydata([y, y])
        self._trace_dot.set_data([x], [y])

        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        right_side = x > xlim[0] + 0.72 * (xlim[1] - xlim[0])
        top_side = y > ylim[0] + 0.78 * (ylim[1] - ylim[0])
        self._trace_annot.xy = (x, y)
        self._trace_annot.set_position((-12 if right_side else 12, -12 if top_side else 12))
        self._trace_annot.set_ha("right" if right_side else "left")
        self._trace_annot.set_va("top" if top_side else "bottom")
        self._trace_annot.set_text(f"t = {x:.3f} T ({t_sec:.2e} s)\nV(0, t) = {y:.4f} V")

        for artist in (self._crosshair_v, self._crosshair_h, self._trace_dot, self._trace_annot):
            artist.set_visible(True)

        self._status_var.set(f"Trace: t = {x:.3f} T ({t_sec:.3e} s) | V(0, t) = {y:.4f} V")
        self.canvas_mpl.draw_idle()

    def _on_plot_leave(self, _event):
        self._hide_trace()

    def _on_save(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("PDF Document", "*.pdf"), ("All Files", "*.*")],
            title="Save Plot As...",
        )
        if path:
            self._hide_trace(redraw=False)
            self.fig.savefig(path, dpi=200, bbox_inches="tight")
            self._status_var.set(f"Plot saved -> {path}")


if __name__ == "__main__":
    app = TransientApp()
    app.mainloop()
