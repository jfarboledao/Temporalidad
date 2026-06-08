from __future__ import annotations

import base64
import warnings
from io import BytesIO

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import music21
from sklearn.preprocessing import MinMaxScaler

warnings.filterwarnings("ignore")

WINDOW_SIZE = 4.0

_VESSEL_COLORS = {
    "flux_rate": "#f8bf46",
    "avg_gestalt": "#7c9eff",
    "tension_index": "#ff7c7c",
    "entropy": "#7cffa4",
    "vertical_density": "#c084fc",
    "poly_activity": "#fb923c",
}
_VESSEL_LABELS = {
    "flux_rate": "Flux Rate",
    "avg_gestalt": "Avg Gestalt",
    "tension_index": "Tension Index",
    "entropy": "Entropy",
    "vertical_density": "Vertical Density",
    "poly_activity": "Poly Activity",
}
_TENSION_WEIGHTS = [10.0, 5.0, 2.0, 1.0, 1.0, 0.5]


def get_polyphonic_density(elements):
    """
    Calcula la densidad de voces y la actividad rítmica independiente.
    Returns (avg_vertical_density, polyphonic_activity).
    """
    if not elements:
        return 0.0, 0.0

    voice_counts = []
    for e in elements:
        if e.isChord:
            voice_counts.append(len(e.pitches))
        elif e.isNote:
            voice_counts.append(1)

    avg_vertical_density = float(np.mean(voice_counts)) if voice_counts else 0.0
    total_attacks = len(elements)
    polyphonic_activity = (
        total_attacks / avg_vertical_density if avg_vertical_density > 0 else 0.0
    )

    return avg_vertical_density, polyphonic_activity


def analyze_temporal_vessels(
    score_path: str, window_size: float = WINDOW_SIZE
) -> pd.DataFrame:
    """
    Analyze a score using the temporal vessels from dynamic time theory.
    Returns one row per time window.
    """
    score = music21.converter.parse(score_path)
    flat_score = score.flatten().notes
    total_duration = float(score.quarterLength)
    windows = np.arange(0, total_duration, window_size)

    results = []
    for start in windows:
        end = start + window_size
        elements = list(
            flat_score.getElementsByOffset(start, end, includeEndBoundary=False)
        )

        # Vessel 1 — Flux Rate: distinct attack points per unit time
        offsets = [float(e.offset) for e in elements]
        flux_rate = len(set(offsets)) / window_size

        # Vessel 2 — Temporal Gestalts: average note duration
        durations = [float(e.duration.quarterLength) for e in elements]
        avg_gestalt = float(np.mean(durations)) if durations else 0.0

        # Collect pitches for vessels 3 & 4
        pitches: list[music21.pitch.Pitch] = []
        for e in elements:
            if e.isNote:
                pitches.append(e.pitch)
            elif e.isChord:
                pitches.extend(e.pitches)

        # Vessel 3 — Tension Index: weighted interval vector (Tosar hybrid)
        tension_index = 0.0
        if pitches:
            try:
                iv = music21.chord.Chord(pitches).intervalVector
                tension_index = float(sum(v * w for v, w in zip(iv, _TENSION_WEIGHTS)))
            except Exception:
                pass

        # Vessel 4 — Information Entropy: pitch-class unpredictability (Mailman)
        pitch_classes = [p.pitchClass for p in pitches]
        entropy = 0.0
        if pitch_classes:
            counts = pd.Series(pitch_classes).value_counts(normalize=True)
            entropy = float(-np.sum(counts.values * np.log2(counts.values + 1e-9)))

        # Vessel 5 & 6 — Polyphonic Density
        vertical_density, poly_activity = get_polyphonic_density(elements)

        results.append(
            {
                "start_beat": float(start),
                "flux_rate": flux_rate,
                "avg_gestalt": avg_gestalt,
                "tension_index": tension_index,
                "entropy": entropy,
                "vertical_density": vertical_density,
                "poly_activity": poly_activity,
            }
        )

    return pd.DataFrame(results)


def normalize_vessels(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize vessel metrics to [0, 1] and add relative_time column."""
    df = df.copy()
    cols = [
        "flux_rate",
        "avg_gestalt",
        "tension_index",
        "entropy",
        "vertical_density",
        "poly_activity",
    ]
    available = [c for c in cols if c in df.columns]
    if available and len(df) > 1:
        scaler = MinMaxScaler()
        df[available] = scaler.fit_transform(df[available])
    max_beat = df["start_beat"].max() if not df.empty else 1.0
    df["relative_time"] = df["start_beat"] / max_beat if max_beat > 0 else 0.0
    return df


def _plots_per_metric(df: pd.DataFrame, x_col: str, suffix: str) -> dict[str, str]:
    """Generate one chart per vessel metric; return dict of {metric: base64 PNG}."""
    x_label = "Relative Time (0 → 1)" if x_col == "relative_time" else "Start Beat"
    charts: dict[str, str] = {}

    for metric, color in _VESSEL_COLORS.items():
        if metric not in df.columns:
            continue

        fig, ax = plt.subplots(figsize=(10, 3))
        fig.patch.set_facecolor("#0d1223")
        ax.set_facecolor("#161f38")

        ax.plot(df[x_col], df[metric], color=color, lw=2.5, alpha=0.9)
        ax.fill_between(df[x_col], df[metric], alpha=0.15, color=color)

        label = _VESSEL_LABELS[metric]
        ax.set_title(f"{label} — {suffix}", color="#f8f5eb", fontsize=11, pad=10)
        ax.set_xlabel(x_label, color="#ece7d8", fontsize=9)
        ax.set_ylabel(label, color="#ece7d8", fontsize=9)
        ax.tick_params(colors="#ece7d8", labelsize=8)
        for spine in ax.spines.values():
            spine.set_color((1.0, 1.0, 1.0, 0.12))
        ax.grid(True, alpha=0.12, color="white")
        plt.tight_layout()

        buf = BytesIO()
        fig.savefig(
            buf,
            format="png",
            bbox_inches="tight",
            facecolor=fig.get_facecolor(),
            dpi=110,
        )
        plt.close(fig)
        buf.seek(0)
        charts[metric] = base64.b64encode(buf.read()).decode("utf-8")

    return charts


def analyze_file_for_api(score_path: str) -> dict:
    """
    Full vessel pipeline for a single file.
    Returns a JSON-serializable dict with raw/normalized data and per-metric base64 charts.
    """
    raw_df = analyze_temporal_vessels(score_path)

    if raw_df.empty:
        return {"error": "El archivo no contiene notas o no pudo ser analizado."}

    norm_df = normalize_vessels(raw_df)

    peak_entropy_idx = int(raw_df["entropy"].idxmax())
    peak_tension_idx = int(raw_df["tension_index"].idxmax())

    summary = {
        "total_windows": len(raw_df),
        "total_beats": float(raw_df["start_beat"].max() + WINDOW_SIZE),
        "avg_flux_rate": float(raw_df["flux_rate"].mean()),
        "avg_entropy": float(raw_df["entropy"].mean()),
        "avg_tension": float(raw_df["tension_index"].mean()),
        "avg_gestalt": float(raw_df["avg_gestalt"].mean()),
        "peak_entropy_beat": float(raw_df.loc[peak_entropy_idx, "start_beat"]),
        "peak_tension_beat": float(raw_df.loc[peak_tension_idx, "start_beat"]),
        "avg_vertical_density": float(raw_df["vertical_density"].mean()),
        "avg_poly_activity": float(raw_df["poly_activity"].mean()),
    }

    return {
        "windows": raw_df.to_dict(orient="records"),
        "windows_normalized": norm_df.to_dict(orient="records"),
        "summary": summary,
        "graficos_normalized": _plots_per_metric(norm_df, "relative_time", "Normalized"),
        "graficos_raw": _plots_per_metric(raw_df, "start_beat", "Raw"),
    }
