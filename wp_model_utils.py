"""
Shared Win Probability prediction utilities.
Loads the ML model if available, otherwise falls back to the analytic formula.
All WP consumers (calculate_wpa, wp_replay, preprocess_wp_data) import from here.
"""

import math
import os
import sys
import numpy as np


# ── CalibratedModel class (must be here for pickle deserialization) ───
class CalibratedModel:
    """
    GBM + calibration wrapper that mimics sklearn estimator API.
    Supports two calibration strategies:
      - Platt scaling (LogisticRegression): fits 2 params on log-odds, robust default
      - Isotonic regression (IsotonicRegression): non-parametric, legacy fallback
    """
    def __init__(self, base_model, calibrator):
        self.base_model = base_model
        self.calibrator = calibrator

    def predict_proba(self, X):
        raw = self.base_model.predict_proba(X)[:, 1]
        calibrated = self._apply_calibrator(raw)
        return np.column_stack([1 - calibrated, calibrated])

    def _apply_calibrator(self, raw_probs):
        raw_probs = np.clip(raw_probs, 1e-7, 1 - 1e-7)
        # Platt scaling: calibrator is LogisticRegression on log-odds
        if hasattr(self.calibrator, 'coef_'):
            log_odds = np.log(raw_probs / (1 - raw_probs)).reshape(-1, 1)
            return self.calibrator.predict_proba(log_odds)[:, 1]
        # Isotonic regression: direct predict (legacy / fallback)
        return self.calibrator.predict(raw_probs)


# ── Lazy-loaded model singleton ───────────────────────────────
_model = None
_model_loaded = False
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'data_cache', 'wp_model.pkl')


def _load_model():
    """Attempt to load the trained ML model once."""
    global _model, _model_loaded
    if _model_loaded:
        return _model
    _model_loaded = True
    if os.path.exists(MODEL_PATH):
        try:
            import joblib
            # Temporarily inject CalibratedModel into common module namespaces
            # so joblib/pickle can resolve it regardless of where it was pickled
            import wp_model_utils
            _orig_main = sys.modules.get('__main__')
            _orig_train = sys.modules.get('train_wp_model')
            # Patch: make CalibratedModel available in __main__ and train_wp_model
            if _orig_main is not None:
                if not hasattr(_orig_main, 'CalibratedModel'):
                    _orig_main.CalibratedModel = CalibratedModel
            if _orig_train is not None:
                if not hasattr(_orig_train, 'CalibratedModel'):
                    _orig_train.CalibratedModel = CalibratedModel
            else:
                # Create a fake module so pickle can resolve train_wp_model.CalibratedModel
                import types
                _fake = types.ModuleType('train_wp_model')
                _fake.CalibratedModel = CalibratedModel
                sys.modules['train_wp_model'] = _fake

            _model = joblib.load(MODEL_PATH)

            # Clean up fake module if we created one
            if _orig_train is None and 'train_wp_model' in sys.modules:
                del sys.modules['train_wp_model']

            print(f"[WP Model] Loaded ML model from {MODEL_PATH}")
        except Exception as e:
            print(f"[WP Model] Failed to load ML model: {e}. Using analytic fallback.")
            _model = None
    return _model


# ── Analytic fallback (original formula) ──────────────────────
def _analytic_wp(margin, seconds_remaining):
    """Original logistic formula — used when no ML model is available."""
    if seconds_remaining <= 0:
        return 1.0 if margin > 0 else (0.0 if margin < 0 else 0.5)
    sigma = 11.0 * math.sqrt(seconds_remaining / 2400.0)
    if sigma < 0.1:
        sigma = 0.1
    z = margin / sigma
    return 1.0 / (1.0 + math.exp(-0.8 * z))


# ── Public API ────────────────────────────────────────────────
def predict_wp(margin, seconds_remaining, elo_diff=0.0, is_home=True,
               scoring_run=0.0, lead_changes=0):
    """
    Predict win probability for Team A (home).

    Parameters
    ----------
    margin : float
        POINTS_A - POINTS_B (positive = home leads).
    seconds_remaining : float
        Seconds left in regulation (2400 = full game).
    elo_diff : float
        Home Elo - Away Elo (0 if unknown).
    is_home : bool
        Whether the perspective team is the home team.
    scoring_run : float
        Recent scoring differential (last ~10 possessions).
    lead_changes : int
        Number of lead changes so far in the game.

    Returns
    -------
    float
        Win probability for Team A, between 0.0 and 1.0.
    """
    # Hard edge case: game is over — deterministic result
    if seconds_remaining <= 0:
        return 1.0 if margin > 0 else (0.0 if margin < 0 else 0.5)

    model = _load_model()

    if model is None:
        # Fallback: ignore context features, use pure margin + time
        return _analytic_wp(margin, seconds_remaining)

    # Build feature vector matching train_wp_model.py feature order
    time_frac = seconds_remaining / 2400.0 if seconds_remaining > 0 else 0.0
    period = _period_from_seconds(seconds_remaining)
    is_overtime = 1.0 if period > 4 else 0.0
    margin_time = margin * time_frac
    sqrt_tf = time_frac ** 0.5 if time_frac > 0 else 0.01
    normalized_lead = margin / sqrt_tf

    features = np.array([[
        margin,
        seconds_remaining,
        time_frac,
        elo_diff,
        1.0 if is_home else 0.0,
        margin_time,
        normalized_lead,
        scoring_run,
        float(lead_changes),
        is_overtime,
    ]])

    prob = model.predict_proba(features)[0][1]  # P(Team A wins)
    return float(prob)


def predict_wp_batch(df):
    """
    Vectorised prediction for a DataFrame with columns:
        margin, seconds_remaining, elo_diff, is_home, scoring_run, lead_changes

    Returns a numpy array of WP values.
    """
    model = _load_model()

    if model is None:
        return np.array([
            _analytic_wp(row['margin'], row['seconds_remaining'])
            for _, row in df.iterrows()
        ])

    time_frac = df['seconds_remaining'] / 2400.0
    period = df['seconds_remaining'].apply(_period_from_seconds)
    is_overtime = (period > 4).astype(float)
    margin_time = df['margin'] * time_frac
    sqrt_tf = time_frac.clip(lower=0.0001) ** 0.5
    normalized_lead = df['margin'] / sqrt_tf

    features = np.column_stack([
        df['margin'].values,
        df['seconds_remaining'].values,
        time_frac.values,
        df['elo_diff'].values,
        df['is_home'].astype(float).values,
        margin_time.values,
        normalized_lead.values,
        df['scoring_run'].values,
        df['lead_changes'].astype(float).values,
        is_overtime.values,
    ])

    return model.predict_proba(features)[:, 1]


# ── Per-game Elo lookup ───────────────────────────────────────
_game_elos = None
_game_elos_loaded = False
GAME_ELOS_PATH = os.path.join(os.path.dirname(__file__), 'data_cache', 'game_elos.json')


def _load_game_elos():
    """Load the per-game Elo snapshot file once."""
    global _game_elos, _game_elos_loaded
    if _game_elos_loaded:
        return _game_elos
    _game_elos_loaded = True
    if os.path.exists(GAME_ELOS_PATH):
        try:
            import json
            with open(GAME_ELOS_PATH, 'r') as f:
                _game_elos = json.load(f)
        except Exception as e:
            print(f"[WP Model] Could not load game_elos.json: {e}")
            _game_elos = {}
    else:
        _game_elos = {}
    return _game_elos


def get_elo_diff(season, gamecode):
    """
    Return the pre-game Elo differential (home - away) for a given game.
    Returns 0.0 if not found (safe fallback — model handles unknown Elo).
    """
    elos = _load_game_elos()
    key = f"{season}_{gamecode}"
    entry = elos.get(key)
    if entry is None:
        return 0.0
    return entry['elo_diff']


def _period_from_seconds(seconds_remaining):
    """Estimate the period from seconds remaining."""
    if seconds_remaining <= 0:
        return 4
    if seconds_remaining <= 600:
        return 4
    elif seconds_remaining <= 1200:
        return 3
    elif seconds_remaining <= 1800:
        return 2
    elif seconds_remaining <= 2400:
        return 1
    else:
        return 5  # overtime
