def analyze_performance_utz(stream_performance, stream_score, window_seconds=2.0):
    """
    Compara la partitura ideal con la performance (Teoría de Utz).
    Mide la desviación temporal y la micro-dinámica.
    """
    # Sincronizamos ambos flujos (asumiendo que están alineados)
    perf_notes = stream_performance.flatten().notes
    score_notes = stream_score.flatten().notes

    results = []
    # El tiempo ahora es cronométrico (segundos), no por beats
    total_time = stream_performance.seconds
    windows = np.arange(0, total_time, window_seconds)

    for start in windows:
        end = start + window_seconds
        perf_elements = perf_notes.getElementsByOffset(
            start, end, includeEndBoundary=False
        )

        # --- VESSEL UTZ 1: DESVIACIÓN TEMPORAL (Agógica) ---
        # Calculamos el ratio entre el tiempo ejecutado y el tiempo escrito
        # Un ratio > 1 indica un 'ritardando' o expansión interpretativa
        actual_durations = [n.duration.quarterLength for n in perf_elements]
        # (Aquí se requeriría una lógica de matching nota a nota para precisión extrema)

        # --- VESSEL UTZ 2: ENERGÍA DINÁMICA ---
        # Utz analiza el 'shaping' a través de la velocidad
        velocities = [
            n.volume.velocity for n in perf_elements if n.volume.velocity is not None
        ]
        avg_velocity = np.mean(velocities) if velocities else 0
        std_velocity = (
            np.std(velocities) if velocities else 0
        )  # Variabilidad (acentuación)

        # --- RE-CÁLCULO DE MAILMAN (Entropía en tiempo real) ---
        # La entropía de Mailman cambia si el intérprete agrupa las notas de forma distinta
        pitch_classes = [n.pitch.pitchClass for n in perf_elements if n.isNote]
        counts = pd.Series(pitch_classes).value_counts(normalize=True)
        perf_entropy = -sum(counts * np.log2(counts)) if not counts.empty else 0

        results.append(
            {
                "time_sec": start,
                "tempo_flex": len(perf_elements) / window_seconds,  # Flux real
                "dynamic_shape": avg_velocity,
                "accentuation_index": std_velocity,
                "performed_entropy": perf_entropy,
            }
        )

    return pd.DataFrame(results)


import librosa
import numpy as np
import pandas as pd


def analyze_audio_performance(audio_path, hop_length=512):
    """
    Extrae descriptores de audio para mapear las teorías de Utz y Mailman.
    """
    y, sr = librosa.load(audio_path)

    # --- VESSEL 1: DINÁMICA (Utz - Shaping) ---
    # RMS mide la potencia del audio, equivalente a la intensidad interpretativa
    rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

    # --- VESSEL 2: FLUJO ESPECTRAL (Mailman - Flux) ---
    # Mide qué tan rápido cambia el espectro (densidad de información sonora)
    spec_flux = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)

    # --- VESSEL 3: TEMPO DINÁMICO (Utz - Agógica) ---
    # Extraemos el tempo estimado momento a momento
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    prior_tempogram = librosa.feature.tempogram(
        onset_envelope=onset_env, sr=sr, hop_length=hop_length
    )
    # Promedio de tempo por ventana (simplificado)
    local_tempo = np.mean(prior_tempogram, axis=0)

    # Normalización de tiempos para el DataFrame
    times = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop_length)

    df_audio = pd.DataFrame(
        {
            "time_sec": times,
            "dynamic_intensity": rms,
            "spectral_flux": spec_flux,
            "local_tempo": local_tempo,
        }
    )

    return df_audio


import librosa
import librosa.display
from dtw import dtw


def align_score_to_audio(score_path, audio_path):
    # 1. Cargar audio y extraer Cromograma
    y, sr = librosa.load(audio_path)
    chroma_audio = librosa.feature.chroma_stft(y=y, sr=sr)

    # 2. Sintetizar la partitura a croma (usando music21)
    score = music21.converter.parse(score_path)
    # Creamos un croma sintético a partir de los offsets de la partitura
    # (Simplificado: asumiendo una tasa de frames constante)
    chroma_score = generate_score_chroma(score)

    # 3. Calcular DTW
    # dist: distancia total, cost_matrix: matriz de alineación
    dist, cost_matrix, acc_cost_matrix, path = librosa.sequence.dtw(
        X=chroma_score, Y=chroma_audio, metric="cosine"
    )

    return path, times_audio, times_score


def calculate_utz_elasticity(path, sr, hop_length):
    """
    Calcula qué tan elástica es la performance frente a la partitura.
    """
    # El path[0] son los frames de la partitura, path[1] los del audio
    score_frames, audio_frames = path[0], path[1]

    # Derivamos el path para encontrar el 'Tempo Relativo'
    # Un valor de 1.0 significa que el intérprete va a la velocidad escrita
    elasticity_curve = np.diff(audio_frames) / np.diff(score_frames)

    return elasticity_curve


import concurrent.futures
from essentia.standard import MonoLoader, TensorflowPredictEffnetDiscogs, FrequencyBands

# Essentia es ideal para procesar miles de archivos por su velocidad en C++


def process_corpus_large_scale(file_list):
    """
    Paraleliza la extracción de descriptores Utz/Mailman/Tosar.
    """
    results_db = []

    with concurrent.futures.ProcessPoolExecutor() as executor:
        # Mapeamos la función de análisis a toda la lista de archivos
        future_to_file = {
            executor.submit(analyze_single_track, f): f for f in file_list
        }

        for future in concurrent.futures.as_completed(future_to_file):
            try:
                data = future.result()
                results_db.append(data)
            except Exception as e:
                print(f"Error procesando {future_to_file[future]}: {e}")

    return pd.DataFrame(results_db)


import os
import joblib
import pandas as pd
from joblib import Parallel, delayed


def process_and_save_chunk(file_batch, batch_index):
    """
    Procesa un pequeño grupo de archivos y guarda el resultado parcial.
    Esto evita perder datos si la PC se crashea o se queda sin RAM.
    """
    batch_results = []
    for score_f, audio_f in file_batch:
        try:
            # 1. Extracción (Mailman + Tosar)
            score_data = analyze_temporal_vessels(score_f)

            # 2. Performance (Utz via Audio)
            audio_data = analyze_audio_performance(audio_f)

            # 3. Alineación (DTW con restricciones para ahorrar RAM)
            # Usamos un 'hop_length' mayor para el DTW masivo
            path, _, _ = align_score_to_audio(score_f, audio_f)

            # 4. Síntesis
            final_data = merge_theories(score_data, audio_data, path)
            batch_results.append(final_data)
        except Exception as e:
            continue

    # Guardar en formato Parquet (mucho más rápido que CSV)
    df_batch = pd.DataFrame(batch_results)
    df_batch.to_parquet(f"results/batch_{batch_index}.parquet")


# Ejecución paralela usando todos los núcleos menos 2 (para no congelar la PC)
num_cores = os.cpu_count() - 2
Parallel(n_jobs=num_cores)(
    delayed(process_and_save_chunk)(chunk, i) for i, chunk in enumerate(file_chunks)
)


import pandas as pd
import glob
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import seaborn as sns


def generate_historical_map(parquet_dir):
    # 1. Cargar y consolidar todos los batches
    all_files = glob.glob(f"{parquet_dir}/*.parquet")
    df_list = [pd.read_parquet(f) for f in all_files]
    full_corpus = pd.concat(df_list, ignore_index=True)

    # 2. Selección de métricas para la "Teoría General"
    features = [
        "flux_rate",
        "entropy",
        "tension_index",
        "vertical_density",
        "poly_activity",
        "elasticity",
    ]

    # Limpiamos valores infinitos o NaNs comunes en el análisis de audio
    data = full_corpus[features].replace([np.inf, -np.inf], np.nan).dropna()
    periods = full_corpus.loc[data.index, "period"]  # Etiquetas (Barroco, etc.)

    # 3. Normalización (Z-score)
    x = StandardScaler().fit_transform(data)

    # 4. PCA: Reducir a 2 componentes principales
    pca = PCA(n_components=2)
    components = pca.fit_transform(x)

    pca_df = pd.DataFrame(
        data=components,
        columns=["PC1 (Energía/Complejidad)", "PC2 (Elasticidad/Estructura)"],
    )
    pca_df["Periodo"] = periods.values

    # 5. Visualización del "Mapa del Tiempo Musical"
    plt.figure(figsize=(14, 8))
    sns.scatterplot(
        x="PC1 (Energía/Complejidad)",
        y="PC2 (Elasticidad/Estructura)",
        hue="Periodo",
        data=pca_df,
        alpha=0.5,
        palette="viridis",
    )

    # Dibujar centroides por periodo (la "huella" de cada era)
    for p in pca_df["Periodo"].unique():
        subset = pca_df[pca_df["Periodo"] == p]
        plt.annotate(
            p,
            (
                subset["PC1 (Energía/Complejidad)"].mean(),
                subset["PC2 (Elasticidad/Estructura)"].mean(),
            ),
            fontsize=12,
            weight="bold",
            bbox=dict(facecolor="white", alpha=0.7),
        )

    plt.title("Teoría General del Tiempo: Mapa Evolutivo del Corpus")
    plt.show()

    return pca.explained_variance_ratio_
