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

    for current_chord in combined.recurse().getElementsByClass('Chord'):
        if previous_chord is None:
            previous_chord = current_chord
            continue

        # 1. Determinar intervalo actual (i_curr) en semitonos
        i_curr_obj = current_chord.intervals[0] # Intervalo entre las dos voces
        i_curr_semi = abs(i_curr_obj.semitones) % 12 
        # Ajuste para diferenciar 0 de 12
        if i_curr_semi == 0 and i_curr_obj.semitones != 0:
            i_curr_semi = 12

        # 2. Filtrar solo Consonancias Perfectas (0, 7, 12)
        if i_curr_semi in [0, 7, 12]:
            
            # 3. Determinar intervalo anterior (i_prev) simple
            i_prev_obj = previous_chord.intervals[0]
            i_prev_semi = abs(i_prev_obj.semitones) % 12
            
            # 4. Determinar tipo de movimiento (Variable Independiente)
            # Extraemos el movimiento de cada nota individual
            v1_move = interval.notesToInterval(previous_chord[0], current_chord[0]).semitones
            v2_move = interval.notesToInterval(previous_chord[1], current_chord[1]).semitones
            
            mov_type = ""
            if v1_move > 0 and v2_move < 0 or v1_move < 0 and v2_move > 0:
                mov_type = "Contrario"
            elif (v1_move == 0 and v2_move != 0) or (v1_move != 0 and v2_move == 0):
                mov_type = "Oblicuo"
            elif v1_move == v2_move and v1_move != 0:
                mov_type = "Paralelo"
            elif v1_move * v2_move > 0: # Misma dirección pero distinta magnitud
                mov_type = "Directo"
            else:
                mov_type = "Estático"

            # 5. Guardar en el Corpus
            data_corpus.append({
                'i_prev': i_prev_semi,
                'mov': mov_type,
                'i_curr': i_curr_semi,
                'v1_delta': v1_move, # Vector Lewin
                'v2_delta': v2_move  # Vector Lewin
            })

        previous_chord = current_chord

    return data_corpus

# Ejemplo de uso
# resultados = analizar_polifonia('mi_pieza.krn')











import pandas as pd

df = pd.DataFrame(resultados)
# Tabla que muestra qué movimiento se prefiere para llegar a cada intervalo perfecto
tabla_mediacion = pd.crosstab(df['i_prev'], [df['i_curr'], df['mov']])
print(tabla_mediacion)




import os
import pandas as pd
from music21 import converter

def procesar_corpus(directorio_raiz):
    todo_el_corpus = []
    
    # Recorrer carpetas (ej: '1500-1600', '1600-1700')
    for root, dirs, files in os.walk(directorio_raiz):
        for file in files:
            if file.endswith(('.krn', '.xml', '.mxl')):
                path = os.path.join(root, file)
                periodo = os.path.basename(root) # Carpeta como etiqueta temporal
                
                try:
                    # Llamamos a la función anterior 'analizar_polifonia'
                    datos_pieza = analizar_polifonia(path)
                    for entrada in datos_pieza:
                        entrada['periodo'] = periodo
                        entrada['obra'] = file
                        todo_el_corpus.append(entrada)
                except Exception as e:
                    print(f"Error en {file}: {e}")
                    
    return pd.DataFrame(todo_el_corpus)

# df_final = procesar_corpus('./mi_corpus_musical')
