# Peak Time Class: ClaSE PEAK jULIO 25 — Technical Specification & Reconstruction Guide

**Clase:** Peak Time Techno Masterclass  
**Instructor:** Peerk  
**Proyecto Fuente:** `/Users/juancruz/Downloads/ClaSE PEAK jULIO 25 Project/ClaSE PEAK jULIO 25.als`  
**Video Fuente:** `/Users/juancruz/Downloads/video peak.mp4` (9,732s / 162.2 min)  
**DAW / Motor:** Ableton Live 12.2.1 Suite (Build Revision `c0d59beb0465cc1bcc75830dbff2b10a48082a7d`)  
**Archivo de Especificación Asociado:** `clase_peak_julio_25.json`  

---

## 1. Arquitectura Global del Proyecto y Metadatos

- **Tempo Global:** `135.00 BPM` (Estándar para Hard Techno y Peak Time contemporáneo).
- **Compás:** `4/4`.
- **Tonalidad / Escala:** `G Menor (Sol Menor Natural)`. Todas las líneas de sintetizador, arpegios, stabs y cortes vocales están afinados en Sol Menor (G1, G2, G3, D4, Eb4, G4).
- **Línea de Tiempo del Arreglo:**
  - Extensión total: `176 compases` (`704.0 beats`).
  - Duración total de reproducción: `312.89 segundos` (`5 minutos 12.9 segundos`).
- **Pistas Totales:** `33 pistas` + Pista Máster (`MainTrack`).
- **Clips del Proyecto:** `370 clips MIDI` y `1,823 clips de audio`.

---

## 2. Jerarquía de Pistas y Arquitectura de Buses Anidados (3 Niveles)

El proyecto implementa una estructura de procesamiento de stems altamente disciplinada, organizando las 33 pistas en 3 niveles de grupos anidados para control de ganancia y pegamento sonoro:

```
Pista Máster (MainTrack) [T-RackS 6 Limiter + Voxengo SPAN]
  ├── Pista 00: [Grupo] 1-Group (Bus Máster de STEMs, Vol -4.7 dB)
  │     ├── Pista 01: [Grupo] 2-Group (Bus de Baterías y Melodías, Vol -0.7 dB)
  │     │     ├── Pista 02: [Grupo] 3-Group (Bus de Bombo y Sub, Vol -5.7 dB)
  │     │     │     ├── Pista 03: [Audio] 4-OL_SKPA1_Kick_Loop_01_123 (5) (Vol -3.0 dB)
  │     │     │     └── Pista 04: [Audio] 5-TWHS_HGE1_RUMBLE_LOOP_08_143BPM (Vol -9.4 dB)
  │     │     ├── Pista 05: [Audio] 6-OL_SKPA1_Kick_Loop_01_123 (5) (Kick Layer 2, Vol -9.1 dB)
  │     │     ├── Pista 06: [MIDI]  7-ADRKT_WTTB4_Synth_10 (Wavetable Lead 1, Vol -13.9 dB)
  │     │     ├── Pista 07: [MIDI]  8-Omnisphere (Atmosphere Pulse, Vol -2.0 dB)
  │     │     ├── Pista 08: [Audio] 9-TWHS_HGE1_CH_LOOP_03_142BPM (Closed Hat, Vol -9.6 dB)
  │     │     ├── Pista 09: [MIDI]  10-ADRKT_WTTB4_Synth_26 (Wavetable Hook, Vol 0.0 dB)
  │     │     ├── Pista 10: [MIDI]  11-ADRKT_WTTB4_Synth_15 (Wavetable Lead 2, Vol -11.3 dB)
  │     │     └── Pista 11: [Audio] Omnisphere (Bounced Atmosphere STEM, Vol -8.4 dB)
  │     ├── Pista 12: [MIDI]  13-ADRKT_WTTB4_Synth_18 (Wavetable Arp / Riser, Vol -4.6 dB)
  │     ├── Pista 13: [MIDI]  ADRKT_WTTB4_Bass_01 (Wavetable Sub/Mid Bass Stab, Vol -9.4 dB)
  │     ├── Pista 14: [Audio] 15-TWHS_HGE1_CLAP_02 (Main Clap, Vol -12.7 dB)
  │     ├── Pista 15: [Audio] 16-AU_MTF2_126_vocal_rap_doubles (Lead Vocals - Manipulator, Vol -8.3 dB)
  │     ├── Pista 16: [Audio] 17-AU_MTF2_126_vocal_rap_doubles (Filtered Vocal Spin 1, Vol -30.0 dB)
  │     ├── Pista 17: [Audio] 18-AU_MTF2_126_vocal_rap_doubles (Vocal Chop 2, Vol -12.2 dB)
  │     ├── Pista 18: [Audio] 19-AU_MTF2_126_vocal_rap_doubles (Filtered Vocal Spin 2, Vol -12.2 dB)
  │     ├── Pista 19: [Audio] 20-AU_MTF2_126_vocal_rap_doubles (Vocal Build Chop, Vol -30.0 dB)
  │     ├── Pista 20: [Audio] 21-AU_MTF2_126_vocal_rap_doubles (Cola del Volcado / Tail, Vol -31.5 dB)
  │     ├── Pista 21: [Audio] 22-TA_MK4_SNARE_ROLL_MASSIVE_126 (Snare Build Roll, Vol -16.8 dB)
  │     └── Pista 22: [MIDI]  23-Serum 2 (Synth Hook / Arp, Vol -14.0 dB)
  ├── Pista 23: [Audio] 24-ZEN_KBB_137_drum_groove_storm (Aux Percussion, Vol -20.4 dB)
  ├── Pista 24: [MIDI]  25-Omnisphere (Drone Pad 1, Vol -20.3 dB)
  ├── Pista 25: [Audio] Omnisphere (Drone Audio Layer, Vol -21.2 dB)
  ├── Pista 26: [MIDI]  27-Omnisphere (Drone Pad 2, Vol -21.2 dB)
  ├── Pista 27: [Audio] 28-031_FX_Impact_-_SEROTONINTRANCE (Impact FX, Vol -22.0 dB)
  ├── Pista 28: [Audio] 29-ESM_7th_Dimension_Build_Up_Rising (Transition Riser, Vol -13.8 dB)
  ├── Pista 29: [Audio] 30-Freeze ... Oscar Mulero - On a Metal Horse (Industrial Texture, Vol -28.3 dB)
  ├── Pista 30: [Return] A-Reverb (Vol 0.0 dB)
  ├── Pista 31: [Return] B-Delay (Vol 0.0 dB)
  └── Pista 32: [Return] C-Echo (Vol 0.0 dB)
```

### Ruteo de Señales
- **Sub-Grupo 34 (`3-Group` Kick + Rumble):** Se suma directamente hacia el Grupo 22 (`2-Group`).
- **Grupo 22 (`2-Group` Drums + Melodics):** Se suma hacia el Grupo 33 (`1-Group`).
- **Grupo 33 (`1-Group` All Master STEMs):** Alimenta directamente el canal Máster.
- **Pistas Auxiliares (23 a 29):** Alimentan directamente el canal Máster de forma independiente para procesamiento en paralelo sin la compresión del grupo principal.

---

## 3. Inventario Completo y Verificado de Muestras de Audio (Samples)

Todas las muestras han sido auditadas físicamente en `/Users/juancruz/Downloads/ClaSE PEAK jULIO 25 Project/Samples/`, abarcando 19 archivos `.wav` reales en disco organizados con sus prefijos exactos de subcarpeta:

### A. Muestras Importadas (`Samples/Imported/`)
1. `Imported/031_FX_Impact_-_SEROTONINTRANCE_Zenhiser.wav` (44.1kHz 24b PCM, 2 ch, 8.49s, 2.14 MB) → Pista 27 (28-031_FX_Impact).
2. `Imported/ESM_7th_Dimension_Build_Up_Rising_Riser_Cinematic_Trailer_Movie_Transition.wav` (44.1kHz 16b PCM, 2 ch, 5.59s, 1.03 MB) → Pista 28 (29-ESM_7th_Dimension).
3. `Imported/TA_MK4_SNARE_ROLL_MASSIVE_126.wav` (44.1kHz 24b PCM, 2 ch, 15.24s, 3.85 MB) → Pista 21 (22-TA_MK4_SNARE_ROLL).
4. `Imported/TWHS_HGE1_CH_LOOP_03_142BPM.wav` (44.1kHz 24b PCM, 2 ch, 6.76s, 1.79 MB) → Pista 08 (9-TWHS_HGE1_CH_LOOP_03).
5. `Imported/ZEN_KBB_137_drum_groove_storm.wav` (44.1kHz 24b PCM, 2 ch, 14.02s, 3.54 MB) → Pista 23 (24-ZEN_KBB_137_drum_groove_storm).

### B. Muestras Procesadas / Consolidadas (`Samples/Processed/Consolidate/`)
6. `Processed/Consolidate/OL_SKPA1_Kick_Loop_01_123 (5) [2025-06-25 203905].wav` (44.1kHz 24b PCM, 2 ch, 3.56s, 0.90 MB) → Pistas 03 & 05 (Main Kick).
7. `Processed/Consolidate/TWHS_HGE1_RUMBLE_LOOP_08_143BPM [2025-06-25 203947].wav` (44.1kHz 24b PCM, 2 ch, 0.44s, 0.11 MB) → Pista 04 (Sub Rumble).
8. `Processed/Consolidate/TWHS_HGE1_CLAP_02 [2025-06-25 211236].wav` (44.1kHz 24b PCM, 2 ch, 0.89s, 0.22 MB) → Pista 14 (Main Clap).
9. `Processed/Consolidate/AU_MTF2_126_vocal_rap_doubles_female_get_naughty_sex_pills_dry_Gmin [2025-06-25 211824].wav` (44.1kHz 24b PCM, 2 ch, 7.62s, 1.92 MB) → Pistas 15, 17, 18 (Lead Vocals).
10. `Processed/Consolidate/AU_MTF2_126_vocal_rap_doubles_female_get_naughty_sex_pills_dry_Gmin [2025-06-25 211605].wav` (44.1kHz 24b PCM, 2 ch, 15.48s, 3.91 MB) → Toma vocal alternativa 2.
11. `Processed/Consolidate/AU_MTF2_126_vocal_rap_doubles_female_get_naughty_sex_pills_dry_Gmin [2025-06-25 211534].wav` (44.1kHz 24b PCM, 2 ch, 15.48s, 3.91 MB) → Toma vocal alternativa 1.
12. `Processed/Consolidate/AU_MTF2_126_vocal_rap_doubles_female_get_naughty_sex_pills_dry_Gmin (Cola del volcado) [2025-06-25 213100].wav` (44.1kHz 24b PCM, 2 ch, 9.78s, 2.47 MB) → Pista 20 (Cola del Volcado).
13. `Processed/Consolidate/(Volcar) [2025-06-25 223141].wav` (44.1kHz 24b PCM, 2 ch, 14.22s, 3.59 MB) → Volcado de pista Omnisphere.

### C. Muestras Reversadas (`Samples/Processed/Reverse/`)
14. `Processed/Reverse/AU_MTF2_126_vocal_rap_doubles_female_get_naughty_sex_pills_dry_Gmin [2025-06-25 211824] R.wav` (44.1kHz 24b PCM, 2 ch, 7.62s, 1.92 MB) → Transición vocal reversada principal.
15. *Reasignación Item #15:* La toma temporal `[2025-06-25 215155] R.wav` (de la cual sólo existía `.asd` en disco) ha sido remapeada a la toma idéntica y físicamente existente `AU_MTF2_... [2025-06-25 211824] R.wav`.

### D. Volcados y Congelamientos (`Samples/Processed/Bounce/` y `Processed/Freeze/`)
16. `Processed/Bounce/Bounce 7-Omnisphere [2025-06-25 210111]-2.wav` (44.1kHz 32b IEEE_FLOAT, 2 ch, 14.33s, 4.82 MB) → Pista 11 (Omnisphere Bounced STEM).
17. *Reasignación Item #17:* El bounce intermedio `Bounce 25-Omnisphere [2025-06-25 222218]-2.wav` (sólo `.asd`) ha sido remapeado al stem final congelado de la Pista 25: `Processed/Freeze/Freeze 25-Omnisphere [2025-06-26 020502]-1.wav` (44.1kHz 32b IEEE_FLOAT, 2 ch, 14.57s, 4.90 MB).
18. `Processed/Freeze/Freeze 24-ZEN_KBB_137_drum_groove_storm [2025-06-26 020502]-1.wav` (44.1kHz 32b IEEE_FLOAT, 2 ch, 12.56s, 4.22 MB) → Pista 23 (Aux Drum Freeze Cache).
19. `Processed/Freeze/Freeze 25-Omnisphere [2025-06-26 020502]-1.wav` (44.1kHz 32b IEEE_FLOAT, 2 ch, 14.57s, 4.90 MB) → Pista 24 (Omnisphere Drone Freeze Cache).

### E. Grabaciones en Vivo Catalogadas (`Samples/Recorded/`)
20. `Recorded/13-AU_MTF2_126_vocal_rap_doubles_female_get_naughty_sex_pills_dry_Gmin 0001 [2025-06-25 212002].wav` (44.1kHz 24b PCM, 1 ch Mono, 1.41s, 0.18 MB) → Toma scratch en vivo grabada durante la clase a las 21:20:02.
21. `Recorded/15-Audio 0001 [2025-06-25 212820].wav` (44.1kHz 24b PCM, 2 ch Stereo, 4.66s, 1.17 MB) → Toma de remuestreo interno (resample) en Pista 15 grabada a las 21:28:20.

*Nota sobre Pista 29 (Oscar Mulero Metal Horse):* Los archivos de congelamiento de esta pista externa sólo existen en formato `.asd` (cache sin audio distribuido en el set original). Se documenta explícitamente para su reconstrucción/síntesis nativa en Suite durante Milestone 3.

---

## 4. Cadenas de Dispositivos y Recetas de Sonido

### A. Racks de Wavetable para Sonido Industrial (`InstrumentGroupDevice`)
Utilizados en las pistas 06, 09, 10, 12 y 13:
- **Motor Wavetable:** Oscilador 1 con sprite `Cobalt`, posición `1.0`, efecto `FM Modern` a `0.734`.
- **Filtro Analógico:** Circuito `MS2` Korg ladder con saturación extrema (`8.81 dB Drive`).
- **Cadena de Distorsión en Serie:**
  - `Amp`: Simulación de cabezal vintage.
  - `Overdrive`: Saturación crujiente en frecuencias medias.
  - `Pedal`: Distorsión agresiva.
  - `Saturator`: Pegamento analógico y limitación de transientes.
  - `Redux2`: Reducción de bits y downsampling para aspereza industrial (en Pista 12).
- **Tratamiento Espacial y Dinámico:**
  - `Delay` y `Hybrid Reverb` para dimensiones oscuras.
  - `DrumBuss` para realzar el cuerpo subgrave (`Boom`).
  - `EQ Eight` con corte estricto por debajo de 100 Hz en pistas líderes.

### B. Procesamiento Vocal y Efecto `Band-pass Spinner`
- **Pista 15 (Lead Vocal):** Plugin `Polyverse Manipulator (VST3)` modificando pitch y formantes para lograr la típica voz robótica y oscura de Techno.
- **Pistas 16, 18, 19 (`Band-pass Spinner`):**
  - Dispositivo `AutoFilter2`:
    - Tipo de Filtro: Paso banda (`Band-pass 24 dB/oct`).
    - Modelo de Circuito: `MS2` con `15.9% Drive`.
    - Frecuencia Central: `2490.39 Hz` (~2.5 kHz).
    - Resonancia: `0.738` (alta resonancia que enfatiza el timbre vocal).
    - LFO de Modulación: Senoidal a `0.64 Hz`, cantidad `14.5%`, parámetro `Spin: 0.5` (crea una rotación binaural continua entre el canal izquierdo y derecho).
    - Mezcla: `100% Wet`.
    - Envíos Auxiliares: Send A (`Reverb`) = `100%`, Send C (`Echo`) = `100%`. Esto genera las masivas nubes vocales que barren el breakdown.

### C. Live 12 Meld Synth (`Meld Housy Bass`)
- Pista `Meld` con el preset oficial de Live 12 `Housy Bass.adv`, aportando pegada y armónicos analógicos en el registro grave.

### D. Pista Máster
1. **T-RackS 6 Limiter (VST3):** Limitación analógica y saturación de bus.
2. **Voxengo SPAN (VST3):** Analizador espectral FFT de alta resolución para monitoreo de fase y balance tonal.

---

## 5. Distribución de Notas MIDI (Tonalidad G Menor)

| Pista | Nota MIDI / Tono | Función en el Arreglo | Total Notas Programadas |
| :--- | :---: | :--- | :---: |
| **Track 06 (`Synth 10`)** | `G1 (31)` | Groove rítmico bajo-medio sincopado | 544 |
| **Track 07 (`Omnisphere`)** | `G2 (43)` | Pulso atmosférico rítmico | 1,632 |
| **Track 09 (`Synth 26`)** | `G1 (31)` | Stab de acento en transiciones | 54 |
| **Track 10 (`Synth 15`)** | `G3 (55)` | Gancho melódico principal (semicorcheas) | 576 |
| **Track 12 (`Synth 18`)** | `G2 (43), G3 (55), G#3 (56)` | Riser de tensión (semitono ascendente G a G#) | 3,264 |
| **Track 13 (`Bass 01`)** | `G1 (31)` | Stab de bajo cada 16 beats (compases 3, 7, 11...) | 28 |
| **Track 22 (`Serum 2`)** | `G3 (55), D4 (62), Eb4 (63), G4 (67)` | Tríada de Sol Menor + 6ta menor | 1,032 |
| **Track 24 (`Drone 1`)** | `G3 (55)` | Drone sostenido durante el breakdown (compases 77-80) | 1 |
| **Track 26 (`Drone 2`)** | `G3 (55)` | Drone atmosférico extendido (compases 65-80) | 1 |

---

## 6. Evolución Cronológica a Través de los 5 Snapshots de Backup

Los 5 archivos en `Backup/` registran el proceso pedagógico real durante la clase de Peerk:

1. **Snapshot 1 (`2025-06-25 20:58:31`, 33 KB): El Groove Inicial**
   - 5 pistas: Kick Loop, Rumble Bass Loop, Synth 10 (Wavetable rack), Reverb, Delay. Se define el pulso y la relación kick/sub a 135 BPM.
2. **Snapshot 2 (`2025-06-25 22:18:31`, 158 KB): Expansión Melódica (1h 20m)**
   - 8 pistas: Incorporación de Omnisphere, Hi-Hat cerrado y Synth 15 lead. Estructuración inicial de bucles.
3. **Snapshot 3 (`2025-06-25 22:58:32`, 560 KB): Agrupamiento y Vocales (2h 00m)**
   - 29 pistas: Reestructuración en 3 grupos anidados (`1-Group`, `2-Group`, `3-Group`). Se agregan Clap, Snare Roll, Serum 2, efectos y el retorno Echo. Introducción de los cortes vocales y el efecto `Band-pass Spinner`.
4. **Snapshot 4 (`2025-06-25 23:00:02`, 838 KB): Clímax y Textura Industrial**
   - 33 pistas: Inserción del sample de Oscar Mulero (`Metal Horse`, 640 cortes de audio). Extensión del arreglo hasta los 176 compases completos.
5. **Snapshot 5 (`2025-06-26 02:24:22`, 837 KB): Pulido Post-Clase**
   - Volcado y congelamiento de pistas pesadas (`Freeze 24-ZEN_KBB_137`, `Freeze 25-Omnisphere`). Limpieza de ecualización en bajas frecuencias.
6. **Proyecto Final (`ClaSE PEAK jULIO 25.als`, 1,056 KB): Masterización y Entrega**
   - Carga de T-RackS 6 y Voxengo SPAN en el canal máster. Verificación final de niveles y exportación.
