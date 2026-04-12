from __future__ import annotations

import base64
from io import BytesIO

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from music21 import converter, interval


def _outer_pitches(ch):
    """Devuelve (grave, aguda) usando los extremos del acorde."""
    if len(ch.pitches) < 2:
        return None
    ordered = sorted(ch.pitches, key=lambda p: p.midi)
    return ordered[0], ordered[-1]


def analizar_polifonia(file_path):
    # Cargar archivo (.krn o .xml)
    s = converter.parse(file_path)
    # Extraer solo las partes (voces) superiores e inferiores
    voices = s.parts
    if len(voices) < 2:
        return "Se necesitan al menos dos voces."

    v1 = voices[0].flatten().notes
    v2 = voices[1].flatten().notes

    # Sincronizar voces (chordify es útil para manejar ritmos distintos)
    combined = s.chordify()
    data_corpus = []

    previous_chord = None

    for current_chord in combined.recurse().getElementsByClass("Chord"):
        if previous_chord is None:
            previous_chord = current_chord
            continue

        curr_outer = _outer_pitches(current_chord)
        prev_outer = _outer_pitches(previous_chord)

        # Saltar eventos sin al menos dos notas sonando.
        if curr_outer is None or prev_outer is None:
            previous_chord = current_chord
            continue

        curr_low, curr_high = curr_outer
        prev_low, prev_high = prev_outer

        # 1. Determinar intervalo actual (i_curr) en semitonos
        i_curr_obj = interval.Interval(curr_low, curr_high)
        i_curr_semi = abs(i_curr_obj.semitones) % 12
        # Ajuste para diferenciar 0 de 12
        if i_curr_semi == 0 and i_curr_obj.semitones != 0:
            i_curr_semi = 12

        # 2. Filtrar solo Consonancias Perfectas (0, 7, 12)
        if i_curr_semi in [0, 7, 12]:

            # 3. Determinar intervalo anterior (i_prev) simple
            i_prev_obj = interval.Interval(prev_low, prev_high)
            i_prev_semi = abs(i_prev_obj.semitones) % 12

            # 4. Determinar tipo de movimiento (Variable Independiente)
            # Extraemos el movimiento de cada nota individual
            v1_move = interval.Interval(prev_high, curr_high).semitones
            v2_move = interval.Interval(prev_low, curr_low).semitones

            mov_type = ""
            if v1_move > 0 and v2_move < 0 or v1_move < 0 and v2_move > 0:
                mov_type = "Contrario"
            elif (v1_move == 0 and v2_move != 0) or (v1_move != 0 and v2_move == 0):
                mov_type = "Oblicuo"
            elif v1_move == v2_move and v1_move != 0:
                mov_type = "Paralelo"
            elif v1_move * v2_move > 0:  # Misma dirección pero distinta magnitud
                mov_type = "Directo"
            else:
                mov_type = "Estático"

            # 5. Guardar en el Corpus
            data_corpus.append(
                {
                    "i_prev": i_prev_semi,
                    "mov": mov_type,
                    "i_curr": i_curr_semi,
                    "v1_delta": v1_move,  # Vector Lewin
                    "v2_delta": v2_move,  # Vector Lewin
                }
            )

        previous_chord = current_chord

    return data_corpus


def _figure_to_base64(fig):
    buffer = BytesIO()
    fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def generar_grafico_resultados(df):
    heatmap_data = pd.crosstab(df["i_prev"], df["i_curr"])

    fig, ax = plt.subplots(figsize=(8, 5))
    if heatmap_data.empty:
        ax.axis("off")
        ax.text(
            0.5,
            0.5,
            "No hay datos para graficar.",
            ha="center",
            va="center",
            fontsize=14,
        )
        return _figure_to_base64(fig)

    im = ax.imshow(heatmap_data.values, aspect="auto", cmap="Blues")

    ax.set_title("Frecuencia de transiciones: i_prev -> i_curr")
    ax.set_xlabel("i_curr")
    ax.set_ylabel("i_prev")
    ax.set_xticks(range(len(heatmap_data.columns)))
    ax.set_xticklabels(heatmap_data.columns)
    ax.set_yticks(range(len(heatmap_data.index)))
    ax.set_yticklabels(heatmap_data.index)

    for i in range(heatmap_data.shape[0]):
        for j in range(heatmap_data.shape[1]):
            value = heatmap_data.iat[i, j]
            if value > 0:
                ax.text(j, i, str(value), ha="center", va="center", color="black")

    fig.colorbar(im, ax=ax, label="Frecuencia")
    fig.tight_layout()
    return _figure_to_base64(fig)


def generar_grafico_movimientos(df):
    orden = ["Contrario", "Oblicuo", "Paralelo", "Directo", "Estático"]
    mov_counts = df["mov"].value_counts().reindex(orden, fill_value=0)

    fig, ax = plt.subplots(figsize=(8, 5))
    if mov_counts.sum() == 0:
        ax.axis("off")
        ax.text(
            0.5,
            0.5,
            "No hay datos para graficar movimientos.",
            ha="center",
            va="center",
            fontsize=14,
        )
        return _figure_to_base64(fig)

    bars = ax.bar(mov_counts.index, mov_counts.values, color="#2E86AB")

    ax.set_title("Frecuencia por tipo de movimiento")
    ax.set_xlabel("Movimiento")
    ax.set_ylabel("Cantidad")
    ax.grid(axis="y", linestyle="--", alpha=0.4)

    for bar in bars:
        height = int(bar.get_height())
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            height + 0.2,
            str(height),
            ha="center",
            va="bottom",
        )

    fig.tight_layout()
    return _figure_to_base64(fig)


def analizar_archivo(file_path):
    resultados = analizar_polifonia(file_path)
    if isinstance(resultados, str):
        return {"error": resultados}

    df = pd.DataFrame(resultados)
    if df.empty:
        return {
            "resultados": [],
            "grafico_resultados": None,
            "grafico_movimientos": None,
            "total_eventos": 0,
        }

    tabla_mediacion = pd.crosstab(df["i_prev"], [df["i_curr"], df["mov"]])
    tabla_mediacion = tabla_mediacion.reset_index()
    tabla_mediacion.columns = [
        (
            "i_prev"
            if isinstance(col, tuple) and col[0] == "i_prev"
            else "_".join(map(str, col)) if isinstance(col, tuple) else str(col)
        )
        for col in tabla_mediacion.columns
    ]

    return {
        "resultados": df.to_dict(orient="records"),
        "tabla_mediacion": tabla_mediacion.to_dict(orient="records"),
        "grafico_resultados": generar_grafico_resultados(df),
        "grafico_movimientos": generar_grafico_movimientos(df),
        "total_eventos": int(len(df)),
    }


if __name__ == "__main__":
    resultados = analizar_archivo("Binchois.musicxml")
    if "error" in resultados:
        print(resultados["error"])
    else:
        print(f"Eventos analizados: {resultados['total_eventos']}")
