import music21
import pandas as pd
import numpy as np
import math

def analyze_temporal_vessels(score_path, window_size=4.0):
    """
    Analiza una obra bajo los 4 vessels de la teoría dinámica.
    window_size: Tamaño de la ventana en 'quarter lengths' (beats).
    """
    score = music21.converter.parse(score_path)
    # Extraer todas las notas/acordes en una línea de tiempo plana
    flat_score = score.flatten().notes
    
    # Definir el rango temporal
    total_duration = score.quarterLength
    windows = np.arange(0, total_duration, window_size)
    
    results = []

    for start in windows:
        end = start + window_size
        # Filtrar elementos en esta ventana (vessel)
        elements = flat_score.getElementsByOffset(start, end, includeEndBoundary=False)
        
        # --- VESSEL 1: FLUX-RATE (Densidad de cambio) ---
        # Medimos la cantidad de ataques (offsets distintos) por unidad de tiempo
        offsets = [float(e.offset) for e in elements]
        flux_rate = len(set(offsets)) / window_size

        # --- VESSEL 2: TEMPORAL GESTALTS (Unidades de atención) ---
        # Promedio de duraciones: ¿Son gestaltes largos (lentos) o breves (densos)?
        durations = [float(e.duration.quarterLength) for e in elements]
        avg_gestalt_length = np.mean(durations) if durations else 0

        # --- VESSEL 3: VECTORES DE TENSIÓN (Híbrido Tosar) ---
        # Calculamos el Interval Vector (densidad cromática) de la ventana
        # Esto mide la "fricción" o carga energética del segmento
        pitches = []
        for e in elements:
            if e.isNote: pitches.append(e.pitch)
            elif e.isChord: pitches.extend(e.pitches)
        
        if pitches:
            pc_set = music21.chord.Chord(pitches).pitchClassSet
            # El Interval Vector representa la 'energía' interna (Tosar)
            interval_vector = music21.chord.Chord(pitches).intervalVector
            tension_index = sum([iv * weight for iv, weight in zip(interval_vector, [10, 5, 2, 1, 1, 0.5])])
        else:
            tension_index = 0

        # --- VESSEL 4: ENTROPÍA DE INFORMACIÓN (Mailman puro) ---
        # ¿Qué tan impredecible es el contenido de alturas en esta ventana?
        pitch_classes = [p.pitchClass for p in pitches]
        entropy = 0
        if pitch_classes:
            counts = pd.Series(pitch_classes).value_counts(normalize=True)
            entropy = -sum(counts * np.log2(counts))

        results.append({
            'start_beat': start,
            'flux_rate': flux_rate,
            'avg_gestalt': avg_gestalt_length,
            'tension_index': tension_index,
            'entropy': entropy
        })

    return pd.DataFrame(results)

# Ejemplo de uso:
# df = analyze_temporal_vessels('ruta/a/tu/archivo.krn')
# print(df.head())







from sklearn.preprocessing import MinMaxScaler

def normalize_vessels(df):
    """
    Normaliza los resultados para que sean comparables entre obras 
    de distinta duración y densidad.
    """
    scaler = MinMaxScaler()
    # Columnas a normalizar
    cols = ['flux_rate', 'avg_gestalt', 'tension_index', 'entropy']
    
    # Aplicamos escalamiento min-max
    df[cols] = scaler.fit_transform(df[cols])
    
    # Añadimos 'Relative Time' (0.0 a 1.0) para mapear la estructura formal
    df['relative_time'] = df['start_beat'] / df['start_beat'].max()
    
    return df

def get_corpus_profile(df_list):
    """
    Recibe una lista de DataFrames (uno por obra) y devuelve 
    la "huella digital" promedio del tiempo musical para ese corpus.
    """
    combined = pd.concat(df_list)
    # Agrupamos por tiempo relativo (deciles) para ver la evolución promedio
    combined['time_decile'] = (combined['relative_time'] * 10).round() / 10
    
    profile = combined.groupby('time_decile')[['flux_rate', 'tension_index', 'entropy']].mean()
    return profile










import os
import matplotlib.pyplot as plt

def batch_process_corpus(corpus_root):
    """
    Recorre el corpus, analiza cada obra y la etiqueta por periodo.
    corpus_root: Carpeta con subcarpetas ['Renacimiento', 'Barroco', 'Siglo_XX', ...]
    """
    all_period_data = {}

    for period in os.listdir(corpus_root):
        period_path = os.path.join(corpus_root, period)
        if not os.path.isdir(period_path): continue
        
        print(f"Procesando periodo: {period}...")
        period_dfs = []
        
        for file in os.listdir(period_path):
            if file.endswith(('.mid', '.xml', '.krn')):
                try:
                    # Usamos la función anterior con normalización
                    raw_df = analyze_temporal_vessels(os.path.join(period_path, file))
                    norm_df = normalize_vessels(raw_df)
                    period_dfs.append(norm_df)
                except Exception as e:
                    print(f"Error en {file}: {e}")

        if period_dfs:
            # Generamos el perfil promedio del periodo (Vessel de Perfil Histórico)
            all_period_data[period] = get_corpus_profile(period_dfs)
            
    return all_period_data








def plot_historical_evolution(all_period_data, metric='entropy'):
    """
    Grafica una métrica específica a través de todos los periodos.
    """
    plt.figure(figsize=(12, 6))
    
    for period, profile in all_period_data.items():
        # Graficamos la métrica elegida a lo largo del 'relative_time' de la obra promedio
        plt.plot(profile.index, profile[metric], label=period, lw=2)
    
    plt.title(f"Evolución de la {metric.capitalize()} en el Tiempo Musical Occidental")
    plt.xlabel("Progreso relativo de la obra (0.0 - 1.0)")
    plt.ylabel("Valor Normalizado")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.show()




    def get_polyphonic_density(elements, window_size):
    """
    Calcula la densidad de voces y la actividad rítmica independiente.
    """
    if not elements:
        return 0, 0
    
    # 1. Voces Simultáneas (Densidad Vertical)
    # Contamos cuántas notas o voces distintas suenan en promedio
    voice_counts = []
    for e in elements:
        if e.isChord:
            voice_counts.append(len(e.pitches))
        elif e.isNote:
            voice_counts.append(1)
    
    avg_vertical_density = np.mean(voice_counts) if voice_counts else 0
    
    # 2. Índice de Actividad (Contrapunto)
    # Medimos la 'independencia' rítmica: ataques por voz en la ventana
    total_attacks = len(elements)
    polyphonic_activity = total_attacks / avg_vertical_density if avg_vertical_density > 0 else 0
    
    return avg_vertical_density, polyphonic_activity

# Integración en el loop principal (analyze_temporal_vessels):
# ... dentro del for start in windows ...
    v_density, p_activity = get_polyphonic_density(elements, window_size)
    
    results.append({
        'start_beat': start,
        'flux_rate': flux_rate,
        'avg_gestalt': avg_gestalt_length,
        'tension_index': tension_index,
        'entropy': entropy,
        'vertical_density': v_density,
        'poly_activity': p_activity
    })












    import seaborn as sns

def plot_decile_comparison(all_period_data, metric='entropy'):
    """
    Compara la forma temporal de diferentes periodos usando deciles.
    """
    plt.figure(figsize=(12, 7))
    sns.set_style("whitegrid")
    
    for period, profile in all_period_data.items():
        # Suavizamos la curva para mejor visualización transhistórica
        x = profile.index * 100  # Convertir a porcentaje 0-100%
        y = profile[metric].rolling(window=2, min_periods=1).mean()
        
        plt.plot(x, y, label=period, lw=3, alpha=0.8)
    
    plt.title(f"Arquetipo Temporal Occidental: {metric.upper()} por Periodo", fontsize=15)
    plt.xlabel("Progreso de la Obra (%)", fontsize=12)
    plt.ylabel(f"Valor Promedio de {metric.capitalize()}", fontsize=12)
    plt.legend(title="Periodos", bbox_to_anchor=(1.05, 1), loc='upper left')
    plt.tight_layout()
    plt.show()