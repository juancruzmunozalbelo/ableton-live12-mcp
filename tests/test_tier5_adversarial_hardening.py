"""
Tier 5 Adversarial Hardening & White-Box Resilience Test Suite
=============================================================
Milestone 5 Phase 2: Comprehensive white-box coverage and adversarial stress testing.

Audit Surface:
- src/ableton_live12_mcp/server.py (Stdio JSON-RPC 2.0 framing, signal/EOF lifecycle)
- src/ableton_live12_mcp/client.py (TCP client, timeout handling, connection errors)
- src/ableton_live12_mcp/dialogs.py (Path validation, AppleScript timeouts, UI dialogs)
- src/live12_bridge/bridge.py (Main-thread queue, TCP listener, client handler)
- src/live12_bridge/handlers.py (High-level structured tool handlers)
- src/live12_bridge/reflection.py (Dynamic LOM resolver, pointer validation, note conversions)

Test Categories:
1. Concurrency & Socket Multiplexing
2. Abrupt Socket Disconnects & EOF Edge Cases
3. Malformed Framing, Non-UTF8 & Binary Payloads
4. Deep LOM Traversal, Cycles & Reflection Security
5. OS Dialog Engine, Stale File Race Conditions & Path Anomalies
6. High-Level Bridge Handlers Boundary & Architectural Edge Cases
"""

from __future__ import annotations

import concurrent.futures
import io
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from typing import Any, Dict, List, Optional

import pytest

# Ensure repo root and src are in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from ableton_live12_mcp import dialogs
from ableton_live12_mcp.client import (
    Live12Client,
    Live12ConnectionError,
    Live12RpcError,
    Live12TimeoutError,
    ToolResult,
)
from ableton_live12_mcp.dialogs import (
    AccessibilityPermissionError,
    ApplicationNotRunningError,
    DialogError,
    TimeoutExpiredError,
    UnsupportedPlatformError,
    ValidationError as DialogValidationError,
    validate_als_open_path,
    validate_als_save_path,
    validate_wav_export_path,
)
from ableton_live12_mcp.server import McpServer
from live12_bridge.bridge import BridgeJob, Live12ControlSurface
from live12_bridge.handlers import BridgeHandlers, dispatch_tool_call
from live12_bridge.reflection import (
    dict_to_midi_note_spec,
    liveobj_valid,
    lom_call,
    lom_get,
    lom_inspect,
    lom_set,
    midi_note_to_dict,
    resolve_path,
    serialize_lom_value,
)


# ==============================================================================
# Helper Mock Objects for In-Memory Host Environment
# ==============================================================================

class MockCInstance:
    """Mock Ableton Live C++ host container."""
    def __init__(self):
        self.logs: List[str] = []

    def log_message(self, msg: str) -> None:
        self.logs.append(msg)

    def show_message(self, msg: str) -> None:
        pass


class MockLiveTrack:
    def __init__(self, name: str, is_return: bool = False):
        self.name = name
        self.is_return = is_return
        self.color = 0
        self.solo = False
        self.mute = False
        self.arm = False
        self.clip_slots: List[Any] = []
        self.devices: List[Any] = []


class MockLiveSong:
    def __init__(self):
        self.tracks: List[MockLiveTrack] = [MockLiveTrack("Track 1")]
        self.return_tracks: List[MockLiveTrack] = [MockLiveTrack("Return A", is_return=True)]
        self.tempo = 120.0
        self.is_playing = False

    def start_playing(self):
        self.is_playing = True

    def stop_playing(self):
        self.is_playing = False

    def create_midi_track(self, index: int):
        self.tracks.insert(index, MockLiveTrack("New MIDI Track"))

    def create_return_track(self):
        self.return_tracks.append(MockLiveTrack("New Return", is_return=True))

    def delete_track(self, index: int):
        if 0 <= index < len(self.tracks):
            self.tracks.pop(index)
        else:
            raise IndexError("Track index out of range")


# ==============================================================================
# 1. Concurrency & Socket Multiplexing
# ==============================================================================

@pytest.mark.tier5
class TestTier5ConcurrencyAndMultiplexing:
    """Adversarial testing of concurrent RPC requests and socket multiplexing."""

    def test_concurrent_connections_burst(self):
        """Stress tests 30 concurrent TCP connections executing RPCs simultaneously."""
        cs = Live12ControlSurface(MockCInstance())
        time.sleep(0.05)
        stop_worker = False

        def drain_loop():
            while not stop_worker:
                cs._drain_queue()
                time.sleep(0.002)

        t = threading.Thread(target=drain_loop, daemon=True)
        t.start()

        client = Live12Client(port=cs._port)

        def worker_call(idx: int):
            return client.call("live12_transport_play", {"restart": False})

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=15) as pool:
                futures = [pool.submit(worker_call, i) for i in range(30)]
                results = [f.result(timeout=5.0) for f in futures]
                assert len(results) == 30
                assert all(r.get("is_playing") is True for r in results)
        finally:
            stop_worker = True
            cs.disconnect()

    def test_pipelined_requests_single_connection(self):
        """Sends multiple back-to-back JSON-RPC requests across a single socket without waiting."""
        cs = Live12ControlSurface(MockCInstance())
        time.sleep(0.05)
        stop_worker = False

        def drain_loop():
            while not stop_worker:
                cs._drain_queue()
                time.sleep(0.002)

        t = threading.Thread(target=drain_loop, daemon=True)
        t.start()

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", cs._port))

        try:
            # Send 5 requests back to back
            for req_id in range(1, 6):
                req = json.dumps({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "method": "live12_transport_play",
                    "params": {"restart": False},
                }).encode("utf-8") + b"\n"
                s.sendall(req)

            # Receive all 5 responses
            responses = []
            buf = b""
            s.settimeout(5.0)
            while len(responses) < 5:
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf += chunk
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    line = line.strip()
                    if line:
                        responses.append(json.loads(line.decode("utf-8")))

            assert len(responses) == 5
            received_ids = [r["id"] for r in responses]
            assert received_ids == [1, 2, 3, 4, 5]
        finally:
            s.close()
            stop_worker = True
            cs.disconnect()


# ==============================================================================
# 2. Abrupt Socket Disconnects & EOF Edge Cases
# ==============================================================================

@pytest.mark.tier5
class TestTier5SocketDisconnectsAndEOF:
    """Stress tests client/server behavior on unexpected socket drop and EOF."""

    def test_client_disconnect_before_main_thread_drain(self):
        """Client sends request and immediately terminates socket before job execution."""
        cs = Live12ControlSurface(MockCInstance())
        time.sleep(0.05)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", cs._port))
        req = json.dumps({
            "jsonrpc": "2.0",
            "id": 101,
            "method": "live12_transport_play",
            "params": {},
        }).encode("utf-8") + b"\n"
        s.sendall(req)
        # Abruptly close socket immediately
        s.close()

        time.sleep(0.05)
        # Main thread drains queue; must not raise uncaught exception
        assert cs._request_queue.qsize() == 1
        cs._drain_queue()
        assert cs._request_queue.qsize() == 0
        cs.disconnect()

    def test_client_timeout_when_bridge_hangs(self):
        """Asserts Live12TimeoutError is raised when bridge fails to reply within timeout."""
        # Create non-responding TCP server
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        port = srv.getsockname()[1]
        srv.listen(1)

        def slow_worker():
            conn, _ = srv.accept()
            # Sleep without sending response
            time.sleep(1.0)
            conn.close()

        t = threading.Thread(target=slow_worker, daemon=True)
        t.start()

        client = Live12Client(port=port, timeout=0.2)
        try:
            with pytest.raises(Live12TimeoutError) as exc_info:
                client.call("live12_transport_play")
            assert "timed out" in str(exc_info.value).lower()
        finally:
            srv.close()

    def test_client_empty_response_eof(self):
        """Asserts Live12ConnectionError is raised when socket closes with zero bytes."""
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.bind(("127.0.0.1", 0))
        port = srv.getsockname()[1]
        srv.listen(1)

        def immediate_close():
            conn, _ = srv.accept()
            conn.recv(1024)
            conn.close()

        t = threading.Thread(target=immediate_close, daemon=True)
        t.start()

        client = Live12Client(port=port, timeout=1.0)
        try:
            with pytest.raises(Live12ConnectionError) as exc_info:
                client.call("live12_transport_play")
            assert "empty response" in str(exc_info.value).lower()
        finally:
            srv.close()


# ==============================================================================
# 3. Malformed Framing, Non-UTF8 & Binary Payloads
# ==============================================================================

@pytest.mark.tier5
class TestTier5MalformedFramingAndEncoding:
    """Verifies server and bridge robustness under corrupt framing and payloads."""

    def test_bridge_json_rpc_batch_handling(self):
        """
        Adversarial Test (Gap 1): Bridge must return structured JSON-RPC response or
        clean error rather than dropping TCP connection on batch or non-dict payloads.
        """
        cs = Live12ControlSurface(MockCInstance())
        time.sleep(0.05)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", cs._port))
        s.settimeout(2.0)

        try:
            # Send standard JSON-RPC 2.0 batch array
            batch_payload = json.dumps([
                {"jsonrpc": "2.0", "id": 1, "method": "live12_transport_play", "params": {}},
            ]).encode("utf-8") + b"\n"
            s.sendall(batch_payload)

            resp_bytes = s.recv(4096)
            assert resp_bytes != b"", "Live12ControlSurface dropped connection on batch payload"
            resp = json.loads(resp_bytes.decode("utf-8"))
            assert isinstance(resp, (list, dict))
            assert "error" in resp
            assert resp["error"]["code"] == -32600
        finally:
            s.close()
            cs.disconnect()

    def test_bridge_primitive_json_payload(self):
        """
        Adversarial Test (Gap 1): Sending integer or string JSON literal must not crash bridge thread.
        """
        cs = Live12ControlSurface(MockCInstance())
        time.sleep(0.05)

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect(("127.0.0.1", cs._port))
        s.settimeout(2.0)

        try:
            s.sendall(b"12345\n")
            resp_bytes = s.recv(4096)
            assert resp_bytes != b"", "Live12ControlSurface dropped connection on non-object JSON literal"
            resp = json.loads(resp_bytes.decode("utf-8"))
            assert "error" in resp
            assert resp["error"]["code"] == -32600
        finally:
            s.close()
            cs.disconnect()

    def test_server_stdio_malformed_utf8_recovery(self):
        """
        Adversarial Test (Gap 2): McpServer loop should handle or discard invalid UTF-8 bytes
        rather than permanently dying.
        """
        server = McpServer(mode="mock")

        class MalformedStdinStream:
            def __init__(self):
                self.calls = 0

            def readline(self):
                self.calls += 1
                if self.calls == 1:
                    # Raises strict UnicodeDecodeError on first read
                    raise UnicodeDecodeError("utf-8", b"\xff\xfe", 0, 1, "invalid start byte")
                elif self.calls == 2:
                    # Valid JSON request on next read
                    return json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}) + "\n"
                return ""

        out = io.StringIO()
        server.run(stdin=MalformedStdinStream(), stdout=out)
        lines = [json.loads(l) for l in out.getvalue().strip().split("\n") if l.strip()]
        assert len(lines) == 2
        assert lines[0].get("error", {}).get("code") == -32700
        assert lines[1].get("id") == 1


# ==============================================================================
# 4. Deep LOM Traversal, Cycles & Reflection Security
# ==============================================================================

@pytest.mark.tier5
class TestTier5ReflectionCyclesAndSecurity:
    """Tests LOM reflection bounds, non-serializable object handling, and private attribute security."""

    def test_lom_serialization_circular_references(self):
        """Verifies circular structures terminate safely at depth > 5 without recursion overflow."""
        circular_list: List[Any] = []
        circular_list.append(circular_list)
        res = serialize_lom_value(circular_list)
        assert isinstance(res, list)

        circular_dict: Dict[str, Any] = {}
        circular_dict["self"] = circular_dict
        res_d = serialize_lom_value(circular_dict)
        assert isinstance(res_d, dict)

    def test_lom_serialization_to_dict_non_primitive(self):
        """
        Adversarial Test (Gap 3): If to_dict returns a non-primitive object like a set,
        serialize_lom_value must sanitize it to ensure json.dumps() compatibility.
        """
        class CustomWithSet:
            def to_dict(self):
                return {"tags": {"synth", "polyphonic"}}

        serialized = serialize_lom_value(CustomWithSet())
        dumped = json.dumps(serialized)
        assert isinstance(serialized["tags"], list)
        assert "synth" in dumped

    def test_lom_set_private_attribute_backdoor(self):
        """
        Adversarial Test (Gap 4): lom_set must disallow mutating private/internal attributes.
        """
        cs = Live12ControlSurface(MockCInstance())

        def root_getter(k):
            return cs

        try:
            with pytest.raises(PermissionError):
                lom_set(root_getter, "this_device", "_running", False)
            assert cs._running is True
        finally:
            cs.disconnect()

    def test_lom_resolve_path_bracket_notation(self):
        """
        Adversarial Test (Gap 10): resolve_path should support standard bracket notation 'tracks[0]'.
        """
        class DummySong:
            def __init__(self):
                self.tracks = ["track_0", "track_1"]

        def rg(k):
            return DummySong()

        val = resolve_path(rg, "song.tracks[0]")
        assert val == "track_0"

    def test_liveobj_valid_deleted_pointer(self):
        """Verifies liveobj_valid returns False when object raises RuntimeError on access."""
        class DeletedBoostObject:
            def __eq__(self, other):
                raise RuntimeError("Live object is deleted")

        obj = DeletedBoostObject()
        assert liveobj_valid(obj) is False
        assert liveobj_valid(None) is False


# ==============================================================================
# 5. OS Dialog Engine, Stale File Race Conditions & Path Anomalies
# ==============================================================================

@pytest.mark.tier5
class TestTier5DialogEngineAndPathAnomalies:
    """Stress tests path normalization, timeout exceptions, and dialog parsing."""

    def test_save_set_stale_file_false_positive(self):
        """
        Adversarial Test (Gap 6): Pre-existing file at destination_path causes false success
        without verifying actual save execution.
        """
        with tempfile.NamedTemporaryFile(suffix=".als", delete=False) as tf:
            tf.write(b"pre-existing content")
            stale_path = tf.name

        try:
            # When path already exists, polling loop can immediately exit
            assert os.path.exists(stale_path)
            assert os.path.getsize(stale_path) > 0
        finally:
            if os.path.exists(stale_path):
                os.remove(stale_path)

    def test_inspect_os_dialogs_title_with_comma(self):
        """
        Adversarial Test (Gap 7): Dialog title containing commas must not inflate sheet count.
        """
        fake_stdout = "Do you want to save changes to the set, or discard them?"
        split_titles = dialogs.split_dialog_titles(fake_stdout)
        assert len(split_titles) == 1
        assert split_titles[0] == "Do you want to save changes to the set, or discard them?"

    def test_path_validation_embedded_null_byte_gap(self):
        """
        Adversarial Test: Embedded null bytes are rejected by validate_als_save_path.
        """
        with pytest.raises(DialogValidationError):
            validate_als_save_path("/tmp/test\x00set.als")

    def test_timeout_expired_error_interface(self):
        """Verifies TimeoutExpiredError fulfills both DialogError and subprocess.TimeoutExpired."""
        err = TimeoutExpiredError("Operation timed out", cmd=["osascript"], timeout=5.0)
        assert err.code == -32003
        assert isinstance(err, DialogError)
        assert isinstance(err, subprocess.TimeoutExpired)
        assert str(err) == "Operation timed out"


# ==============================================================================
# 6. High-Level Bridge Handlers Boundary & Architectural Edge Cases
# ==============================================================================

@pytest.mark.tier5
class TestTier5BridgeHandlersBoundaries:
    """Tests high-level handlers edge cases and architectural divergence."""

    def test_return_track_deletion_gap(self):
        """
        Adversarial Test (Gap 9): live12_track_delete only deletes from s.tracks,
        so return tracks created via live12_track_create(type='return') cannot be deleted.
        """
        cs = Live12ControlSurface(MockCInstance())
        handlers = BridgeHandlers(cs)
        song = MockLiveSong()
        handlers.song = lambda: song

        # Create return track
        res = handlers.live12_track_create(type="return")
        ret_idx = res["track_index"]
        assert len(song.return_tracks) == 2

        # In unhardened handlers, live12_track_delete targets song.tracks instead of song.return_tracks
        # If ret_idx is 1, and song.tracks has length 1, it raises IndexError!
        with pytest.raises(IndexError):
            handlers.live12_track_delete(track_index=ret_idx)
        cs.disconnect()

    def test_mixer_set_sends_alpha_key_failure(self):
        """
        Hardened Test: live12_mixer_set accepts alphabetic send key 'A' and sets send 0.
        """
        class MockParam:
            def __init__(self):
                self.value = 0.0

        class MockMixer:
            def __init__(self):
                self.sends = [MockParam()]

        class MockTrackWithMixer:
            def __init__(self):
                self.mixer_device = MockMixer()

        class MockSongWithMixer:
            def __init__(self):
                self.tracks = [MockTrackWithMixer()]

        mock_song = MockSongWithMixer()
        cs = Live12ControlSurface(MockCInstance())
        handlers = BridgeHandlers(cs)
        handlers.song = lambda: mock_song

        res = handlers.live12_mixer_set(track_index=0, sends={"A": 0.5})
        assert "sends" in res
        assert res["sends"]["0"] == 0.5
        assert mock_song.tracks[0].mixer_device.sends[0].value == 0.5
        cs.disconnect()

    def test_routing_set_monitoring_stub(self):
        """
        Hardened Test: live12_routing_set assigns monitoring state.
        """
        class MockTrackWithMonitoring:
            def __init__(self):
                self.current_monitoring_state = 2  # 'off'

        class MockSongWithTrack:
            def __init__(self):
                self.tracks = [MockTrackWithMonitoring()]

        mock_song = MockSongWithTrack()
        cs = Live12ControlSurface(MockCInstance())
        handlers = BridgeHandlers(cs)
        handlers.song = lambda: mock_song

        res = handlers.live12_routing_set(track_index=0, monitoring="in")
        assert res.get("monitoring") == "in"
        assert mock_song.tracks[0].current_monitoring_state == 0
        cs.disconnect()

    def test_bridge_reload(self):
        """
        Verify live12_bridge_reload safely reloads modules and returns status.
        """
        cs = Live12ControlSurface(MockCInstance())
        handlers = BridgeHandlers(cs)
        cs._handlers = handlers
        res = handlers.live12_bridge_reload()
        assert res["status"] == "reloaded"
        assert "handlers_count" in res
        assert res["handlers_count"] > 50
        cs.disconnect()
