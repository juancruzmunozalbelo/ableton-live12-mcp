# HOLO Master Class — Módulo 1: Concepto y Referencia

**Clase:** Módulo 1 — Concepto y Referencia (`HOLO MASTER CLASS`)  
**Instructor:** Tomas Otero (Holo Audio / RESONANT)  
**Entorno DAW:** Ableton Live 12.4.6 Suite  
**Archivo de Especificación Asociado:** `holo_m1_concepto_referencia.json`  
**Video Fuente:** `/Users/juancruz/Downloads/HOLO MASTER CLASS/Modulo 1 [CONCEPTO Y REFERENCIA].mp4` (5,604s / 93.4 min)  

---

## 1. Visión Musical y Concepto Artístico

El objetivo primordial del Módulo 1 es asentar las bases estructurales, tonales y de monitoreo de un track profesional de **Melodic Techno**, partiendo de un lienzo en blanco hasta lograr un entorno de producción calibrado y ergonómico.

### Parámetros Globales del Proyecto
- **Tempo:** `126.00 BPM` (Tempo estándar para Melodic Techno de clubes y festivales modernos).
- **Compás:** `4/4`.
- **Tonalidad / Escala:** `C Menor (Do Menor Natural / Eólico)`.
  - Intervalos: `[0, 2, 3, 5, 7, 8, 10]` (C - D - Eb - F - G - Ab - Bb).
  - Enfoque emotivo: Atmósfera oscura, melancólica y de alta tensión cinética.
- **Extensión Temporal de la Maqueta:** `180 compases` (~5 minutos 43 segundos a 126 BPM), con 8 compases adicionales para colas de reverberación y fade out natural del máster.

---

## 2. Análisis y Warping de Tracks de Referencia

La referencia comercial es el estándar contra el cual se contrastan el balance tonal, la pegada de transientes, la apertura estéreo y la progresión de energía durante toda la masterclass.

### Referencias Utilizadas
1. **Referencia Primaria:** `04. Sezer Uysal, Axelax - Calling For More [HBT024].wav`
   - Formato: WAV 48.0 kHz, 24-bit PCM estéreo.
   - BPM Original: 124.0 BPM → Warpeado a 126.0 BPM en modo **Complex Pro** (Preserve Formants: 100%, Envelope: 128).
   - Función: Referencia de equilibrio espectral en bajos (sub rumble vs kick punch) y densidad de transientes en medios-altos.
2. **Referencia Secundaria:** `Eze Ramirez - Hyper Saw (Extended Mix).mp3`
   - Formato: MP3 44.1 kHz, 16-bit estéreo.
   - BPM Original: 125.0 BPM → Warpeado a 126.0 BPM en modo **Complex Pro**.
   - Función: Referencia para el ancho estéreo de sintes líderes (supersaw / wavetable leads) y transiciones de pre-drop.

### Arquitectura de Ruteo de Referencias (Bypass de Máster)
- Ambas pistas de audio se alojan dentro del grupo `CONCEPTO Y REFERENCIA`.
- **Salida de Audio del Grupo:** Configurada estrictamente a `Ext Out` o `Cue Out` (salida de pre-escucha/auriculares).
- **Razón Técnica:** Evita que el audio ya masterizado de las referencias comerciales atraviese los compresores, saturadores o limitadores del bus máster del proyecto, garantizando una comparación A/B real, sin distorsión ni coloración agregada.

---

## 3. Red de Retornos de Efectos (6 Return Tracks)

El proyecto define una red modular de 6 buses de retorno compartidos para otorgar coherencia espacial, densidad y profundidad tridimensional al mix:

1. **Return A — `CLA-76` (Compresión Paralela de Baterías):**
   - Dispositivo: `Live.Compressor` modelando circuito FET estilo 1176.
   - Parámetros: Attack ultra rápido (`0.02 ms`), Release rápido (`50 ms`), Ratio `4:1`, Makeup `+4.5 dB`.
   - Propósito: Aporta agresividad, snap y sustain a los transientes de percusiones y cajas sin aplastar la dinámica directa.
2. **Return B — `room` (Ambiente Corto de Sala):**
   - Dispositivo: `Live.Reverb` (Studio Room).
   - Parámetros: Decay `650 ms`, Pre-Delay `12 ms`, High Cut `4500 Hz`, Low Cut `220 Hz`, Diffusion `75%`.
   - Propósito: Emplazar kick, claps y shakers en el mismo espacio acústico tangible.
3. **Return C — `PLate` (Reverberación Plate Densa):**
   - Dispositivo: `Live.Hybrid` en modo algoritmo Plate.
   - Parámetros: Decay `1800 ms`, Pre-Delay `20 ms`, Damping `5000 Hz`.
   - Propósito: Brillo metálico sedoso para sintes stabs, percusiones secundarias y claps.
4. **Return D — `long rvbv` (Hall Atmosférico Extendido):**
   - Dispositivo: `Live.Reverb`.
   - Parámetros: Decay `5200 ms`, Pre-Delay `35 ms`, Room Size `90`, Low Cut `180 Hz`.
   - Propósito: Swells épicos, lanzamientos de delay al final de frases y colas en el breakdown.
5. **Return E — `SHIMMER` (Reverb con Pitch Octavado):**
   - Dispositivo: `Live.Hybrid` algoritmo Shimmer.
   - Parámetros: Pitch Shift `+12 semitonos` en el loop de realimentación, Decay `4500 ms`, Feedback `40%`.
   - Propósito: Colas celestiales y armónicos superiores para líneas melódicas y acordes en C Menor.
6. **Return F — `Portal` (Delay Granular y Stutter):**
   - Dispositivo: `Live.Echo` con modulación granular activada.
   - Parámetros: Left Delay `3/16` (dotted 8th), Right Delay `1/8`, Feedback `38%`.
   - Propósito: Rebotes rítmicos espaciales y texturas flotantes.

---

## 4. Cuadrícula de Marcadores de Arreglo (11 Locators)

La estructura completa del track se planifica desde el compás 1 hasta el compás 177 mediante 11 localizadores estratégicos que definen la curva de energía:

| Marcador | Compás | Tiempo (Beats) | Duración | Descripción Funcional y Contenido Musical |
| :--- | :---: | :---: | :---: | :--- |
| `INTRO` | 1.1.1 | 0.0 | 16 bars | Entrada limpia para DJ mixing. Bombo, sub rumble filtrado, shaker y drone atmosférico tenue. |
| `ARMADO` | 17.1.1 | 64.0 | 16 bars | Entrada de claps en tiempos 2 y 4, hi-hats en semicorcheas y primera insinuación filtrada del lead. |
| `PUENTE` | 33.1.1 | 128.0 | 16 bars | Retiro de capas de percusión, apertura progresiva del filtro paso bajo del lead y redoble de caja. |
| `DROP 1` | 49.1.1 | 192.0 | 16 bars | Primer pico de energía. Bombo, rumble, batería completa y sinte líder abierto sin filtro. |
| `PUENTE 2` | 65.1.1 | 256.0 | 16 bars | Variación melódica secundaria, patrones de bajo en tresillo y modulación en charles. |
| `DROP 2` | 81.1.1 | 320.0 | 16 bars | Sección de alta tracción rítmica. Leads principales y secundarios interactuando en llamada y respuesta. |
| `PUENTE 3` | 97.1.1 | 384.0 | 16 bars | Desarme paulatino hacia el breakdown. El filtro paso alto barre hacia arriba retirando frecuencias graves. |
| `BREAK` | 113.1.1 | 448.0 | 16 bars | El bombo y el bajo cortan al 100%. Exposición emotiva de la progresión de acordes y pads en C Menor. |
| `PREDROP` | 129.1.1 | 512.0 | 16 bars | Riser de pitch, redoble de caja acelerando, barrido de ruido blanco y atenuación de -1.5 dB en compás 144. |
| `MAIN DROP` | 145.1.1 | 576.0 | 16 bars | CLÍMAX ABSOLUTO (`DROP :)`). Todos los elementos musicales sonando en unísono con impacto de crash. |
| `OUTRO` | 161.1.1 | 640.0 | 16 bars | Desvanecimiento de acordes y melodías; reducción a bombo y bajo para mezcla de salida del DJ. |

---

## 5. Criterios de Calibración de Niveles y Ganancia (Gain Staging)

1. **Nivel Nominal de Pistas Individuales:**
   - Instrumentos y canales de audio se ajustan para promediar entre `-18 dBFS` y `-12 dBFS` RMS, evitando saturación prematura en los puntos de suma internos.
2. **Headroom en el Bus Máster:**
   - La suma combinada pre-limitador no debe superar `-6.0 dBFS` pico durante los drops más intensos.
3. **Monitoreo A/B Imparcial:**
   - El volumen de escucha de las referencias comerciales se atenúa entre `-6 dB` y `-8 dB` mediante el control de ganancia de clip o `Utility` para igualar el nivel de sonoridad percibido (LUFS) del track en producción antes de juzgar dinámicas y balances.
