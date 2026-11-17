"""Transformaciones puras sobre la ventana de tres rezagos verificados."""

import numpy as np

LAGS = ["ventas_hace_3_meses", "ventas_hace_2_meses", "ventas_mes_anterior"]
DERIVED = ["lag3_mean", "lag3_std", "lag3_zero_fraction"]


def lag_features(frame):
    lags = frame[LAGS].to_numpy(dtype=float)
    if not np.isfinite(lags).all() or (lags < 0).any():
        raise ValueError("Missing or invalid closed lag")
    return frame.assign(
        lag3_mean=lags.mean(axis=1),
        lag3_std=lags.std(axis=1),
        lag3_zero_fraction=(lags == 0).mean(axis=1),
    )
