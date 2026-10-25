"""
Renderizador de loops de percusión/atmosfera sample-accurate a un tempo dado.

Genera loops estériles de 16 beats (4 compases) en WAV estéreo 44.1 kHz usando
solo stdlib (array + wave) + ffmpeg para decodificar/filtrar los one-shots.

Usado por los builders de masterclasses: los loops de 138 BPM del set "Acid Flow" y
los de 132 BPM del set "Gravity (verified)" no pueden mezclarse (si no, los loops
derivan del tempo al reproducirlos).
"""

from __future__ import annotations

import os
import subprocess
from array import array
from typing import Dict
import wave

SAMPLES_DIR = "/Users/juancruz/Downloads/ClaSE PEAK jULIO 25 Project/Samples"
SAMPLE_RUMBLE = os.path.join(SAMPLES_DIR, "Processed", "Consolidate", "TWHS_HGE1_RUMBLE_LOOP_08_143BPM [2025-06-25 203947].wav")
SAMPLE_CLAP = os.path.join(SAMPLES_DIR, "Processed", "Consolidate", "TWHS_HGE1_CLAP_02 [2025-06-25 211236].wav")
SAMPLE_SNARE = os.path.join(SAMPLES_DIR, "Imported", "TA_MK4_SNARE_ROLL_MASSIVE_126.wav")
CORE_LIB = "/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Core Library/Samples"
CORE_OH_909 = os.path.join(CORE_LIB, "One Shots", "Drums", "Hihat", "Hihat Open 909.aif")
CORE_RIDE_909 = os.path.join(CORE_LIB, "One Shots", "Drums", "Ride", "Ride 909.aif")
VOC_PAD_C4 = os.path.join(CORE_LIB, "One Shots", "Vocal", "Vocal Pad Avalon C4.wav")

SR = 44100


def render_club_loops(bpm: float, out_dir: str, suffix: str = "") -> Dict[str, str]:
    """Renderiza los loops base a `bpm`. Devuelve {'rumble': path, ...}.

    Los nombres llevan `suffix` para poder mantener sets a distintos tempos en el
    mismo directorio (p.ej. "_132bpm").
    """
    os.makedirs(out_dir, exist_ok=True)
    beat_frames = int(round((60.0 / bpm) * SR))
    bar4_frames = beat_frames * 16
    bar4_sec = bar4_frames / float(SR)
    tempo_ratio = bpm / 138.0  # el snare original es de 126 BPM -> se estira al tempo pedido

    paths = {
        "rumble": os.path.join(out_dir, f"loop_rumble_16b{suffix}.wav"),
        "clap": os.path.join(out_dir, f"loop_clap_16b{suffix}.wav"),
        "open_hat": os.path.join(out_dir, f"loop_909_offbeat_oh{suffix}.wav"),
        "ride": os.path.join(out_dir, f"loop_909_acid_ride_sc{suffix}.wav"),
        "snare": os.path.join(out_dir, f"loop_snare_climax_16b{suffix}.wav"),
        "vocal_pad": os.path.join(out_dir, f"loop_g_phrygian_vocal_pad_16b{suffix}.wav"),
    }

    def load_stereo_pcm(src_path: str, filter_chain: str = "anull") -> array:
        tmp_wav = os.path.join(out_dir, "_tmp_decode.wav")
        subprocess.run([
            "ffmpeg", "-y", "-i", src_path, "-af", filter_chain,
            "-ar", str(SR), "-ac", "2", "-sample_fmt", "s16", tmp_wav,
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        with wave.open(tmp_wav, "rb") as wf:
            raw = wf.readframes(wf.getnframes())
        if os.path.exists(tmp_wav):
            os.remove(tmp_wav)
        pcm = array("h")
        pcm.frombytes(raw)
        return pcm

    def place_hit(canvas: list, hit: array, start_frame: int, max_frames: int,
                  gain: float, fade_exp: float = 1.0) -> None:
        hit_frames = min(len(hit) // 2, max_frames)
        for f in range(hit_frames):
            dst_f = start_frame + f
            if dst_f >= bar4_frames:
                break
            env = ((1.0 - (f / float(hit_frames))) ** fade_exp) if fade_exp > 0.0 else 1.0
            scale = gain * env
            idx, h_idx = dst_f * 2, f * 2
            canvas[idx] += int(hit[h_idx] * scale)
            canvas[idx + 1] += int(hit[h_idx + 1] * scale)

    def save_stereo_pcm(dest_path: str, canvas: list) -> None:
        out = array("h", (max(-32000, min(32000, v)) for v in canvas))
        with wave.open(dest_path, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(SR)
            wf.writeframes(out.tobytes())

    # 1. Rumble: un hit por beat, con high-pass 125 Hz (no toca la banda del sub).
    one_rumble = load_stereo_pcm(SAMPLE_RUMBLE, "highpass=f=125,lowpass=f=360")
    canvas = [0] * (bar4_frames * 2)
    for b in range(16):
        place_hit(canvas, one_rumble, b * beat_frames, beat_frames, gain=0.45, fade_exp=0.35)
    save_stereo_pcm(paths["rumble"], canvas)

    # 2. Clap: golpes suaves en los beats 1, 3, 5, ... de cada compás.
    one_clap = load_stereo_pcm(SAMPLE_CLAP, "highpass=f=240,lowpass=f=7500")
    canvas = [0] * (bar4_frames * 2)
    for b in range(1, 16, 2):
        place_hit(canvas, one_clap, b * beat_frames, int(beat_frames * 0.85), gain=0.32, fade_exp=0.4)
    save_stereo_pcm(paths["clap"], canvas)

    # 3. Open hat 909 en cada '&' (contratiempo).
    one_oh = load_stereo_pcm(CORE_OH_909, "highpass=f=480,lowpass=f=8500")
    canvas = [0] * (bar4_frames * 2)
    for b in range(16):
        place_hit(canvas, one_oh, int((b + 0.5) * beat_frames), int(beat_frames * 0.42), gain=0.18, fade_exp=1.6)
    save_stereo_pcm(paths["open_hat"], canvas)

    # 4. Acid ride: 16avos con ducking suave en el beat 1.
    one_ride = load_stereo_pcm(CORE_RIDE_909, "highpass=f=600,lowpass=f=8200")
    canvas = [0] * (bar4_frames * 2)
    for b in range(16):
        for sub_step, vel_scale in ((0.25, 0.45), (0.50, 1.0), (0.75, 0.72)):
            place_hit(canvas, one_ride, int((b + sub_step) * beat_frames),
                      int(beat_frames * 0.35), gain=0.16 * vel_scale, fade_exp=1.5)
    save_stereo_pcm(paths["ride"], canvas)

    # 5. Snare roll de 16 beats (estirado al tempo pedido).
    subprocess.run([
        "ffmpeg", "-y", "-i", SAMPLE_SNARE,
        "-af", f"atempo={tempo_ratio:.6f},areverse,atrim=start=0:end={bar4_sec:.6f},areverse,"
               f"highpass=f=220,lowpass=f=7000,afade=t=in:st=0:d=2.5,volume=0.45",
        "-ar", str(SR), "-ac", "2", paths["snare"],
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # 6. Pad vocal afinado a G3 (C4 - 5 semitonos) con tremolo al tempo pedido.
    rate_g3 = int(round(SR * (2 ** (-5.0 / 12.0))))
    subprocess.run([
        "ffmpeg", "-y", "-stream_loop", "4", "-i", VOC_PAD_C4,
        "-af", f"asetrate={rate_g3},aresample=44100,highpass=f=220,lowpass=f=2400,"
               f"tremolo=f={bpm / 30.0:.4f}:d=0.55,aecho=0.8:0.88:326|652:0.4|0.3,"
               f"atrim=start=0:end={bar4_sec:.6f},afade=t=in:st=0:d=0.6,"
               f"afade=t=out:st={bar4_sec - 0.6:.4f}:d=0.6,volume=0.55",
        "-ar", str(SR), "-ac", "2", paths["vocal_pad"],
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return paths


if __name__ == "__main__":
    import json
    import sys
    bpm = float(sys.argv[1]) if len(sys.argv) > 1 else 132.0
    suffix = sys.argv[2] if len(sys.argv) > 2 else f"_{int(bpm)}bpm"
    print(json.dumps(render_club_loops(bpm, "/Users/juancruz/ableton-live12-mcp/masterclasses/peak", suffix), indent=2))


# ==============================================================================
# RE-GRID: recorta un loop sample (142/143/135 BPM) y lo vuelve a Placing sobre
# la grilla del tempo objetivo, detectando los onsets del propio sample.
# ==============================================================================

def _decode_stereo(src_path: str, sr: int = SR):
    """Decodifica a PCM estéreo 16-bit con ffmpeg y devuelve (pcm, sr)."""
    import array as _array
    tmp = os.path.join(os.path.dirname(src_path) or ".", "_regrid_decode.wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", src_path, "-ac", "2", "-ar", str(sr), "-sample_fmt", "s16", tmp,
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with wave.open(tmp, "rb") as wf:
        raw = wf.readframes(wf.getnframes())
    os.remove(tmp)
    pcm = _array.array("h")
    pcm.frombytes(raw)
    return pcm, sr


def _detect_hits(pcm, sr: int, thresh: float = 0.22, min_gap: float = 0.15):
    """Devuelve [(frame_inicio, pico)] de los onsets del loop (en muestras/canales)."""
    step = int(sr * 0.002)
    env = []
    for i in range(0, len(pcm) - 1, step * 2):
        l = abs(pcm[i])
        r = abs(pcm[i + 1])
        env.append(max(l, r))
    peak = max(env) if env else 1
    hits, last = [], -10.0
    for i, v in enumerate(env):
        t = i * step / sr
        if v / peak > thresh and t - last > min_gap:
            hits.append((i * step, v / peak))
            last = t
    return hits


def render_regridded(src_path: str, dest_path: str, bpm: float, beats: int = 16,
                     filter_chain: str = "anull", gain: float = 1.0,
                     thresh: float = 0.22, min_gap: float = 0.15,
                     repeat_first: bool = False) -> dict:
    """Re-coloca los onsets de un loop sample sobre la grilla de `bpm`.

    Devuelve info del resultado (hits detectados, BPM inferido del sample).
    """
    pcm, sr = _decode_stereo(src_path)
    if filter_chain != "anull":
        tmp_in = dest_path + ".in.wav"
        with wave.open(tmp_in, "wb") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(sr)
            wf.writeframes(pcm.tobytes())
        subprocess.run([
            "ffmpeg", "-y", "-i", tmp_in, "-af", filter_chain, "-ac", "2", "-ar", str(sr),
            "-sample_fmt", "s16", dest_path + ".f.wav",
        ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.remove(tmp_in)
        pcm, sr = _decode_stereo(dest_path + ".f.wav")
        os.remove(dest_path + ".f.wav")

    hits = _detect_hits(pcm, sr, thresh, min_gap)
    if not hits:
        return {"status": "no_hits", "hits": 0}

    beat_frames = int(round((60.0 / bpm) * sr))
    total_frames = beat_frames * beats
    canvas = [0] * (total_frames * 2)

    # periodo mediano de los onsets -> BPM "nativo" del sample (para reportar)
    gaps = [(hits[i + 1][0] - hits[i][0]) / sr for i in range(len(hits) - 1)]
    gaps_sorted = sorted(gaps) if gaps else [60.0 / bpm]
    median_gap = gaps_sorted[len(gaps_sorted) // 2]
    src_bpm = 60.0 / median_gap if median_gap > 0 else 0.0

    def _place(chunk, dst_frame: float, scale: float) -> None:
        dst_i = int(round(dst_frame))
        for f in range(0, len(chunk) - 1, 2):
            d = dst_i + f // 2
            if d >= total_frames:
                break
            canvas[d * 2] += int(chunk[f] * scale)
            canvas[d * 2 + 1] += int(chunk[f + 1] * scale)

    if repeat_first:
        # El sample es un solo hit (no un loop): se repite en CADA beat.
        frame, amp = hits[0]
        chunk = pcm[frame:len(pcm)]
        for b in range(beats):
            _place(chunk, b * beat_frames, amp * gain)
    else:
        # 1) patrón original -> grilla de semicorcheas del tempo destino (snap)
        placed = []
        for idx, (frame, amp) in enumerate(hits):
            nxt = hits[idx + 1][0] if idx + 1 < len(hits) else len(pcm)
            chunk = pcm[frame:nxt]
            if not chunk:
                continue
            scaled_beat = (frame / sr) * (bpm / 60.0)
            dst_beat = round(scaled_beat * 4.0) / 4.0
            placed.append((dst_beat, chunk, amp))
        # 2) si el patrón original es más corto que el loop destino, se.tilea
        if placed:
            span = placed[-1][0] - placed[0][0]
            if span > 0:
                offset = span
                while placed[-1][0] < beats - 0.01:
                    for dst_beat, chunk, amp in list(placed):
                        if placed[-1][0] >= beats - 0.01:
                            break
                        placed.append((dst_beat + offset, chunk, amp))
        # 3) se coloca
        for dst_beat, chunk, amp in placed:
            if dst_beat >= beats - 0.001:
                continue
            _place(chunk, dst_beat * beat_frames, amp * gain)

    out = array("h", (max(-32000, min(32000, v)) for v in canvas))
    with wave.open(dest_path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(out.tobytes())

    return {
        "status": "ok",
        "hits": len(hits),
        "src_bpm": round(src_bpm, 2),
        "dst_bpm": bpm,
        "beats": beats,
        "path": dest_path,
    }


def render_hit_loop(src_path: str, dest_path: str, bpm: float, beats: int = 16,
                    offsets=(0.0,), filter_chain: str = "anull", gain: float = 1.0,
                    sr: int = SR, min_gap: float = 0.12) -> dict:
    """Coloca el PRIMER hit del sample en las posiciones `offsets` (en beats).

    Es la misma técnica que usa render_club_loops() (que ya sonó bien): se detecta
    el onset, se corta el segmento del hit y se lo coloca sample-accurate sobre la
    grilla del tempo destino. Así el loop queda phase-locked con el resto del set.
    """
    pcm, sr = _decode_stereo(src_path, sr)
    if filter_chain != "anull":
        tmp_in = dest_path + ".in.wav"
        with wave.open(tmp_in, "wb") as wf:
            wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr)
            wf.writeframes(pcm.tobytes())
        subprocess.run(["ffmpeg", "-y", "-i", tmp_in, "-af", filter_chain, "-ac", "2",
                        "-ar", str(sr), "-sample_fmt", "s16", dest_path + ".f.wav"],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        os.remove(tmp_in)
        pcm, sr = _decode_stereo(dest_path + ".f.wav", sr)
        os.remove(dest_path + ".f.wav")

    hits = _detect_hits(pcm, sr, 0.22, min_gap)
    if not hits:
        return {"status": "no_hits"}
    start = hits[0][0]
    end = hits[1][0] if len(hits) > 1 else len(pcm)
    chunk = pcm[start:end]
    amp = hits[0][1]

    beat_frames = int(round((60.0 / bpm) * sr))
    total_frames = beat_frames * beats
    canvas = [0] * (total_frames * 2)
    for off in offsets:
        dst = int(round(off * beat_frames))
        if dst < 0 or dst >= total_frames:
            continue
        scale = amp * gain
        for f in range(0, len(chunk) - 1, 2):
            d = dst + f // 2
            if d >= total_frames:
                break
            canvas[d * 2] += int(chunk[f] * scale)
            canvas[d * 2 + 1] += int(chunk[f + 1] * scale)

    out = array("h", (max(-32000, min(32000, v)) for v in canvas))
    with wave.open(dest_path, "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr)
        wf.writeframes(out.tobytes())
    return {"status": "ok", "hits_detected": len(hits), "chunk_sec": round(len(chunk) / sr / 2, 3),
            "positions": list(offsets), "path": dest_path}
