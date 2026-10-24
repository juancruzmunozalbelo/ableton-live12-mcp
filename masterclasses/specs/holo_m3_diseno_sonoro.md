# HOLO Master Class — Módulo 3: Diseño Sonoro

**Clase:** Módulo 3 — Diseño Sonoro (`HOLO MASTER CLASS`)  
**Instructor:** Tomas Otero (Holo Audio / RESONANT)  
**Entorno DAW:** Ableton Live 12.4.6 Suite  
**Archivo de Especificación Asociado:** `holo_m3_diseno_sonoro.json`  
**Video Fuente:** `/Users/juancruz/Downloads/HOLO MASTER CLASS/Modulo 3 [DISEÑO SONORO].mp4` (6,335s / 105.6 min)  

---

## 1. Síntesis Insignia con Dispositivos Nativos de Ableton Live 12 Suite

El Módulo 3 explora las capacidades de síntesis avanzada de Ableton Live 12 Suite, empleando `Wavetable`, `Meld`, `Drift`, `Operator` y el procesador de distorsión multi-etapa `Roar` para forjar una identidad sonora vanguardista de Melodic Techno.

---

## 2. Recetas Detalladas de Diseño Sonoro

### A. Lead Principal en Wavetable (`Wavetable Lead`)
El sonido líder es una reinterpretación moderna del clásico supersaw, enriquecido con modulación wavetable y filtrado agresivo estilo escalera analógica:
- **Oscilador 1:**
  - Categoría: `Retro / Complex`.
  - Sprite Wavetable: `Cobalt`.
  - Posición de Tabla de Ondas: `1.0` (extremo armónico rico).
  - Modo de Efecto de Onda: `FM Modern` a una intensidad de `0.734`.
- **Oscilador 2:**
  - Forma de Onda: Diente de sierra (`Saw`).
  - Desafinación Fina: `+7 cents` para generar movimiento coral estéreo.
- **Sub-Oscilador:**
  - Activado a `-1 octava`, nivel `0.0 dB` para solidificar los medios-graves del sonido.
- **Sección de Filtros:**
  - **Filtro 1:** Circuito `MS2` (clon del legendario filtro paso bajo en escalera del Korg MS-20).
    - Frecuencia de corte base: `650 Hz`.
    - Resonancia: `0.156` (moderada para evitar silbidos estridentes).
    - Drive analógico: `8.81 dB` (empuja el filtro a una saturación cálida muy característica).
    - Modulación por Envolvente: Decaimiento de `800 ms` con sostenido a `-6 dB`.
  - **Filtro 2:** Filtro paso banda / formante vocal para otorgar resonancias de vocalización orgánica.
- **Modo Unísono:**
  - Algoritmo: `Shimmer` unísono (4 voces con dispersión del 25%).
- **Portamento / Glide:**
  - Modo: `Portamento` con tiempo de deslizamiento suave de `30.0 ms`.

### B. Saturación Multi-Etapa con `Roar`
`Roar`, el dispositivo insignia de saturación de Live 12, se inserta inmediatamente después de Wavetable:
- **Arquitectura de Ruteo:** Modo `Parallel / Multi-band` (divide la señal en bandas independientes).
- **Etapa 1 (Banda Media):** Modo `Warm Tube` con ganancia de `+6.5 dB` y bias asimétrico de `0.20`, aportando cuerpo analógico a las notas fundamentales.
- **Etapa 2 (Banda Alta):** Modo `High-cut Crunch` con ganancia de `+4.0 dB`, modulada sutilmente por el seguidor de envolvente (`Envelope Follower` al 25%) y realimentación armónica (`Feedback` al 15%).
- **Mezcla Global (Dry/Wet):** `65% Wet`.

### C. Bajo y Texturas Híbridas con `Meld` (`Meld Bass & Texture`)
Meld aprovecha su arquitectura de doble motor bio-acústico y experimental:
- **Motor A (Engine A):** `Virtual Analog Sub` (Onda Pulse/Saw a `-1 octava`), enfocado en la contundencia de medios-bajos.
- **Motor B (Engine B):** Motor `Rain / Noisy Texture` con resonancia alta (`0.65`) que reacciona a la velocidad MIDI, generando un crujido táctil y orgánico.
- **Modulación Cruzada:** Conexión de modulación cruzada al `35%` y saturación de filtro a `4.5 dB`.

### D. Lead Analógico Flotante con `Drift` (`Drift Analog Lead`)
- Emulación analógica pura mediante osciladores sustractivos.
- Oscilador 1: Sierra (`Saw`), Oscilador 2: Cuadrada (`Square`) afinada con `+9 cents`.
- Parámetro `Drift Amount`: Ajustado a `0.45` para inducir micro-fluctuaciones de afinación inestables e impredecibles, típicas de los sintetizadores de voltaje vintage de los años 70.
- Modo estéreo: `Wide Chorus` para abrir la imagen espacial.

### E. Stabs de Ataque Digital con `Operator` (`Operator FM`)
- Algoritmo 1 de síntesis FM (cadena vertical `D -> C -> B -> A`).
- Oscilador A (Portadora): Senoidal limpia.
- Oscilador B (Moduladora 1): Senoidal a frecuencia 1:1, nivel `-12 dB`.
- Oscilador C (Moduladora 2): Senoidal a razón 2:1, nivel `-24 dB`.
- Oscilador D (Moduladora 3): Ruido blanco con caída ultra-rápida (`15 ms`), inyectando un chasquido metálico punzante en el arranque de cada nota.
- Filtro: Paso bajo a `450 Hz` para que el ataque digital no enmascare las frecuencias altas del lead.

---

## 3. Filtrado Dinámico y Limpieza Espectral: `SC Filter Ducking`

Para evitar que los sintetizadores interfieran con el bombo y el sub rumble:
1. **Dispositivo `SC Filter`:** Se implementa un `Auto Filter` en modo paso alto (`HighPass 24 dB/oct`) configurado en `200 Hz`.
2. **Entrada Sidechain:** Vinculada al canal `Kick Punch`.
3. **Comportamiento Acústico:** Cada vez que el bombo impacta, el filtro corta instantáneamente todo el contenido por debajo de 200 Hz en los sintetizadores, devolviendo la respuesta de frecuencia completa una vez que la cola del bombo desciende. Esto elimina completamente la acumulación de energía desfasada en la zona crítica de 100–250 Hz.

---

## 4. Mapeo de Controles Macro para Interpretación y Automatización

El instrumento principal se encapsula en un `Instrument Rack` con 8 controles Macro esenciales:

| Macro # | Nombre del Macro | Parámetro de Destino | Rango de Mapeo | Función Musical |
| :---: | :--- | :--- | :---: | :--- |
| **Macro 1** | `Lead Cutoff` | Wavetable Lead Filter 1 Cutoff | `20 Hz – 20,000 Hz` | Barrido principal de apertura/cierre en builds y drops. |
| **Macro 2** | `Lead Resonance` | Wavetable Lead Filter 1 Res | `0.00 – 0.85` | Afilamiento del pico del filtro para énfasis psicodélico. |
| **Macro 3** | `Envelope Decay` | Wavetable Env 2 Decay | `50 ms – 3,000 ms` | Transición de stabs cortos y secos a notas sostenidas. |
| **Macro 4** | `Roar Saturation` | Roar Multi-Stage Drive | `0.0 dB – 18.0 dB` | Aumento de distorsión y agresividad en subidas de tensión. |
| **Macro 5** | `Delay Throw` | Lead Ping-Pong Delay Send | `0% – 100%` | Creación de ecos rítmicos espaciales al final de frases. |
| **Macro 6** | `Reverb Wash` | Long Reverb Send (Return D) | `0% – 100%` | Inmersión en nube ambiental durante el breakdown. |
| **Macro 7** | `Shimmer Octave` | SHIMMER Reverb Send (Return E) | `0% – 100%` | Proyección de cola brillante de octava superior. |
| **Macro 8** | `Stereo Spread` | Wavetable Unison Spread | `0% – 200%` | Ensanchamiento del campo estéreo de mono a súper ancho. |

---

## 5. Ruteo Espacial y Procesamiento de Bus

- El grupo de sintes (`SYNTHS Group`) alimenta el bus máster a `-3.0 dBFS`.
- Un `Glue Compressor` en el bus de sintes con ratio `4:1` y ataque suave de `10 ms` unifica la tímbrica de Wavetable, Meld y Drift antes de ingresar a la mezcla final.
