from __future__ import annotations

import base64
import re
import warnings
from io import BytesIO
from pathlib import Path

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

_SUMMARY_METRICS = [
    "flux_rate",
    "avg_gestalt",
    "tension_index",
    "entropy",
    "vertical_density",
    "poly_activity",
]


def _century_ordinal(n: int) -> str:
    suffix = (
        {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        if n % 100 not in (11, 12, 13)
        else "th"
    )
    return f"{n}{suffix} c."


# ──────────────────────────────────────────────────────────────────────────────
# Core helpers
# ──────────────────────────────────────────────────────────────────────────────

def get_polyphonic_density(elements):
    """Returns (avg_vertical_density, polyphonic_activity)."""
    if not elements:
        return 0.0, 0.0
    voice_counts = [
        len(e.pitches) if e.isChord else 1 for e in elements if e.isChord or e.isNote
    ]
    avg = float(np.mean(voice_counts)) if voice_counts else 0.0
    activity = len(elements) / avg if avg > 0 else 0.0
    return avg, activity


def extract_century(score: music21.stream.Score, filename: str) -> int | None:
    """
    Extract century from an already-parsed music21 Score object.
    Tries metadata date fields first; falls back to filename pattern XX.YYYY-ZZZZ_Name.
    """
    try:
        meta = score.metadata
        for attr in ("date", "dateCreated", "dateFirstPublished", "dateModified"):
            val = getattr(meta, attr, None)
            if val is None:
                continue
            year: int | None = None
            if hasattr(val, "year") and val.year:
                year = int(val.year)
            else:
                m = re.search(r"\b(\d{4})\b", str(val))
                if m:
                    year = int(m.group(1))
            if year:
                return (year - 1) // 100 + 1
    except Exception:
        pass

    # Filename fallback: XX.YYYY-ZZZZ_Name  or  XX_…  or  XX-…
    stem = Path(filename).stem
    m = re.match(r"^(\d{2})[.\-_]", stem)
    if m:
        return int(m.group(1))
    return None


# ──────────────────────────────────────────────────────────────────────────────
# Analysis core
# ──────────────────────────────────────────────────────────────────────────────

def _analyze_vessels_from_score(
    score: music21.stream.Score, window_size: float = WINDOW_SIZE
) -> pd.DataFrame:
    """
    Run temporal vessel analysis on an already-parsed Score.
    Uses pre-sorted offset array + bisect instead of getElementsByOffset
    to avoid O(n) scans per window.
    """
    flat_notes = score.flatten().notes

    # Build a sorted list once — O(n log n) upfront, O(log n) per window after
    pairs: list[tuple[float, object]] = sorted(
        ((float(e.offset), e) for e in flat_notes), key=lambda x: x[0]
    )
    offsets = np.array([o for o, _ in pairs], dtype=float)

    total_duration = float(score.quarterLength)
    windows = np.arange(0, total_duration, window_size)

    results = []
    for start in windows:
        end = start + window_size
        lo = int(np.searchsorted(offsets, start, side="left"))
        hi = int(np.searchsorted(offsets, end, side="left"))
        elements = [e for _, e in pairs[lo:hi]]

        # Vessel 1 — Flux Rate
        attack_offsets = {offsets[lo + i] for i in range(hi - lo)}
        flux_rate = len(attack_offsets) / window_size

        # Vessel 2 — Avg Gestalt
        durations = [float(e.duration.quarterLength) for e in elements]
        avg_gestalt = float(np.mean(durations)) if durations else 0.0

        # Collect pitches for tension + entropy
        pitches: list[music21.pitch.Pitch] = []
        for e in elements:
            if e.isNote:
                pitches.append(e.pitch)
            elif e.isChord:
                pitches.extend(e.pitches)

        # Vessel 3 — Tension Index
        tension_index = 0.0
        if pitches:
            try:
                iv = music21.chord.Chord(pitches).intervalVector
                tension_index = float(
                    sum(v * w for v, w in zip(iv, _TENSION_WEIGHTS))
                )
            except Exception:
                pass

        # Vessel 4 — Entropy
        entropy = 0.0
        if pitches:
            pcs = [p.pitchClass for p in pitches]
            counts = pd.Series(pcs).value_counts(normalize=True)
            entropy = float(-np.sum(counts.values * np.log2(counts.values + 1e-9)))

        # Vessels 5 & 6 — Polyphonic Density
        v_density, p_activity = get_polyphonic_density(elements)

        results.append(
            {
                "start_beat": float(start),
                "flux_rate": flux_rate,
                "avg_gestalt": avg_gestalt,
                "tension_index": tension_index,
                "entropy": entropy,
                "vertical_density": v_density,
                "poly_activity": p_activity,
            }
        )

    return pd.DataFrame(results)


def analyze_temporal_vessels(
    score_path: str, window_size: float = WINDOW_SIZE
) -> pd.DataFrame:
    """Public wrapper: parse path then run the analysis."""
    score = music21.converter.parse(score_path)
    return _analyze_vessels_from_score(score, window_size)


def normalize_vessels(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    cols = [
        "flux_rate", "avg_gestalt", "tension_index",
        "entropy", "vertical_density", "poly_activity",
    ]
    available = [c for c in cols if c in df.columns]
    if available and len(df) > 1:
        df[available] = MinMaxScaler().fit_transform(df[available])
    max_beat = df["start_beat"].max() if not df.empty else 1.0
    df["relative_time"] = df["start_beat"] / max_beat if max_beat > 0 else 0.0
    return df


# ──────────────────────────────────────────────────────────────────────────────
# Chart helpers
# ──────────────────────────────────────────────────────────────────────────────

def _plots_per_metric(df: pd.DataFrame, x_col: str, suffix: str) -> dict[str, str]:
    """One chart per metric; returns {metric: base64 PNG}."""
    x_label = "Relative Time (0 → 1)" if x_col == "relative_time" else "Start Beat"
    charts: dict[str, str] = {}

    for metric, color in _VESSEL_COLORS.items():
        if metric not in df.columns:
            continue

        fig, ax = plt.subplots(figsize=(9, 2.5))
        fig.patch.set_facecolor("#0d1223")
        ax.set_facecolor("#161f38")
        ax.plot(df[x_col], df[metric], color=color, lw=2.0, alpha=0.9)
        ax.fill_between(df[x_col], df[metric], alpha=0.13, color=color)

        label = _VESSEL_LABELS[metric]
        ax.set_title(f"{label} — {suffix}", color="#f8f5eb", fontsize=10, pad=8)
        ax.set_xlabel(x_label, color="#ece7d8", fontsize=8)
        ax.set_ylabel(label, color="#ece7d8", fontsize=8)
        ax.tick_params(colors="#ece7d8", labelsize=7)
        for spine in ax.spines.values():
            spine.set_color((1.0, 1.0, 1.0, 0.12))
        ax.grid(True, alpha=0.1, color="white")
        plt.tight_layout()

        buf = BytesIO()
        fig.savefig(buf, format="png", bbox_inches="tight",
                    facecolor=fig.get_facecolor(), dpi=85)
        plt.close(fig)
        buf.seek(0)
        charts[metric] = base64.b64encode(buf.read()).decode("utf-8")

    return charts


def _century_profile_chart(df: pd.DataFrame) -> str:
    available = [m for m in _SUMMARY_METRICS if m in df.columns]
    x = np.arange(len(available))

    norm_df = df.copy()
    for m in available:
        col = df[m].astype(float)
        mn, mx = col.min(), col.max()
        norm_df[m] = (
            (col - mn) / (mx - mn)
            if mx > mn
            else pd.Series([0.5] * len(col), index=col.index)
        )

    tab10 = plt.cm.get_cmap("tab10").colors  # type: ignore[attr-defined]

    fig, ax = plt.subplots(figsize=(12, 5))
    fig.patch.set_facecolor("#0d1223")
    ax.set_facecolor("#161f38")

    for idx, (_, row) in enumerate(norm_df.iterrows()):
        raw_row = df.iloc[idx]
        century_val = raw_row.get("century", "?")
        try:
            label = _century_ordinal(int(century_val))
        except (ValueError, TypeError):
            label = str(century_val)
        n_files = int(raw_row.get("file_count", 1))

        y = [float(row[m]) for m in available]
        color = tab10[idx % len(tab10)]
        ax.plot(x, y, marker="o", lw=2.2, color=color, alpha=0.9,
                label=f"{label}  (n={n_files})")
        ax.fill_between(x, y, alpha=0.06, color=color)

    ax.set_xticks(x)
    ax.set_xticklabels(
        [_VESSEL_LABELS[m] for m in available],
        rotation=20, ha="right", color="#ece7d8", fontsize=9,
    )
    ax.set_ylabel("Normalized mean (0 → 1)", color="#ece7d8", fontsize=9)
    ax.set_title("Century Vessel Profiles", color="#f8f5eb", fontsize=12, pad=12)
    ax.tick_params(colors="#ece7d8", labelsize=8)
    for spine in ax.spines.values():
        spine.set_color((1.0, 1.0, 1.0, 0.12))
    ax.legend(facecolor="#1a2240", labelcolor="#ece7d8", framealpha=0.85,
              fontsize=9, loc="upper right")
    ax.grid(True, alpha=0.12, color="white", axis="y")
    ax.set_ylim(-0.05, 1.1)
    plt.tight_layout()

    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight",
                facecolor=fig.get_facecolor(), dpi=100)
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────

def analyze_file_for_api(score_path: str, filename: str = "") -> dict:
    """
    Full pipeline for one file.
    Parses the score exactly once and reuses it for analysis + century extraction.
    """
    score = music21.converter.parse(score_path)

    raw_df = _analyze_vessels_from_score(score)
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

    # Reuse the already-parsed score — no second parse
    century = extract_century(score, filename) if filename else None

    return {
        "century": century,
        "windows": raw_df.to_dict(orient="records"),
        "windows_normalized": norm_df.to_dict(orient="records"),
        "summary": summary,
        "graficos_normalized": _plots_per_metric(norm_df, "relative_time", "Normalized"),
        "graficos_raw": _plots_per_metric(raw_df, "start_beat", "Raw"),
    }


def compute_century_summary(file_results: list[dict]) -> dict:
    metric_map = {
        "flux_rate": "avg_flux_rate",
        "avg_gestalt": "avg_gestalt",
        "tension_index": "avg_tension",
        "entropy": "avg_entropy",
        "vertical_density": "avg_vertical_density",
        "poly_activity": "avg_poly_activity",
    }

    rows = []
    unknown: list[str] = []
    for fr in file_results:
        century = fr.get("century")
        summary = fr.get("summary", {})
        if century is None:
            unknown.append(fr.get("filename", "?"))
            continue
        row = {"century": century}
        for dest, src in metric_map.items():
            row[dest] = float(summary.get(src, 0.0))
        rows.append(row)

    if not rows:
        return {"rows": [], "chart": None, "files_without_century": unknown}

    df = pd.DataFrame(rows)
    grouped = (
        df.groupby("century")
        .agg(
            file_count=("flux_rate", "count"),
            flux_rate=("flux_rate", "mean"),
            avg_gestalt=("avg_gestalt", "mean"),
            tension_index=("tension_index", "mean"),
            entropy=("entropy", "mean"),
            vertical_density=("vertical_density", "mean"),
            poly_activity=("poly_activity", "mean"),
        )
        .reset_index()
        .sort_values("century")
    )

    return {
        "rows": grouped.to_dict(orient="records"),
        "chart": _century_profile_chart(grouped),
        "files_without_century": unknown,
    }
