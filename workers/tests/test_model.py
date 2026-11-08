import numpy as np
import polars as pl

from halflife.evaluate import psi, reference
from halflife.train import calibrate, logit


def test_platt_calibration_matches_observed_rate_and_keeps_order():
    rng = np.random.default_rng(0)
    raw = rng.uniform(0.3, 0.9, 20_000)
    y = rng.uniform(size=raw.size) < raw / 20
    a, b = calibrate(raw, y)
    p = 1 / (1 + np.exp(-(a * logit(raw) + b)))
    assert abs(p.mean() - y.mean()) < 0.002
    assert np.all(np.diff(p[np.argsort(raw)]) >= 0)


def test_psi_flags_a_shifted_feature_only():
    rng = np.random.default_rng(1)
    base = pl.DataFrame({"x": rng.normal(0, 1, 50_000), "z": rng.normal(0, 1, 50_000)})
    ref = reference(base, ["x", "z"])
    new = pl.DataFrame({"x": rng.normal(0, 1, 20_000), "z": rng.normal(1.5, 1, 20_000)})
    drift = psi(ref, new)
    assert drift["x"] < 0.05 and drift["z"] > 0.25
