# Space 92 — "Gravity": lo VERIFICADO vs. lo que yo había asumido

> Corrección de Honesty Check. La "fórmula" que usamos para construir
> `space92_gravity.als` **la reconstruí yo** a partir de conocimiento del género
> (psy-tech / peak time) + el blueprint del repo. **No** era un análisis verificado
> del track *Gravity*. Después de investigar (ver fuentes al final), hay correcciones
> importantes: **el tempo, la tonalidad y la duración estaban mal**, y faltaban
> 5 técnicas que el propio Space 92 usa.

---

## 1. Datos duros del track (verificados en 2 fuentes independientes)

| Dato | Valor | Fuente |
|---|---|---|
| Artista / título | Space 92 — *Gravity* | MusicBrainz |
| Sello / catálogo | **Filth on Acid**, FOA126 | MusicBrainz + Reddit |
| Fecha | **17/02/2023** | MusicBrainz |
| **BPM** | **132** (no 138) | SongBPM + metadatos del release |
| **Tonalidad** | **Gm — Sol menor** (no frigio) | Metadatos del release (Reddit/Beatport) |
| Radio edit | 4:00 | SongBPM + release |
| **Extended mix** | **6:06** (≈ 806 beats @132 = 201 compases) | Metadatos + MusicBrainz (365,6 s) |
| Taxonomy | techno / **peak time techno** | MusicBrainz tags |

**Consecuencias directas sobre lo que construimos:**

1. El tempo del set es **138 BPM, debería ser 132 BPM**. 132 es el tempo real del track
   (y es más lento = más "pesado", más peak-time).
2. La escala del set es **G Frigio, debería ser G menor**. En G menor **no existe el Ab**
   (b2) — o sea: mi "tensión del b2" es un recurso **genérico del género**, no de *Gravity*.
   En G menor la nota de tensión sería un **Ab prestado** (b2) usado puntualmente.
3. La duración del set es **5:05, el extended real es 6:06** (el radio edit son 4:00) →
   faltan ~100 compases de estructura.
4. El propio Space 92 describe su sonido en 3 palabras: **"ass-kicking, melodic, trancey"**
   → el "melodic" es central y mi hook frigio es más oscuro que lo que él hace.

---

## 2. Las 6 lecciones reales del breakdown de "Gravity" (Production Music Live, ep. 004)

François PML desglosó el estilo de *Gravity* y Miriam las 6 lecciones clave.
Son técnicas que **mi build NO tiene**:

| # | Lección (PML) | Qué implementé yo | Qué falta / corregir |
|---|---|---|---|
| 1 | **Un "Rumble Rack"** para *dar color y forma* al rumble y encajarlo en la pista | rumble = sample estático con high-pass fijo | ❌ falta: un **Rack de device (Drum Rack)** con macros para dar forma al rumble |
| 2 | **Velocidades MIDI randomizadas** en elementos de percusión (ej. snare rolls) | todos los hits a velocidad fija | ❌ falta: **randomizar velocity** por nota (en el hook, el clap y el roll) |
| 3 | **EQ dinámica** para hacer espacio entre elementos que compiten (main / bass stab) | EQ estático en cada pista | ❌ falta: **EQ dinámica** (Live 12 la tiene) para el cruce kick/sub vs. stab |
| 4 | **Groove loops y "atmo"** para llenar el espectro | rumble + vocal pad | ⚠️ parcial: falta una capa de **atmo** propia |
| 5 | **Mezcla creativa con envelope followers de Ableton** | sidechain estático (implícito) | ❌ falta: **envelope follower** para "sidechain" en tiempo real de un bus |
| 6 | **Cadenas de efectos sidechained y en paralelo** (p.ej. reverb *tail* en paralelo como relleno de frecuencia, ~32:30 del video) | sends estáticos a reverb/delay | ⚠️ parcial: falta el **procesamiento en paralelo** (ya hay send, pero no la cadena paralela con ducking) |

> Nota: la #2 (velocity randomizada) es de las que más se notan en un tema de club:
> es lo que hace que la percusión suene "tocada por una persona" y no por una máquina.

---

## 3. Dónde se analiza Space 92 (foros, blogs y fuentes)

###.Foros y comunidades (Reddit)
| Hilo | Qué hay |
|---|---|
| [r/TechnoProduction — How to produce like Umek or Space 92?](https://www.reddit.com/r/TechnoProduction/comments/tpqs58/how_to_produce_like_umek_or_space_92/) | El hilo más directo. Consejo central: *importá un track de él a tu DAW y reproducí lo que escuchás hasta acercarte*; comparar, guardar, seguir con otro, volver meses después. |
| [r/proresivesound — Space 92 - Gravity [Filth on Acid]](https://www.reddit.com/r/proresivesound/comments/115haua/space_92_gravity_filth_on_acid/) | Metadatos exactos del release (key/BPM/duración de cada versión). |
| [r/Techno — Space 92 - Dimension (2026)](https://www.reddit.com/r/Techno/comments/1slzgex/space_92_dimension_2026/) · [Orbit Motion (2025)](https://www.reddit.com/r/Techno/comments/1kicre3/space_92_orbit_motion_2025/) · [Polaris (2024)](https://www.reddit.com/r/Techno/comments/1drmjuw/space_92_polaris_foa168_2024/) · [Atlas (2021)](https://www.reddit.com/r/Techno/comments/ochekc/space_92_atlas_2021/) | Discusión de cada tema (qué funciona, qué no). |
| [r/psytrance — hilo de Space 92](https://www.reddit.com/r/psytrance/comments/15jk3hx/the_craziest_beat_i_have_heard_n_wow_is_the_word/) | Contexto de la raíz psytrance del sonido (rolling bass, gallops). |
| r/deeptech_house — "Space 92 – Melodia (Extended Mix) [ARC056BP]" | Metadatos de otros releases del sello. |

### breakdowns y entrevistas
| Fuente | Qué aporta |
|---|---|
| **Production Music Live — "Producer Notes: In the Style of Space 92 *Gravity*" (ep. 004, con François PML)** ⭐ | **El breakdown real de Gravity.** Las 6 lecciones de la tabla de arriba. Menciona el "clean parallel tail-reverb frequency filler" (~32:30). |
| [Gray Area — "An Interview with Space 92, Techno's French Kingpin"](https://grayarea.co/magazine/an-interview-with-space-92-techno-s-french-kingpin) | Entrevista: se define como *"ass-kicking, melodic, trancey"*; influencia del pop sci-fi de los 80; Clerkenwell (Londres) → Toulouse. |
| [Beatportal — "Introducing Space 92's new Cosmic Champion"](https://www.beatportal.com/articles/12120-introducing-space-92-technos-new-cosmic-champion) | Perfil de label/vision artística. |
| [UFO Network — Space 92 label announcement](https://ufo-network.com/2025/02/24/space-92-record-label-announcement/) | Foco actual del artista (su propio sello). |
| [Innovations Sounds — "Mandala (Space 92 style)"](https://innovationsounds.com/products/mandala-space-92-style-techno-ghost-production) | Sample pack comercial **específicamente** derivado de su sonido (útil como referencia sonic). |
| [SongBPM — Gravity](https://songbpm.com/@space-92/gravity-WPNl5h4QQd) / [Tunebat](https://tunebat.com/Info/Gravity-Space-92/2EHdG8AvxtuZGLk74YQUXt) | BPM y tonalidad por track. |
| [MusicBrainz — Space 92](https://musicbrainz.org/artist/e2bef0c5-02e7-4505-b87f-90fc96bd70c3) | Fechas, sellos, duración real de las grabaciones. |

### Música de referencia para comparar (si querés hacer "match by ear")
`Space 92 – Gravity (Extended Mix)` · `Space 92 – Cooper` (Abm, 132 BPM, 5:57) ·
`Space 92 – Reaktor` (Ebm, 133 BPM) · `Space 92 – Orbit Motion` · `Space 92 – Dimension`

---

## 4. Plan de corrección (propuesta)

1. **Tempo 138 → 132 BPM** en el builder (`reset_clean_session` + locators re-calculados).
2. **Escala G Frigio → G menor** (root 7 = G, scale "Minor"), y el hook pasa a
   G–Bb–Eb–D con **Ab como nota de tensión puntual** (b2 prestado), no como escala base.
3. **Extender a 6:06** (≈201 compases): agregar "Outro largo" y/o un segundo drop.
4. **Rumble Rack** en Ableton (Drum Rack con 2-3Samples de rumble + macros de color).
5. **Randomizar velocity** del hook, el clap y el snare roll (±8-12).
6. **EQ dinámica** (Live 12) en el cruce kick/sub ↔ hook.
7. **Reverb/delay en paralelo** con ducking por envelope follower.
8. Re-verificar con `measure_track_levels.py` y re-exportar el mapa HTML.

---

## 5. Honestidad sobre el método

- ✅ Lo que **sí** está verificado con fuentes: BPM, key, duración, sello, fecha, y las 6
  técnicas del breakdown de PML.
- ⚠️ Lo que **sigue siendo inferencia mía**: el *arrangement* de 176 compases, la
  estructura de secciones y el diseño del hook. Nadie publica el mapa exacto de
  compases de un track; eso se "reconstruye" escuchando y comparando.
- 📌 Regla para adelante: **todo número que afirme en el HTML explicativo debe salir de
  una fuente o de una medición del set**, nunca de mi memoria del género.
