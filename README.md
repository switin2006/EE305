# EE305 Project 9 — Transmission Line Transient Analysis

Plots the transient voltage $V(z=0, t)$ at the input terminal of a transmission line ($Z_0 = R_0 + jX_0$, length $l$, wave velocity $u$) driven by a DC source $V_0$ with internal resistance $R_g$ and terminated by an inductive load $L_L$ or capacitive load $C_L$, with time $t$ in multiples of $T = l/u$.

## Option 1: Desktop GUI (`main.py`)
```powershell
pip install -r requirements.txt
python main.py
```

## Option 2: Local Web Portal (`server.py` + `static/`)
```powershell
pip install numpy
python server.py
```
Open `http://127.0.0.1:8000` in your browser.
