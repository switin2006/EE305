import numpy as np


def simulate_transient(
    V0,
    Rg,
    l,
    u,
    R0,
    X0,
    load_type,
    LL=None,
    CL=None,
    t_max_T=20.0,
    points_per_T=500,
):
    """Compute transient input voltage V(0, t) for t in [0, t_max_T * T]."""
    if load_type not in ("inductive", "capacitive"):
        raise ValueError("load_type must be 'inductive' or 'capacitive'.")
    if l <= 0 or u <= 0:
        raise ValueError("Line length l and velocity u must be > 0.")
    if Rg < 0:
        raise ValueError("Internal resistance Rg must be >= 0.")
    if t_max_T <= 0:
        raise ValueError("Time span (multiples of T) must be > 0.")

    T = l / u
    Zeff = float(np.sqrt(R0**2 + X0**2))
    if Zeff <= 0:
        raise ValueError("Characteristic impedance magnitude |Z0| must be > 0.")

    # Source reflection coefficient and initial forward voltage step
    GammaS = (Rg - Zeff) / (Rg + Zeff)
    V1_plus = V0 * Zeff / (Rg + Zeff)

    if load_type == "inductive":
        if LL is None or LL < 0:
            raise ValueError("LL must be >= 0 for an inductive load.")
        tau = LL / Zeff
    else:
        if CL is None or CL < 0:
            raise ValueError("CL must be >= 0 for a capacitive load.")
        tau = Zeff * CL

    # Align grid so one-way transit time T = n_delay * dt
    n_delay = int(points_per_T)
    n_steps = max(2, int(round(t_max_T * n_delay)) + 1)
    dt = T / n_delay
    t_norm = np.arange(n_steps, dtype=float) / n_delay

    V_f_source = np.zeros(n_steps, dtype=float)
    V_b_source = np.zeros(n_steps, dtype=float)
    V_f_load = np.zeros(n_steps, dtype=float)
    V_b_load = np.zeros(n_steps, dtype=float)

    exp_factor = float(np.exp(-dt / tau)) if tau > 1e-18 else 0.0
    state = 0.0  # I_L for inductive load, V_C for capacitive load

    for k in range(n_steps):
        if k >= n_delay:
            V_b_source[k] = V_b_load[k - n_delay]

        # Source boundary: V_f(0, t) = V1+ + GammaS * V_b(0, t)
        V_f_source[k] = V1_plus + GammaS * V_b_source[k]

        if k >= n_delay:
            V_f_load[k] = V_f_source[k - n_delay]

        Vf = V_f_load[k]

        if load_type == "inductive":
            if LL <= 1e-18:
                V_b_load[k] = -Vf
            else:
                # V_b = Vf - Zeff*I_L; dI_L/dt + (Zeff/LL)*I_L = 2*Vf/LL
                V_b_load[k] = Vf - Zeff * state
                I_L_eq = 2.0 * Vf / Zeff
                state = I_L_eq + (state - I_L_eq) * exp_factor
        else:
            if CL <= 1e-18:
                V_b_load[k] = Vf
            else:
                # V_b = V_C - Vf; dV_C/dt + V_C/(Zeff*CL) = 2*Vf/(Zeff*CL)
                V_b_load[k] = state - Vf
                V_C_eq = 2.0 * Vf
                state = V_C_eq + (state - V_C_eq) * exp_factor

    V_input = V_f_source + V_b_source
    V_steady = 0.0 if load_type == "inductive" else V0

    params = {
        "T": T,
        "Zeff": Zeff,
        "GammaS": GammaS,
        "V1_plus": V1_plus,
        "tau": tau,
        "V_steady": V_steady,
    }

    return t_norm, V_input, params
