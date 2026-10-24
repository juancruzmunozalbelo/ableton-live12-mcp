# HOLO Master Class — Módulo 4: Bases Armónicas y Melódicas

**Clase:** Módulo 4 — Bases Armónicas y Melódicas (`HOLO MASTER CLASS`)  
**Instructor:** Tomas Otero (Holo Audio / RESONANT)  
**Entorno DAW:** Ableton Live 12.4.6 Suite  
**Archivo de Especificación Asociado:** `holo_m4_bases_armonicas_melodicas.json`  
**Video Fuente:** `/Users/juancruz/Downloads/HOLO MASTER CLASS/Modulo 4 [BASES ARMÓNICAS Y MELÓDICAS].mp4` (6,789s / 113.2 min)  

---

## 1. Marco Armónico y Teoría Musical

El Módulo 4 se enfoca en la composición armónica y melódica sobre la tonalidad de **Do Menor Natural (C Minor / Escala Eólica)**. La meta es crear una progresión melancólica, nostálgica y cinemática que mantenga un pulso constante de propulsión.

### Estructura de la Progresión Armónica Principal (Ciclo de 16 Compases)
La progresión consta de 4 acordes distribuidos en bloques de 4 compases cada uno:

```
Compases 1–4:   [ Cm(add9) ]  (i - Tónica Menor)
Compases 5–8:   [ Ab(add9) ]  (VI - Grado Submediante Mayor)
Compases 9–12:  [ Fm(add9) ]  (iv - Grado Subdominante Menor)
Compases 13–16: [ Gm7      ]  (v - Grado Dominante Menor)
```

### Disposición de Voces (Voicing)
Para obtener un sonido contemporáneo y amplio, se evitan las tríadas cerradas básicas en el registro medio, empleando inversiones abiertas y extensiones de 9na agregada:
1. **Acorde 1 — Cm(add9):**
   - Fundamental en bajo: `C1 (nota MIDI 36)` / `C2 (48)`.
   - Voces superiores: `C3 (48)`, `Eb3 (51)`, `G3 (55)`, `D4 (62)`.
   - La 9na (`D4`) introduce una tensión agridulce que trasciende el acorde menor estándar.
2. **Acorde 2 — Ab(add9):**
   - Fundamental en bajo: `Ab0 (nota MIDI 32)` / `Ab1 (44)`.
   - Voces superiores: `Ab2 (44)`, `C3 (48)`, `Eb3 (51)`, `Bb3 (58)`.
   - Abre el campo armónico con luminosidad dramática.
3. **Acorde 3 — Fm(add9):**
   - Fundamental en bajo: `F0 (nota MIDI 29)` / `F1 (41)`.
   - Voces superiores: `F2 (41)`, `Ab2 (44)`, `C3 (48)`, `G3 (55)`.
   - Proporciona una caída melancólica introspectiva.
4. **Acorde 4 — Gm7:**
   - Fundamental en bajo: `G0 (nota MIDI 31)` / `G1 (43)`.
   - Voces superiores: `G2 (43)`, `Bb2 (46)`, `D3 (50)`, `F3 (53)`.
   - Dominante menor modal que prepara el retorno cíclico hacia el Cm sin la resolución cliché del acorde mayor clásico.

---

## 2. Líneas de Bajo y Motivos Rítmicos en Tresillo

El bajo melódico no es estático; se divide en dos enfoques complementarios:

### A. Bajo Rodante en Semicorcheas (`Rolling 16th Bass`)
- Rueda continuamente en semicorcheas sobre las notas fundamentales de la progresión y sus quintas justas:
  - Sobre Cm: `C1` alternando con saltos rápidos hacia `G1`.
  - Sobre Ab: `Ab0` alternando con `Eb1`.
  - Sobre Fm: `F0` alternando con `C1`.
  - Sobre Gm: `G0` alternando con `D1`.
- Dinámica: Los tiempos fuertes tienen una velocidad MIDI de `110`, mientras que las semicorcheas intermedias (notas de enlace) se programan a velocidad `75`, generando un efecto de galope orgánico.

### B. Motivo de Bajo en Tresillo (`PC2 Triplet Bass Motif`)
- Patrón rítmico sincopado basado en una subdivisión `3-3-2` dentro del compás de 4/4.
- Se introduce en las secciones `PUENTE 2` y `DROP 2` para romper la monotonía de las semicorcheas continuas, aportando tensión polirrítmica inmediatamente antes de las transiciones estructurales.

---

## 3. Fraseo Melódico y Llamada-Respuesta

La melodía principal sigue los principios del diálogo melódico:
1. **Frase Líder (Llamada):** Interpretada por el sinte principal en el registro central (`C4, Eb4, G4, Bb4, Ab4, G4`). Se caracteriza por notas sostenidas con vibrato y apertura de filtro.
2. **Contramelodía en Arpegio (Respuesta):** Ejecutada por un sinte tipo pluck (`Analog Pluck / XFBassPluck`) en un registro más agudo (`G4, D5, Eb5, G5`), rellenando los espacios de silencio dejados por la frase líder mediante arpegios en cascada.

---

## 4. Edición Avanzada de Notas MIDI en Ableton Live 12

Ableton Live 12 introduce herramientas de edición de notas extendidas que elevan la programación MIDI por encima de cualquier DAW tradicional:

### A. Probabilidad de Nota (`Note Probability`)
- Para las notas fantasma del bajo (`Rolling 16th Bass`) y el tema melódico (`Main Melodic Theme`), el parámetro de probabilidad se programa como número flotante compatible con Live 12 LOM (`0.85` / 85% y `0.95` / 95% respectivamente, con rango general `0.80`–`0.90`).
- Esto garantiza que cada compás suene ligeramente diferente durante la reproducción, eliminando la sensación de "bucle robótico pregrabado".

### B. Desviación de Velocidad (`Velocity Deviation`)
- Se asigna un rango de desviación de `+/- 8` a `+/- 12` unidades de velocidad MIDI a los patrones de semicorcheas.
- El motor de Live 12 calcula valores aleatorios gaussianos en tiempo real dentro de ese rango para cada pulsación de nota.

### C. Ajuste a Escala (`Fit to Scale`) y Resaltado (`Highlight Scale`)
- En el editor MIDI de Live 12, se activa `C Minor` con `Highlight Scale` y `Fold to Scale` activados.
- Cualquier transformación melódica o generación de acordes se mantiene estrictamente restringida a las 7 notas de Do Menor.

---

## 5. Elementos de Transición, Redobles y Risers

En los compases de cambio de frase (compás 16, 32, 48, 80, 144):
- **Redobles Estructurales:** `TPS x CamelPhat - Fill 02 (124 BPM)` warpeado a 126 BPM, situado en el compás 48 (inmediatamente antes de Drop 1) y en el compás 144 (predrop).
- **Subidas de Tensión (Risers):** `TPS x CamelPhat - Riser 08 (124 BPM)` con automatización ascendente de volumen y barrido de pitch desde el compás 137 hasta el compás 145.
