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
}
_VESSEL_LABELS = {
    "flux_rate": "Flux Rate",
    "avg_gestalt": "Avg Gestalt",
    "tension_index": "Tension Index",
    "entropy": "Entropy",
}
_TENSION_WEIGHTS = [10.0, 5.0, 2.0, 1.0, 1.0, 0.5]


def analyze_temporal_vessels(score_path: str, window_size: float = WINDOW_SIZE) -> pd.DataFrame:
    """
    Analyze a score using the 4 temporal vessels from dynamic time theory.
    Returns one row per time window.
    """
    score = music21.converter.parse(score_path)
    flat_score = score.flatten().notes
    total_duration = float(score.quarterLength)
    windows = np.arange(0, total_duration, window_size)

    results = []
    for start in windows:
        end = start + window_size
        elements = list(flat_score.getElementsByOffset(start, end, includeEndBoundary=False))

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

        results.append(
            {
                "start_beat": float(start),
                "flux_rate": flux_rate,
                "avg_gestalt": avg_gestalt,
                "tension_index": tension_index,
                "entropy": entropy,
            }
        )

    return pd.DataFrame(results)


def normalize_vessels(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize vessel metrics to [0, 1] and add relative_time column."""
    df = df.copy()
    cols = ["flux_rate", "avg_gestalt", "tension_index", "entropy"]
    available = [c for c in cols if c in df.columns]
    if available and len(df) > 1:
        scaler = MinMaxScaler()
        df[available] = scaler.fit_transform(df[available])
    max_beat = df["start_beat"].max() if not df.empty else 1.0
    df["relative_time"] = df["start_beat"] / max_beat if max_beat > 0 else 0.0
    return df


def _plot_to_base64(df: pd.DataFrame, title: str, x_col: str) -> str:
    """Render a vessel profile line chart and return as base64-encoded PNG."""
    fig, ax = plt.subplots(figsize=(11, 4))
    fig.patch.set_facecolor("#0d1223")
    ax.set_facecolor("#161f38")

    for metric, color in _VESSEL_COLORS.items():
        if metric in df.columns:
            ax.plot(
                df[x_col],
                df[metric],
                label=_VESSEL_LABELS[metric],
                color=color,
                lw=2.5,
                alpha=0.9,
            )

    ax.set_title(title, color="#f8f5eb", fontsize=12, pad=12)
    x_label = "Relative Time (0 → 1)" if x_col == "relative_time" else "Start Beat"
    ax.set_xlabel(x_label, color="#ece7d8", fontsize=10)
    ax.set_ylabel("Value", color="#ece7d8", fontsize=10)
    ax.tick_params(colors="#ece7d8", labelsize=9)
    for spine in ax.spines.values():
        spine.set_color((1.0, 1.0, 1.0, 0.12))
    ax.legend(facecolor="#1a2240", labelcolor="#ece7d8", framealpha=0.85, fontsize=9)
    ax.grid(True, alpha=0.12, color="white")
    plt.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", facecolor=fig.get_facecolor(), dpi=120)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def analyze_file_for_api(score_path: str) -> dict:
    """
    Full vessel pipeline for a single file.
    Returns a JSON-serializable dict with raw/normalized data and base64 charts.
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
    }

    return {
        "windows": raw_df.to_dict(orient="records"),
        "windows_normalized": norm_df.to_dict(orient="records"),
        "summary": summary,
        "grafico_normalizado": _plot_to_base64(
            norm_df, "Vessel Profile — Normalized", x_col="relative_time"
        ),
        "grafico_raw": _plot_to_base64(raw_df, "Vessel Profile — Raw Values", x_col="start_beat"),
    }
