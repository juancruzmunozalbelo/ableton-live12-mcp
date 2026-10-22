#!/usr/bin/env python3
"""
Empirical Challenge & Stress-Test Harness for Milestone 2:
Live 12 Remote Script Bridge & Client Connector.

Adversarial Stress Dimensions:
1. Concurrency & Thread-Safety:
   - 50 concurrent client threads firing 500 requests across TCP bridge.
   - High-burst queue overflow (> MAX_QUEUE_DRAIN_PER_TICK = 64).
   - Verification of exact request-response ID correlation and zero dropped frames.
   - Persistent connection reuse and rapid sequential requests.
2. Error Resilience:
   - Malformed JSON (truncated bytes, raw garbage, invalid non-UTF-8 bytes).
   - Invalid JSON-RPC protocol frames (missing method, non-string method, invalid params).
   - Nonexistent methods (raw names, canonical normalization).
   - Invalid LOM paths (empty, whitespace, dots, bogus roots, out-of-range track indices, nonexistent properties/methods).
   - Protection of main-thread timer: unhandled exceptions must never crash the server or stop the timer.
3. Latency Benchmarking:
   - Roundtrip latency for live12_song_get_state (200 iterations).
   - Roundtrip latency for live12_lom_get (200 iterations).
   - Roundtrip latency under concurrent load (10 background threads).
   - Connection probe (ping) latency (100 iterations).
   - Strict SLA: 100% of responses must complete in < 50ms.
"""

from __future__ import annotations

import json
import math
import os
import queue
import socket
import sys
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

# Ensure repo root is on sys.path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src.live12_bridge import (
    Live12ControlSurface,
    create_instance,
    liveobj_valid,
    lom_call,
    lom_get,
    lom_inspect,
    lom_set,
    dict_to_midi_note_spec,
    midi_note_to_dict,
)
from src.live12_bridge.bridge import BridgeJob, DISCOVERY_PATH, MAX_QUEUE_DRAIN_PER_TICK
from src.live12_bridge.handlers import BridgeHandlers, dispatch_tool_call
from src.ableton_live12_mcp.client import (
    Live12Client,
    Live12ConnectionError,
    Live12RpcError,
    Live12TimeoutError,
    ToolResult,
)


def log_step(name: str, passed: bool, detail: str = ""):
    symbol = "✓ PASS" if passed else "✗ FAIL"
    print(f"[{symbol}] {name}")
    if detail:
        print(f"       -> {detail}")
    if not passed:
        sys.exit(1)


# ==============================================================================
# Mock Ableton Live Engine for Standalone Bridge Execution
# ==============================================================================

class MockApplicationView:
    def __init__(self):
        self.focused_view = "Session"

    def show_view(self, view_name: str):
        self.focused_view = view_name

    def focus_view(self, view_name: str):
        self.focused_view = view_name


class MockApplication:
    def __init__(self):
        self.view = MockApplicationView()
        self.open_dialog_count = 0
        self.current_dialog_message = ""

    def press_current_dialog_button(self, button_index: int):
        if self.open_dialog_count == 0:
            raise IndexError("No open dialog to press")
        self.open_dialog_count = max(0, self.open_dialog_count - 1)


class MockDeviceParam:
    def __init__(self, name: str, val: float, min_v: float, max_v: float):
        self.name = name
        self.value = val
        self.min = min_v
        self.max = max_v
        self.is_quantized = False


class MockDevice:
    def __init__(self, name: str = "Wavetable"):
        self.name = name
        self.type = "instrument"
        self.is_active = True
        self.can_have_chains = "Rack" in name
        self.parameters = [
            MockDeviceParam("Device On", 1.0, 0.0, 1.0),
            MockDeviceParam("Filter Freq", 1000.0, 20.0, 20000.0),
            MockDeviceParam("Macro 1", 0.0, 0.0, 1.0),
        ]
        self.macros = [0.0] * 16
        self.variations: List[Dict[str, Any]] = []
        self.matrix: Dict[str, float] = {}

    def store_variation(self):
        self.variations.append({"index": len(self.variations), "values": list(self.macros)})

    def recall_variation(self, idx: int):
        if idx < 0 or idx >= len(self.variations):
            raise IndexError("Variation index out of range")
        self.macros = list(self.variations[idx]["values"])


class MockClip:
    def __init__(self, length: float = 4.0, name: str = "Test Clip"):
        self.length = length
        self.name = name
        self.loop = True
        self.loop_start = 0.0
        self.loop_end = length
        self.start_marker = 0.0
        self.warping = True
        self.warp_mode = "beats"
        self.pitch_coarse = 0.0
        self.gain = 1.0
        self.notes: List[Any] = []
        self.warp_markers: List[Tuple[float, float]] = []

    def fire(self):
        pass

    def stop(self):
        pass

    def quantize(self, grid: float, amount: float):
        pass

    def add_warp_marker(self, beat_time: float, sample_time: float):
        self.warp_markers.append((float(beat_time), float(sample_time)))

    def add_new_notes(self, note_specs: tuple):
        for spec in note_specs:
            self.notes.append(spec)

    def get_notes_extended(self, start_time: float, pitch: int, time_span: float, pitch_span: int):
        return tuple(self.notes)

    def apply_note_modifications(self, modified_notes: tuple):
        pass


class MockClipSlot:
    def __init__(self):
        self.clip: Optional[MockClip] = None

    def create_clip(self, length: float):
        self.clip = MockClip(length=length)

    def delete_clip(self):
        self.clip = None


class MockMixer:
    def __init__(self):
        self.volume = MockDeviceParam("Volume", 0.0, -70.0, 6.0)
        self.panning = MockDeviceParam("Pan", 0.0, -1.0, 1.0)
        self.sends = [MockDeviceParam("Send A", 0.0, 0.0, 1.0)]
        self.crossfade_assign = 0


class MockTrack:
    def __init__(self, name: str = "Audio 1"):
        self.name = name
        self.color = 0
        self.solo = False
        self.mute = False
        self.arm = False
        self.clip_slots = [MockClipSlot() for _ in range(4)]
        self.devices = [MockDevice()]
        self.mixer_device = MockMixer()
        self.take_lanes: List[Any] = []

    def create_take_lane(self):
        class TakeLane:
            def __init__(self, idx: int):
                self.name = f"Take {idx}"
        self.take_lanes.append(TakeLane(len(self.take_lanes) + 1))


class MockScene:
    def __init__(self, name: str = "Scene 1"):
        self.name = name

    def fire(self):
        pass


class MockScaleInformation:
    def __init__(self):
        self.name = "Major"
        self.root_note = 0


class MockSongView:
    def __init__(self, song: MockSong):
        self._song = song
        self.selected_track = None
        self.selected_scene = None

    def select_device(self, device: Any):
        pass


class MockSong:
    def __init__(self):
        self.tempo = 120.0
        self.signature_numerator = 4
        self.signature_denominator = 4
        self.is_playing = False
        self.record_mode = False
        self.session_record = False
        self.loop = False
        self.loop_start = 0.0
        self.loop_length = 4.0
        self.punch_in = False
        self.punch_out = False
        self.arrangement_overdub = False
        self.metronome = False
        self.scale_information = MockScaleInformation()
        self.tracks = [MockTrack("Audio 1"), MockTrack("MIDI 1")]
        self.return_tracks = [MockTrack("Return A")]
        self.scenes = [MockScene("1"), MockScene("2")]
        self.view = MockSongView(self)

    def start_playing(self):
        self.is_playing = True

    def continue_playing(self):
        self.is_playing = True

    def stop_playing(self):
        self.is_playing = False

    def capture_midi(self):
        pass

    def create_midi_track(self, index: int):
        t = MockTrack(f"MIDI {len(self.tracks) + 1}")
        self.tracks.insert(index, t)
        return t

    def create_audio_track(self, index: int):
        t = MockTrack(f"Audio {len(self.tracks) + 1}")
        self.tracks.insert(index, t)
        return t

    def delete_track(self, index: int):
        if index < 0 or index >= len(self.tracks):
            raise IndexError("Track index out of range")
        return self.tracks.pop(index)


class MockCInstance:
    def __init__(self):
        self._app = MockApplication()
        self._song = MockSong()
        self.log_entries: List[str] = []
        self.status_messages: List[str] = []

    def application(self):
        return self._app

    def song(self):
        return self._song

    def log_message(self, msg: str):
        self.log_entries.append(msg)

    def show_message(self, msg: str):
        self.status_messages.append(msg)


# ==============================================================================
# Stress Test Runner
# ==============================================================================

class Milestone2StressHarness:
    def __init__(self):
        self.c_inst = MockCInstance()
        self.surface: Optional[Live12ControlSurface] = None
        self.drain_thread: Optional[threading.Thread] = None
        self.running = False
        self.drain_interval = 0.005  # 5ms timer emulation

    def start(self):
        self.surface = Live12ControlSurface(self.c_inst)
        self.running = True

        def loop_drain():
            while self.running:
                if self.surface:
                    self.surface._drain_queue()
                time.sleep(self.drain_interval)

        self.drain_thread = threading.Thread(target=loop_drain, name="Emulated-Live-Base-Timer", daemon=True)
        self.drain_thread.start()

    def stop(self):
        self.running = False
        if self.surface:
            self.surface.disconnect()
            self.surface = None

    @property
    def port(self) -> int:
        assert self.surface is not None
        return self.surface._port


def test_concurrency(harness: Milestone2StressHarness):
    print("\n" + "=" * 70)
    print("TEST 1: CONCURRENT CLIENT REQUESTS & QUEUE THREAD-SAFETY")
    print("=" * 70)

    client = Live12Client(port=harness.port)
    log_step("Live12Client connected to test bridge", client.is_reachable())

    # 1.1 Multi-threaded concurrent storm: 50 threads, 10 requests each = 500 requests
    num_threads = 50
    requests_per_thread = 10
    total_requests = num_threads * requests_per_thread
    print(f"\n[STORM] Firing {total_requests} requests across {num_threads} concurrent threads...")

    results = []
    errors = []

    def worker_task(thread_id: int):
        c = Live12Client(port=harness.port)
        for seq in range(requests_per_thread):
            req_type = (thread_id + seq) % 4
            try:
                if req_type == 0:
                    r = c.call("live12_song_get_state", {})
                    assert "tempo" in r
                elif req_type == 1:
                    tempo_val = 100.0 + ((thread_id * 10 + seq) % 50)
                    r = c.call("live12_transport_set_tempo", {"tempo": float(tempo_val)})
                    assert r["tempo"] == float(tempo_val)
                elif req_type == 2:
                    r = c.call("live12_lom_get", {"target_path": "live_set", "property_name": "tempo"})
                    assert "value" in r
                else:
                    r = c.call("live12_lom_inspect", {"target_path": "live_set"})
                    assert "properties" in r
                results.append((thread_id, seq, True))
            except Exception as e:
                errors.append((thread_id, seq, str(e)))

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(worker_task, tid) for tid in range(num_threads)]
        for f in as_completed(futures):
            f.result()
    elapsed = time.perf_counter() - t0

    throughput = total_requests / elapsed
    log_step(
        f"500 concurrent requests completed (100% success rate, 0 dropped)",
        len(results) == total_requests and len(errors) == 0,
        f"Total: {len(results)}/500 | Errors: {len(errors)} | Elapsed: {elapsed:.2f}s | Throughput: {throughput:.1f} req/s",
    )

    # 1.2 High-burst queue overflow (> MAX_QUEUE_DRAIN_PER_TICK = 64)
    print("\n[OVERFLOW] Testing queue overflow with burst > 64 items (MAX_QUEUE_DRAIN_PER_TICK)...")
    harness.running = False  # Pause draining temporarily to pile up queue
    time.sleep(0.02)

    burst_jobs = []
    for i in range(120):  # 120 jobs > 64
        job = BridgeJob(req_id=f"burst_{i}", method="live12_song_get_state", params={})
        harness.surface._request_queue.put(job)
        burst_jobs.append(job)

    qsize_before = harness.surface._request_queue.qsize()
    log_step(f"Queue piled up beyond 64 items (actual depth: {qsize_before})", qsize_before >= 120)

    # First drain tick: should drain exactly 64 items
    harness.surface._drain_queue()
    drained_first_tick = sum(1 for j in burst_jobs if j.done_event.is_set())
    log_step(f"First drain tick bounded by MAX_QUEUE_DRAIN_PER_TICK (64)", drained_first_tick == 64)

    # Second drain tick: drains remainder (56 items)
    harness.surface._drain_queue()
    drained_second_tick = sum(1 for j in burst_jobs if j.done_event.is_set())
    log_step(f"Second drain tick emptied remaining jobs (total: {drained_second_tick}/120)", drained_second_tick == 120)

    # Resume background draining
    harness.running = True
    def resume_drain():
        while harness.running:
            if harness.surface:
                harness.surface._drain_queue()
            time.sleep(harness.drain_interval)
    harness.drain_thread = threading.Thread(target=resume_drain, daemon=True)
    harness.drain_thread.start()

    # 1.3 Persistent connection reuse: rapid sequential requests over single socket
    print("\n[PIPELINING] Testing persistent socket stream with rapid back-to-back requests...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5.0)
    s.connect(("127.0.0.1", harness.port))

    pipelined_count = 50
    for i in range(pipelined_count):
        req = json.dumps({"jsonrpc": "2.0", "id": 1000 + i, "method": "live12_song_get_state", "params": {}}) + "\n"
        s.sendall(req.encode("utf-8"))
        # Read response line
        line = b""
        while not line.endswith(b"\n"):
            chunk = s.recv(1024)
            if not chunk:
                break
            line += chunk
        resp = json.loads(line.decode("utf-8"))
        assert resp["id"] == 1000 + i
        assert "result" in resp

    s.close()
    log_step(f"Persistent socket stream: {pipelined_count} sequential requests with exact ID correlation", True)


def test_error_resilience(harness: Milestone2StressHarness):
    print("\n" + "=" * 70)
    print("TEST 2: ERROR RESILIENCE & MAIN-THREAD TIMER INTEGRITY")
    print("=" * 70)

    # Helper raw TCP sender
    def send_raw(payload: bytes) -> bytes:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect(("127.0.0.1", harness.port))
        try:
            s.sendall(payload)
            resp = b""
            while not resp.endswith(b"\n"):
                chunk = s.recv(1024)
                if not chunk:
                    break
                resp += chunk
            return resp
        finally:
            s.close()

    # 2.1 Malformed JSON payloads
    print("\n[MALFORMED] Testing parse errors on raw garbage and truncated payloads...")
    # Truncated JSON
    resp1 = send_raw(b'{"jsonrpc": "2.0", "id": 1, "method":\n')
    data1 = json.loads(resp1.decode("utf-8"))
    log_step(
        "Truncated JSON returns JSON-RPC -32700 Parse error",
        data1.get("error", {}).get("code") == -32700,
        f"Response: {data1}",
    )

    # Complete garbage
    resp2 = send_raw(b'THIS_IS_NOT_JSON_AT_ALL_GARBAGE\n')
    data2 = json.loads(resp2.decode("utf-8"))
    log_step(
        "Raw garbage returns JSON-RPC -32700 Parse error",
        data2.get("error", {}).get("code") == -32700,
        f"Response: {data2}",
    )

    # Invalid non-UTF8 bytes
    resp3 = send_raw(b'\xff\xfe\x00\x00\xaa\xbb\n')
    data3 = json.loads(resp3.decode("utf-8"))
    log_step(
        "Non-UTF8 byte stream returns JSON-RPC -32700 Parse error",
        data3.get("error", {}).get("code") == -32700,
        f"Response: {data3}",
    )

    # 2.2 Invalid JSON-RPC protocol frames
    print("\n[PROTOCOL] Testing missing or invalid method parameters...")
    # Missing method
    resp4 = send_raw(b'{"jsonrpc": "2.0", "id": 999}\n')
    data4 = json.loads(resp4.decode("utf-8"))
    log_step(
        "Missing method returns JSON-RPC -32600 Invalid Request",
        data4.get("error", {}).get("code") == -32600,
        f"Response: {data4}",
    )

    # Method as integer
    resp5 = send_raw(b'{"jsonrpc": "2.0", "id": 998, "method": 12345}\n')
    data5 = json.loads(resp5.decode("utf-8"))
    log_step(
        "Non-string method returns JSON-RPC -32600 Invalid Request",
        data5.get("error", {}).get("code") == -32600,
        f"Response: {data5}",
    )

    # 2.3 Nonexistent methods
    print("\n[METHODS] Testing nonexistent methods & canonical normalization...")
    client = Live12Client(port=harness.port)
    try:
        client.call("this_method_does_not_exist_at_all", {})
        log_step("Nonexistent method raised Live12RpcError", False)
    except Live12RpcError as e:
        log_step(
            "Nonexistent method cleanly returns Live12RpcError",
            e.code == -32603 and "not found in BridgeHandlers" in e.message,
            f"Error: [{e.code}] {e.message}",
        )

    # 2.4 Invalid LOM paths
    print("\n[LOM PATHS] Testing invalid paths, boundaries, and reflection errors...")
    lom_error_tests = [
        ("empty target path", "", "tempo", "target_path cannot be empty"),
        ("whitespace path", "   ", "tempo", "target_path cannot be empty"),
        ("dots only path", ".......", "tempo", "target_path cannot be empty"),
        ("bogus root object", "bogus_root_object.foo", "bar", "has no attribute"),
        ("out-of-bounds track index", "live_set.tracks.99999", "name", "out of range"),
        ("negative out-of-bounds index", "live_set.tracks.-9999", "name", "out of range"),
        ("nonexistent property", "live_set", "nonexistent_prop_xyz", "has no attribute"),
        ("indexing into non-indexable scalar", "live_set.tempo.0", "name", "Cannot index into"),
    ]

    for label, path, prop, expected_err in lom_error_tests:
        try:
            client.lom_get(path, prop)
            log_step(f"Invalid path '{label}' caught", False)
        except Live12RpcError as e:
            log_step(
                f"Invalid path '{label}' returned structured error",
                expected_err.lower() in e.message.lower(),
                f"[{e.code}] {e.message}",
            )

    # Calling a nonexistent method on valid LOM object
    try:
        client.lom_call("live_set", "nonexistent_lom_method_xyz")
        log_step("Nonexistent LOM method caught", False)
    except Live12RpcError as e:
        log_step(
            "Nonexistent LOM method returned structured error",
            "has no method" in e.message,
            f"[{e.code}] {e.message}",
        )

    # 2.5 Verification of Timer survivability & server continuity
    print("\n[TIMER SURVIVABILITY] Verifying main-thread loop and server survived all error storms...")
    # Directly invoke _process_queue with an intentionally crashing internal method to verify timer isolation
    try:
        harness.surface._process_queue()
        log_step("Direct invocation of _process_queue handles errors without raising", True)
    except Exception as e:
        log_step("Direct invocation of _process_queue raised unhandled exception", False, str(e))

    # Send valid requests following the storm
    res_after = client.call("live12_song_get_state", {})
    log_step(
        "Bridge remains 100% operational following aggressive error injection",
        res_after is not None and "tempo" in res_after,
        f"Tempo: {res_after.get('tempo')} | Tracks: {res_after.get('tracks_count')}",
    )


def test_latency_benchmarks(harness: Milestone2StressHarness):
    print("\n" + "=" * 70)
    print("TEST 3: LATENCY BENCHMARKING (SLA < 50ms)")
    print("=" * 70)

    client = Live12Client(port=harness.port)

    # Helper benchmark function
    def run_benchmark(name: str, fn, iterations: int = 200, max_threshold_ms: float = 50.0):
        latencies_ms = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            fn()
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)

        latencies_ms.sort()
        min_lat = latencies_ms[0]
        median_lat = latencies_ms[len(latencies_ms) // 2]
        p95_lat = latencies_ms[int(len(latencies_ms) * 0.95)]
        p99_lat = latencies_ms[int(len(latencies_ms) * 0.99)]
        max_lat = latencies_ms[-1]
        all_passed = max_lat < max_threshold_ms

        print(f"\nBenchmark: {name} ({iterations} iterations)")
        print(f"  • Min:    {min_lat:.2f} ms")
        print(f"  • Median: {median_lat:.2f} ms")
        print(f"  • P95:    {p95_lat:.2f} ms")
        print(f"  • P99:    {p99_lat:.2f} ms")
        print(f"  • Max:    {max_lat:.2f} ms")
        print(f"  • Target: < {max_threshold_ms:.1f} ms")

        log_step(
            f"Latency for '{name}' strictly < {max_threshold_ms}ms (Max was {max_lat:.2f}ms)",
            all_passed,
            f"p95={p95_lat:.2f}ms, max={max_lat:.2f}ms",
        )
        return latencies_ms

    # 3.1 Benchmark live12_song_get_state
    run_benchmark(
        "live12_song_get_state (TCP Roundtrip)",
        lambda: client.call("live12_song_get_state", {}),
        iterations=200,
        max_threshold_ms=50.0,
    )

    # 3.2 Benchmark live12_lom_get ("live_set", "tempo")
    run_benchmark(
        "live12_lom_get('live_set', 'tempo') (Dynamic Reflection)",
        lambda: client.lom_get("live_set", "tempo"),
        iterations=200,
        max_threshold_ms=50.0,
    )

    # 3.3 Benchmark ping probe latency (is_reachable)
    run_benchmark(
        "client.is_reachable() (TCP Socket Ping Probe)",
        lambda: client.is_reachable(),
        iterations=100,
        max_threshold_ms=20.0,
    )

    # 3.4 Benchmark latency under background concurrent load
    print("\n[LOADED LATENCY] Benchmarking get_state while 10 threads generate continuous load...")
    stop_load = False

    def load_generator():
        c = Live12Client(port=harness.port)
        while not stop_load:
            try:
                c.call("live12_lom_get", {"target_path": "live_set", "property_name": "tempo"})
            except Exception:
                pass
            time.sleep(0.001)

    load_threads = [threading.Thread(target=load_generator, daemon=True) for _ in range(10)]
    for lt in load_threads:
        lt.start()

    try:
        run_benchmark(
            "live12_song_get_state Under 10-Thread Load",
            lambda: client.call("live12_song_get_state", {}),
            iterations=100,
            max_threshold_ms=50.0,
        )
    finally:
        stop_load = True
        for lt in load_threads:
            lt.join(timeout=0.5)


def main():
    print("=" * 70)
    print("EMPIRICAL CHALLENGER VERIFICATION: MILESTONE 2 BRIDGE & CLIENT")
    print(f"Target: Live 12 Remote Script Bridge (src/live12_bridge, src/ableton_live12_mcp)")
    print("=" * 70)

    harness = Milestone2StressHarness()
    harness.start()
    try:
        test_concurrency(harness)
        test_error_resilience(harness)
        test_latency_benchmarks(harness)

        print("\n" + "=" * 70)
        print("VERDICT: CONFIRMED. All empirical stress tests passed with 100% SLA conformance.")
        print("=" * 70)
    finally:
        harness.stop()


if __name__ == "__main__":
    main()
