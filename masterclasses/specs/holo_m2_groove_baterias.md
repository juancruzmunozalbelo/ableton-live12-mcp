# HOLO Master Class — Módulo 2: Groove y Baterías

**Clase:** Módulo 2 — Groove y Baterías (`HOLO MASTER CLASS`)  
**Instructor:** Tomas Otero (Holo Audio / RESONANT)  
**Entorno DAW:** Ableton Live 12.4.6 Suite  
**Archivo de Especificación Asociado:** `holo_m2_groove_baterias.json`  
**Video Fuente:** `/Users/juancruz/Downloads/HOLO MASTER CLASS/Modulo 2 [GROOVE Y BATERIAS].mp4` (6,403s / 106.7 min)  

---

## 1. Fundamentos del Kick y Arquitectura de Graves (Sub Rumble)

En el Melodic Techno, la interacción entre el bombo y el sub rumble es el núcleo rítmico y armónico que define el peso y la energía de la pista. Un grave descontrolado ensucia el mix, mientras que un grave plano carece de pegada física.

### A. Diseño del Bombo de Doble Capa
El bombo principal se construye combinando dos fuentes complementarias:
1. **Capa 1: Kick Punchy Transiente (`10 AT VNTM - Kick F.wav`):**
   - Tonalidad fundamental: `F` (~46.2 Hz).
   - Función: Aporta el click inicial (transiente en 3.2 kHz) y la pegada en frecuencias medias-bajas (70–120 Hz).
   - Procesamiento con `Drum Buss`:
     - Drive: `18%` (saturación suave para enriquecer armónicos).
     - Boom: `+2.2 dB` sintonizado a 46 Hz (refuerzo de la nota fundamental).
     - Transients: `+1.5 dB` (énfasis del ataque de la maza).
     - Crunch: `0%` (mantenido limpio para evitar asperezas).
   - Ecualización con `EQ Eight`:
     - Filtro paso alto a `28 Hz` (pendiente empinada de 48 dB/oct) para erradicar frecuencias subsónicas inaudibles que consumen headroom.
     - Corte quirúrgico tipo campana de `-2.5 dB` en `320 Hz` (factor Q: 2.1) para eliminar el carácter "acartonado".
     - Realce suave de `+1.8 dB` en `3,200 Hz` para garantizar presencia en sistemas de altavoces pequeños y auriculares.
2. **Capa 2: Sub Body de Respaldo (`mau5_kick_17_F#m.wav`):**
   - Transpuesta a `F` para coincidir armónicamente.
   - Función: Aportar masa y sustain redondeado en el rango 40–80 Hz.
   - Procesamiento con `Auto Filter`: Paso bajo estricto a `90 Hz` (24 dB/oct), aislando exclusivamente el peso subgrave.

---

## 2. Cadena de Procesamiento del Sub Rumble en Semicorcheas

El sub rumble sustituye al bajo convencional en los drops y crea el característico empuje hipnótico del Melodic Techno mediante una cadena de retardo, difusión y modulación dinámica:

```
[Kick Punch] 
    │
    ▼ (Envío de audio / Tap paralelo)
[Delay (1/16 triplet / 1/16 feedback 35%)]
    │
    ▼
[Reverb (100% Wet, Decay 850 ms, Pre-delay 0 ms, Diffusion 100%)]
    │
    ▼
[Auto Filter (Paso bajo 24 dB/oct MS2 Ladder a 100 Hz, Drive +3.5 dB)]
    │
    ▼
[Saturator (Curva Soft Sine, Drive +3.0 dB, 100% Wet)]
    │
    ▼
[Utility (Bass Mono activado por debajo de 120 Hz, Ancho 0% / Mono)]
    │
    ▼
[Compressor Sidechain (Fuente: Kick Punch, Ataque 0.1 ms, Release 80 ms, Ducking -12 dB)]
    │
    ▼
[Sub Rumble Bus (Salida limpia y bombeante en fase con el bombo)]
```

### Parámetros Clave del Rumble
- **Frecuencia de Corte:** Paso bajo riguroso a `100 Hz – 115 Hz` con el emulador analógico `MS2` (circuito Korg MS-20 de Ableton 12).
- **Control de Fase y Mono:** Todo el contenido de frecuencias por debajo de 120 Hz debe procesarse en mono estricto (`Utility` -> Bass Mono) para prevenir cancelaciones de fase acústicas en sistemas de sonido de clubes.
- **Sidechain Ducking:** El compresor comprime radicalmente la señal del rumble cada vez que el bombo golpea (tiempo de ataque ultra-rápido de `0.1 ms`), dejando el primer cuarto de tiempo completamente libre para el transiente del bombo y elevando el rumble rítmicamente en las semicorcheas posteriores.

---

## 3. Percusiones, Claps y Elementos Secundarios

### A. Clap-Snare Principal
- Muestra: `Odd Frequency - Pulse - Clap-Snare 1.wav`.
- Posicionamiento: Compases 2 y 4 de cada compás.
- Características sonoras: Transiente inicial afilado con cuerpo estéreo amplio.
- Ruteo a Retornos: Envío al retorno `CLA-76` a `-12 dB` para compresión paralela agresiva, y al retorno `room` a `-14 dB` para cohesión de sala.

### B. Shakers y Loops de Charles (Hi-Hats)
- **Shaker en Semicorcheas:** `Odd Frequency - Pulse - Shaker Loop 1 - 124 BPM` warpeado a 126 BPM.
  - Filtro paso alto a `450 Hz` para despejar el espacio del clap y del bajo.
  - Nivel en el mix: `-13 dBFS` para generar un murmullo constante y orgánico.
- **Hi-Hats a Contratiempo (Offbeat 8th) y Cerrados (16th):**
  - Muestra: `Odd Frequency - Pulse - Hat Loop 18 - 124 BPM` warpeado a 126 BPM.
  - El charles abierto en la corchea a contratiempo define la propulsión hacia adelante, mientras que los charles cerrados en semicorcheas intermedias proporcionan articulación.

### C. Percusiones Auxiliares en Drum Rack
- Pista `Drum Rack Aux Perc`:
  - `Rimshot Wood` (C1, nota MIDI 36): Paneado ligeramente a la izquierda (-25).
  - `Perc Bongo Tight` (D1, nota MIDI 38): Paneado a la derecha (+30).
  - `Closed Hat Ghost` (F#1, nota MIDI 42): Notas fantasma con velocidades variables (entre 60 y 85).
  - `Open Hat Sizzle` (A#1, nota MIDI 46): Toques esporádicos al final de frases de 8 compases.

### D. Bucle Percusivo Superior (`PERCUSSIVE`)
- Muestra: `ZEN_ALL_125_drum_loop_top_timeless.wav`.
- Procesamiento: Filtrado paso banda entre `800 Hz` y `9,000 Hz` para aportar brillo y roce percusivo en la parte alta del espectro sin competir con los medios del lead.

---

## 4. Aplicación de Swing y Groove Pool en Ableton Live 12

Para evitar la rigidez mecánica de la cuantización al 100% en la rejilla de semicorcheas:
1. **Plantilla de Groove:** `Swing 16ths` cargada en la `Groove Pool` de Live 12.
2. **Ajuste de Intensidad:**
   - Para Shakers y Charles cerrados: `Swing 16-59` con una cantidad global de groove del `65%`.
   - Para Percusiones secundarias: `Swing 16-62`.
   - El bombo se mantiene estrictamente cuantizado al 100% (ancla rítmica inamovible).

---

## 5. Bus de Baterías (`DRUMS Group`) y Mezcla

Todas las pistas de baterías se agrupan en `DRUMS`:
- **Compresión de Grupo:** `Glue Compressor` (Ataque `30 ms` para dejar pasar el ataque inicial de los tambores, Release `0.2 s`, Ratio `2:1`, reducción de ganancia entre `1.5 dB` y `2.5 dB`).
- **Ecualización de Grupo:** `EQ Eight` con corte suave en `30 Hz` y realce tipo shelf de `+1.2 dB` en `10 kHz` para otorgar aire profesional.
