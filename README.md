# EE305 Project 9 — Transmission Line Transient Analysis

GUI application to plot the transient voltage $V(z=0, t)$ at the input terminal of a transmission line ($Z_0 = R_0 + jX_0$, length $l$, wave velocity $u$) driven by a DC source $V_0$ with internal resistance $R_g$ and terminated by an inductive load $L_L$ or capacitive load $C_L$, with time $t$ in multiples of $T = l/u$.

## How to Run
```powershell
pip install -r requirements.txt
python main.py
```

## Files
- `main.py` — Tkinter + Matplotlib GUI with interactive cursor graph tracing and PNG export
- `transient_solver.py` — Transient simulation engine
- `requirements.txt` — Python dependencies (`numpy`, `matplotlib`)
