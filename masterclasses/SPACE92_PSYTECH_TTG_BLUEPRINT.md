# Blueprint de Ingeniería y Teoría Musical: El Sistema Space 92 × Trip to Galaxy × Psy-Tech

> [!IMPORTANT]
> **El Secreto de una "Firma Sónica" (Sonic Fingerprint):**
> No te convertís en el próximo Space 92 o Joris Voorn cambiando de sintetizadores todos los días. Te convertís en referente cuando **congelás el 80% de tu ingeniería (tu Chasis Fijo)** y solo variás el **20% compositivo (el Gancho, las Notas y el Vocal)** de un tema a otro. Cuando el oído humano reconoce la misma relación física entre tu Kick, tu Sub Rolling y el timbre de tu Lead en los primeros 3 segundos, tu nombre queda grabado.

---

## 1. La Ecuación de los 3 Mundos (Tu Identidad Propia)

Si copiás 100% a Space 92, sos un clon de Space 92. Pero si cruzás **la arquitectura de tensión y leads épicos de Space 92** + **el motor hipnótico/polirrítmico de Joris Voorn (*Trip to Galaxy*)** + **la precisión quirúrgica del bajo y los squelches del Psy-Tech**, tenés un sonido propio que hoy rompe cualquier pista a `136–138 BPM`.

```mermaid
flowchart TD
    subgraph S92["1. SPACE 92 (Euforia Oscura y Pegada de Estadio)"]
        A1["Escala Frigia (Semitono Oscuro: Tónica -> b2)"]
        A2["Hoover / Supersaw Lead con Glide y Reverb Sidechained"]
        A3["Silencio Pre-Drop (1 negra en cero absoluto antes del impacto)"]
    end

    subgraph TTG["2. JORIS VOORN - TRIP TO GALAXY (Hipnosis y Edits)"]
        B1["Polirritmias Cortas (Loops de 3, 5 o 7 semicorcheas contra 4/4)"]
        B2["Chasis de Remix (Cortar <250 Hz al tema original y montar bajo nuevo)"]
        B3["Evolución de Filtro y Tensión Continua de 6 Minutos"]
    end

    subgraph PSY["3. PSY-TECH (Ingeniería Quirúrgica de Graves y FM)"]
        C1["Bajo Rolling K-B-B-B con Fase Clavada (Start Phase = 0)"]
        C2["Separación Multibanda (<100 Hz Mono Puro vs >150 Hz Saturado)"]
        C3["Micro-FX / Squelches FM en los huecos del compás (Call & Response)"]
    end

    S92 --> CORE["TU FIRMA SÓNICA (136-138 BPM)"]
    TTG --> CORE
    PSY --> CORE
```

---

## 2. Física del Low-End: Por qué el Bajo de Space 92 y el Psy-Tech "Galopa"

En el techno berlinés tradicional el grave es una nube difusa de reverb (*rumble*). En **Space 92** y en el **Psy-Tech**, el grave es **una línea de sintetizador MIDI milimétrica** que conversa con el Kick en cada negra (`1/4`).

### A. La Grilla de 4 Semicorcheas por Tiempo (`1/16` Grid)
Un compás de `4/4` tiene 4 negras (tiempos), y cada negra se divide en **4 semicorcheas (`1/16`)**: `1 - e - & - a`.

* **Posición `1` (Tiempo fuerte):** Golpea el **Kick** solo. El bajo está silenciado al `100%` por la curva de sidechain (*VolumeShaper*).
* **Posición `e` (2da semicorchea):** Entra la primera nota del bajo (al `50–70%` de volumen porque la cola del kick todavía está bajando).
* **Posición `&` (Offbeat / Contratiempo):** Golpea la nota principal del bajo al `100%` de energía. Es la que te hace cabecear.
* **Posición `a` (4ta semicorchea):** Empuja hacia el próximo Kick, generando el efecto "locomotora" o *rolling*.

```mermaid
xychart-beta
    title "Energía en Un Tiempo (1 Negra = 4 Semicorcheas: 1, e, &, a)"
    x-axis ["1 (Golpe Kick)", "e (Sub entra 60%)", "& (Offbeat 100%)", "a (Empuje 90%)"]
    y-axis "Nivel de Presión Sonora (%)" 0 --> 100
    bar [100, 15, 0, 0]
    line [0, 60, 100, 90]
```

> [!TIP]
> **Lectura del gráfico arriba:**
> * Las **barras** son el **Kick**: clava el `100%` del transiente en el `1`, cae al `15%` en `e` y desaparece antes del `&`.
> * La **línea** es el **Rolling Bass (`K-B-B-B`)**: está en `0%` en el `1` (para no cancelar la fase del Kick), sube al `60%` en `e`, explota al `100%` en el `&` y empuja al `90%` en `a`. **Nunca chocan dos graves al mismo tiempo.**

### B. Los 3 Patrones de Bajo que definen el estilo
````carousel
### 1. El Rolling `K-B-B-B` (Psy-Tech & Space 92)
Tres notas de semicorchea (`1/16`) por cada golpe de Kick.
```text
Compás (16 semicorcheas):
Tiempo:  | 1   e   &   a  | 2   e   &   a  | 3   e   &   a  | 4   e   &   a  |
KICK:    | X   .   .   .  | X   .   .   .  | X   .   .   .  | X   .   .   .  |
BASS:    | .   B   B   B  | .   B   B   B  | .   B   B   B  | .   B   B   B  |
Veloc.:  |     75  120 105|     75  120 105|     75  120 105|     75  120 105|
```
* **Clave:** La onda Sawtooth del sintetizador (`Wavetable` / `Operator` / `Serum`) tiene que tener **Phase Random = 0%** (o *Retrig* activado) para que las 3 notas suenen idénticas siempre.
<!-- slide -->
### 2. El Galope en Tresillos `1/8T` (Firma Space 92)
En lugar de dividir el tiempo en 4 semicorcheas, lo dividís en **3 tresillos de corchea**.
```text
Tiempo (Tresillos): | 1    t    l   | 2    t    l   | 3    t    l   | 4    t    l   |
KICK:               | X    .    .   | X    .    .   | X    .    .   | X    .    .   |
BASS (Triplet):     | .    B    B   | .    B    B   | .    B    B   | .    B    B   |
```
* **Efecto psicológico:** Da sensación de marcha épica e hipnótica. Space 92 suele usar `K-B-B-B` en el Drop 1 y pasar a **Tresillos** o **Sub Octavado** en el Drop 2.
<!-- slide -->
### 3. El Polirritmo `3/16` Rolling (Firma Joris Voorn TTG)
Un patrón de **3 semicorcheas** de notas graves (ej. `G1 → G1 → D1`) que se repite sobre la grilla de 4 semicorcheas.
```text
Grilla 1/16: | 1  e  &  a | 2  e  &  a | 3  e  &  a | 4  e  &  a |
KICK:        | X  .  .  . | X  .  .  . | X  .  .  . | X  .  .  . |
ACENTO BASS: | G  g  d  G | g  d  G  g | d  G  g  d | G  g  d  G |
               ^        ^      ^        ^      ^        ^
```
* Como `3` no divide a `16`, el acento del bajo cae en un lugar distinto de cada golpe de Kick y recién vuelve a coincidir cada 3 compases. Eso genera **hipnosis instantánea**.
````

### C. Cadena de Procesamiento Multibanda del Bajo (El Secreto del Brillo sin Barro)

```mermaid
flowchart LR
    MIDI["MIDI: Notas K-B-B-B en G0/G1"] --> SYNTH["Synth: Sawtooth (1 voz, Phase Retrig ON, Cutoff 450 Hz)"]
    SYNTH --> SPLIT{"Divisor de Frecuencias (EQ / Roar Multibanda)"}
    
    SPLIT -->|"Banda Sub (20 Hz - 110 Hz)"| SUB["100% MONO + Compresión Firme (Sin Distorsión)"]
    SPLIT -->|"Banda Media (110 Hz - 1.8 kHz)"| MID["Saturación / Overdrive (Roar / Saturn) + Ligero Chorus"]
    
    SUB --> SUM["Bus del Bajo"]
    MID --> SUM
    SUM --> SC["Sidechain Quirúrgico (Curva 1/4 al Kick)"]
    SC --> BUS["Low-End Bus (Glue Compressor 2 dB GR)"]
```

---

## 3. Teoría Armónica: La Escala del "Peligro Épico" (Modo Frigio y Frigio Dominante)

¿Por qué los temas de **Space 92**, **HOLO** o **Psy-Tech** suenan oscuros, tensos y espaciales sin usar acordes complejos de jazz? Porque casi nunca usan la escala mayor ni la menor alegre: usan **el intervalo de segunda menor (`b2`, a 1 solo semitono de la nota raíz)** del **Modo Frigio**.

```mermaid
flowchart LR
    R["1. Tónica (Raíz: G)"] <-->|"1 Semitono (Tensión Oscura Maxima)"| B2["b2. Segunda Menor (Ab)"]
    R <-->|"3 Semitonos (Tristeza / Épica)"| B3["b3. Tercera Menor (Bb)"]
    R <-->|"7 Semitonos (Potencia / Quinta)"| P5["5. Quinta Justa (D)"]
    P5 <-->|"1 Semitono (Caída Hipnótica)"| B6["b6. Sexta Menor (Eb)"]
```

> [!NOTE]
> **Las 4 únicas notas que necesitás para un himno estilo Space 92 en Sol Frigio (`G Phrygian`):**
> * **`G` (Tónica):** Tu centro de gravedad (donde vive el Kick y el Bajo el 85% del tema).
> * **`Ab` (`+1` semitono):** La nota de "peligro/ácido". Cuando el bajo o el lead tocan `G -> Ab -> G`, el cerebro siente tensión inmediata.
> * **`Bb` (`+3` semitonos) o `B` (`+4` semitonos en Frigio Dominante / Psy):** La nota que abre la euforia en el Breakdown.
> * **`D` (`+7` semitonos) y `Eb` (`+8` semitonos):** La quinta de potencia y su semitono superior (`Eb -> D`), que es el gancho clásico de los leads de Trance/Techno.

---

## 4. El Motor Hipnótico de Joris Voorn (*Trip to Galaxy*): Polirritmia `5 contra 4`

Mientras el Kick y el Bajo clavan una cuadrícula rígida de `4/4` (`16` semicorcheas), Joris Voorn pone arriba un sintetizador (`Meld`, `Drift` o `Wavetable`) cuyo clip MIDI dura **5 semicorcheas (`5/16`)** o **7 semicorcheas (`7/16`)**.

```mermaid
sequenceDiagram
    participant K as Kick & Bass (Ciclo fijo de 4/16)
    participant S as Synth Loop TTG (Ciclo impar de 5/16)
    Note over K,S: Compás 1 (Semicorcheas 1 a 16)
    K->>K: Golpe 1 (Paso 1)
    S->>S: Nota 1 del Loop (Paso 1 - Coinciden)
    K->>K: Golpe 2 (Paso 5)
    S->>S: Nota 1 del Loop empieza en Paso 6 (Desfasado +1/16)
    K->>K: Golpe 3 (Paso 9)
    S->>S: Nota 1 del Loop empieza en Paso 11 (Desfasado +2/16)
    K->>K: Golpe 4 (Paso 13)
    S->>S: Nota 1 del Loop empieza en Paso 16 (Desfasado +3/16)
    Note over K,S: El cerebro humano escucha la misma melodía, pero en cada golpe de Kick suena como una frase nueva.
```

---

## 5. Arquitectura "Call & Response" (Cómo dialogan el Ácido, los Squelches de Psy-Tech y el Lead)

El error más común al empezar es hacer que todos los sintetizadores toquen al mismo tiempo. En **Space 92** y en el **Psy-Tech**, los sonidos se **turnan dentro de un bloque de 2 o 4 compases** (*Pregunta y Respuesta*):

```mermaid
flowchart LR
    subgraph BAR1["Compás 1 (Pregunta Oscura)"]
        M1["Tiempos 1 y 2: Solo Kick + Rolling Bass"] --> M2["Tiempos 3 y 4: Stab Ácido 303 distorsionado (G -> Ab)"]
    end
    subgraph BAR2["Compás 2 (Respuesta Psicodélica)"]
        M3["Tiempos 1 y 2: Solo Kick + Rolling Bass"] --> M4["Tiempos 3 y 4: Squelch FM / Glitch de Psy-Tech con Delay"]
    end
    BAR1 --> BAR2
```

### Cómo lograr que el Lead de Space 92 suene "Gigante pero Limpio" (Ducking Reverb)
Si le ponés una Reverb de 5 segundos a un Lead rápido, se arma una bola de ruido inentendible. Space 92 usa un **Compresor con Sidechain puesto DESPUÉS de la Reverb, escuchando al propio Lead seco**:

```mermaid
flowchart LR
    LEAD["Synth Lead (Supersaw / Hoover con Glide 65ms)"] --> DRY["Canal Principal (Suena 100% seco y al frente)"]
    LEAD -->|"Envío al Return A"| REV["Reverb Gigante (Decay 4.5s, Pre-Delay 35ms, LowCut 250Hz)"]
    REV --> COMP["Compresor (Sidechain tomado del propio Synth Lead)"]
    LEAD -.->|"Cuando el Lead toca, aplasta la Reverb -12 dB"| COMP
    COMP -->|"Cuando el Lead calla, la Reverb sube y llena todo el estadio"| MIX["Master Bus"]
    DRY --> MIX
```

---

## 6. Anatomía del Mapa de Arreglo de 6 Minutos y del "TTG Remix"

Tanto un tema original tuyo como un **Remix estilo Trip to Galaxy / Space 92** siguen esta curva de energía en **176 compases (`~5:15 min` a `137 BPM`)**:

```mermaid
stateDiagram-v2
    [*] --> Intro_DJ: Compases 1-32 (0:00 - 0:56)
    Intro_DJ --> Groove_A: Compases 33-64 (0:56 - 1:52)
    Groove_A --> Breakdown_Epico: Compases 65-96 (1:52 - 2:48)
    Breakdown_Epico --> Pre_Drop_Silence: Compás 96 Tiempo 4 (Silencio Total)
    Pre_Drop_Silence --> Peak_Drop_1: Compases 97-128 (2:48 - 3:44)
    Peak_Drop_1 --> Drop_1_Ride909: Compases 113-128 (Entra Ride 909 + Clap)
    Drop_1_Ride909 --> Mini_Break_Psy: Compases 129-144 (3:44 - 4:12)
    Mini_Break_Psy --> Climax_Drop_2: Compases 145-160 (4:12 - 4:40)
    Climax_Drop_2 --> Outro_DJ: Compases 161-176 (4:40 - 5:08)
    Outro_DJ --> [*]

    note right of Intro_DJ
        Kick + Rolling Bass (filtrado a 300 Hz)
        + Hats + Squelches cortos cada 4 compases.
    end note

    note right of Breakdown_Epico
        Se va el Kick.
        Abre el filtro del Hoover Lead (Space 92)
        o entra el Stem Vocal/Hook del Remix (TTG).
        Snare Roll + Riser en compases 89-96.
    end note

    note right of Pre_Drop_Silence
        1 negra en silencio (o frase vocal seca)
        antes de que reviente el Impact + Kick.
    end note
```

### ¿Cómo funciona el "Chasis de Remix" sobre esta misma estructura?
Cuando querés hacer un remix de cualquier tema (un clásico de trance, un tema indie/pop, o un track de house para llevarlo a Psy-Tech / Peak Time):
1. **Separación en 3 Stems:** Aislás del tema original únicamente el **Vocal**, el **Hook/Sinte principal** y la **Atmósfera** (descartás por completo la batería y el bajo viejos).
2. **Warping a `137 BPM` y Transporte a Frigio:** Warpeás los stems en modo `Complex Pro` (`Formants = 100`) y los llevás a la tónica de tu chasis (`G` o `F`).
3. **Filtro Quirúrgico (`EQ Eight`):** Les cortás todo debajo de `220 Hz` (`48 dB/oct`) para que jamás ensucien tu Kick + Rolling Bass.
4. **Dosificación (Regla de Oro de Joris Voorn):** En los compases `1–64` solo tirás *micro-cortes* de 1 sílaba del vocal con `Echo` psicodélico. Recién en el **Breakdown (`65–96`)** dejás cantar el gancho original entero, y en el **Drop (`97–128`)** el gancho queda picado rítmicamente arriba de tu propio bajo rolling y tu Acid Stab.

---

## 7. ElMapa del Espectro: Dónde vive cada sonido para que suene Profesional

```mermaid
xychart-beta
    title "Ocupación de Frecuencias por Elemento (20 Hz a 16 kHz)"
    x-axis ["20-60Hz (Sub)", "60-120Hz (Punch)", "120-300Hz (Cuerpo)", "300Hz-1kHz (Nota/Acid)", "1k-5kHz (Mordida/Lead)", "5k-16kHz (Aire/Hats)"]
    y-axis "Protagonismo en Mezcla (%)" 0 --> 100
    bar [95, 90, 20, 40, 85, 80]
```

* **`20–60 Hz` (Sub Puro, 100% Mono):** Vive la nota fundamental de tu **Rolling Bass** (`G0`/`F0`, `43–49 Hz`) y la cola grave del Kick. Nadie más entra acá.
* **`60–120 Hz` (Pegada de Pecho, Mono):** Vive el golpe seco del **Kick** (`75–95 Hz`) y el primer armónico del bajo.
* **`120–300 Hz` (La Zona Peligrosa del Barro):** Acá se atenúa casi todo (`-3 a -6 dB`). Solo asoma el cuerpo del Snare y la base cálida del Hoover Lead durante el Breakdown (cuando no están ni el Kick ni el Bajo).
* **`300 Hz – 1.2 kHz` (Zona de los Stabs Ácidos y Squelches FM):** Acá conversan en *Call & Response* el **Acid 303** y los **Squelches de Psy-Tech**.
* **`1.2 kHz – 5 kHz` (Zona Reina del oído humano):** Acá brilla el **Hoover / Supersaw Lead** de Space 92, el **Vocal del Remix** y el chasquido del **Clap**.
* **`5 kHz – 16 kHz` (Brillo, Velocidad y Aire):** Acá corren el **Closed Hat**, el **Open Hat de contratempo (`&`)** y el **Ride 909** del segundo drop.

---

## 8. Tu "Kit de Identidad Propia" en Ableton Live 12 Suite (Los 5 Bloques Fijos)

Para construir tu firma reconocible desde el primer tema, armamos **5 pistas madres fijas** en tu plantilla de Ableton Live 12 Suite:

1. **`01-KICK & PSY-BASS CHASSIS`**: Pista de Kick corto + Pista de `Wavetable`/`Operator` con el patrón `K-B-B-B`, división multibanda en `Roar` (`Sub` limpio + `Mid` rugiente) y curva de ducking exacta.
2. **`02-ACID & PSY SQUELCH CALL-RESPONSE`**: Dos pistas hermanas (`Drift` en modo Acid con filtro resonante + `Operator` FM con `Spectral Resonator`) que dialogan en los tiempos `3` y `4` de cada compás.
3. **`03-TTG POLYRHYTHM ENGINE (5/16)`**: Pista de `Meld` con un clip de `5` semicorcheas en escala Frigia que rota hipnóticamente sobre el `4/4`.
4. **`04-SPACE92 HOOVER LEAD + DUCKED REVERB`**: Pista de `Wavetable` en modo *Unison Shimmer (8 voces)* + *Glide 65ms* + Return de Reverb gigante comprimida por el propio Lead.
5. **`05-REMIX STEM DECK (VOCAL & HOOK)`**: Pistas de audio pre-ruteadas con `EQ Eight` (`<220 Hz` cortado), `Auto Filter`, `Shifter` y envíos de transición para tirar cualquier acapella o stem y convertirlo en un *TTG / Space 92 Edit* en 10 minutos.
