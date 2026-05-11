# MailmansVessels.py - Musical Temporal Analysis

## Overview

This Python script analyzes musical scores through the lens of **dynamic theory**, measuring four key "vessels" (dimensions) of temporal behavior in Western music. It combines musicological theory with data science to profile how music evolves across different historical periods.

---

## Core Concept: The Four Vessels

The analysis frames musical temporality around four interconnected dimensions:

### 1. **Flux-Rate** (Densidad de Cambio - Change Density)
- **What it measures:** How frequently musical events occur per unit of time
- **Calculation:** Counts distinct attack points (note onsets) within a time window divided by window size
- **Interpretation:** High flux-rate = rapid, dense activity; Low flux-rate = sparse, sparse gestures
- **Musical relevance:** Captures the "busyness" or rhythmic intensity of a passage

### 2. **Temporal Gestalts** (Unidades de Atención - Attention Units)
- **What it measures:** The average duration of musical gestures/notes in a window
- **Calculation:** Mean of quarter-length durations across all elements
- **Interpretation:** Longer gestalts = slower, sustained passages; Shorter = rapid, fragmented phrases
- **Musical relevance:** Reflects the perceptual "chunking" of musical time into meaningful units

### 3. **Tension Vectors** (Híbrido Tosar - Harmonic/Chromatic Energy)
- **What it measures:** The harmonic friction or energetic load of a segment
- **Calculation:** 
  - Extracts all pitch classes from the window
  - Computes the **Interval Vector** (chromatic distribution)
  - Weights intervals by their "harmonic weight" (perfect intervals get higher weights)
  - Sums weighted intervals to produce a tension index
- **Interpretation:** Higher tension = more dissonant/complex harmonies; Lower = simpler/consonant
- **Musical relevance:** Quantifies Tosar's idea of harmonic "weight" in temporal flow

### 4. **Information Entropy** (Entropía de Información - Predictability)
- **What it measures:** How unpredictable/varied the pitch-class content is
- **Calculation:** Shannon entropy of pitch-class distribution using `-Σ(p * log₂(p))`
- **Interpretation:** Higher entropy = more chromatic variety, less predictable; Lower = repetitive pitch patterns
- **Musical relevance:** Captures harmonic/melodic novelty and surprise (Mailman's concept)

---

## Main Functions

### 1. `analyze_temporal_vessels(score_path, window_size=4.0)`
**Purpose:** Core analysis engine that processes a musical score.

**Parameters:**
- `score_path`: Path to music file (.mid, .xml, .krn, etc.)
- `window_size`: Temporal window in quarter notes (beats) for segmentation

**Process:**
1. Parses the score using music21
2. Creates sliding windows across the piece
3. For each window, calculates all four vessels
4. Returns a DataFrame with temporal profiles

**Output:** DataFrame with columns:
- `start_beat`: Window start position
- `flux_rate`: Note attack density
- `avg_gestalt`: Mean gesture duration
- `tension_index`: Harmonic energy level
- `entropy`: Pitch predictability

---

### 2. `normalize_vessels(df)`
**Purpose:** Scales vessel metrics to [0, 1] range for cross-piece comparison.

**Process:**
- Applies Min-Max normalization to all metrics
- Adds `relative_time` column (0.0 to 1.0) to map formal structure independently of duration
- Enables meaningful comparison between works of different lengths/styles

**Output:** Same DataFrame with normalized columns

---

### 3. `get_corpus_profile(df_list)`
**Purpose:** Aggregates individual piece analyses into a historical period profile.

**Process:**
1. Concatenates DataFrames from multiple pieces
2. Groups by `time_decile` (10 relative time segments)
3. Averages each vessel metric for each decile

**Output:** DataFrame showing average temporal signature of a period

---

### 4. `batch_process_corpus(corpus_root)`
**Purpose:** Processes entire music corpus organized by historical period.

**Structure Expected:**
```
corpus_root/
  ├── Renacimiento/
  │   ├── piece1.mid
  │   └── piece2.xml
  ├── Barroco/
  └── Siglo_XX/
```

**Process:**
1. Iterates through period folders
2. Analyzes each valid music file (.mid, .xml, .krn)
3. Normalizes individual results
4. Computes corpus profile per period

**Output:** Dictionary mapping period names to their average temporal profiles

---

### 5. `plot_historical_evolution(all_period_data, metric='entropy')`
**Purpose:** Visualizes how a single metric evolved across historical periods.

**Features:**
- Plots one metric per period as a line across relative time (0.0-1.0)
- Allows comparison of temporal archetypes across centuries
- Shows whether, e.g., Baroque pieces had different entropy profiles than 20th-century works

**Example:** "How did harmonic predictability (entropy) change from Renaissance to Modern?"

---

### 6. `plot_decile_comparison(all_period_data, metric='entropy')`
**Purpose:** Advanced visualization comparing temporal shapes across periods.

**Features:**
- Displays all periods' metric evolution in one plot
- Uses smoothing for cleaner period signatures
- Labels progress as percentage (0-100%)
- Creates a "Western musical archetype" showing how temporal dimensions evolved

---

### 7. `get_polyphonic_density(elements, window_size)`
**Purpose:** Measures vertical (simultaneous voices) and horizontal (rhythmic independence) density.

**Metrics:**
- `avg_vertical_density`: Average voices sounding simultaneously
- `polyphonic_activity`: Attack rate per voice (independence measure)

**Musical relevance:** Distinguishes monophonic from polyphonic contexts and their temporal behavior

---

## Workflow Example

```python
# 1. Process entire corpus
corpus_data = batch_process_corpus('/path/to/music/corpus')

# 2. Visualize entropy evolution
plot_historical_evolution(corpus_data, metric='entropy')

# 3. Compare flux-rate patterns
plot_decile_comparison(corpus_data, metric='flux_rate')
```

---

## Key Libraries

| Library | Role |
|---------|------|
| **music21** | Parses and analyzes music files (MIDI, MusicXML, Kern) |
| **pandas** | Data manipulation and DataFrame operations |
| **numpy** | Numerical calculations (entropy, statistical measures) |
| **scikit-learn** | MinMaxScaler for normalization |
| **matplotlib** | Basic plotting |
| **seaborn** | Advanced visualization styling |

---

## Theoretical Background

### **Mailman's Information Theory**
Applies Shannon entropy to pitch distribution, measuring how "surprising" or "novel" harmonic content is across time.

### **Tosar's Tension Vectors**
Quantifies harmonic friction through interval weighting, where perfect intervals (1, 8) are more "consonant" and tritones/minor seconds are more "tense."

### **Dynamic Theory Integration**
Combines these perspectives into a framework where Western music's temporal evolution can be measured quantitatively across:
- Individual pieces
- Historical periods
- Entire corpora

---

## Output Data Structure

Each analysis produces a DataFrame like:

| start_beat | flux_rate | avg_gestalt | tension_index | entropy | relative_time |
|------------|-----------|-------------|---------------|---------|---------------|
| 0.0        | 2.5       | 1.2         | 18.5          | 2.8     | 0.0           |
| 4.0        | 1.8       | 1.8         | 12.3          | 2.1     | 0.05          |
| 8.0        | 3.2       | 0.9         | 24.1          | 3.2     | 0.10          |

---

## Use Cases

1. **Historical Period Analysis:** Identify temporal signatures of Renaissance vs. Baroque vs. Modern music
2. **Compositional Style Detection:** Classify pieces by temporal profile
3. **Corpus Linguistics:** Apply music analysis to large historical datasets
4. **Composition Generation:** Use profiles as constraints for algorithmic composition
5. **Musical Evolution Study:** Track how temporal dimensions changed over 500 years

---

## Notes

- **Normalization is crucial:** Raw metrics vary wildly by piece length/density; normalization enables fair comparison
- **Window size matters:** Smaller windows catch micro-rhythmic details; larger windows reveal macro-structure
- **Multi-format support:** Works with MIDI, MusicXML, Kern notation, and other music21-compatible formats
- **Error handling:** Batch processing skips malformed files, making large corpus analysis robust
