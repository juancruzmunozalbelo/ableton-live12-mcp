"""
Live 12 Bridge - Control Surface & Main-Thread Bridge
====================================================
Implements the Ableton Live 12 Control Surface Remote Script with
high-frequency main thread execution via Live.Base.Timer, dual-drain
fallback in update_display(), and a background TCP JSON-RPC 2.0 server.
"""

from __future__ import annotations

import contextlib
import json
import os
import queue
import socket
import sys
import threading
import time
import traceback
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

try:
    import Live
except ImportError:
    Live = None

try:
    from _Framework.ControlSurface import ControlSurface
except ImportError:
    try:
        from ableton.v2.control_surface import ControlSurface
    except ImportError:
        # Standalone mock base class when imported outside Ableton Live runtime
        class ControlSurface:
            def __init__(self, c_instance: Any = None):
                self._c_instance = c_instance

            def application(self) -> Any:
                if self._c_instance and hasattr(self._c_instance, "application"):
                    return self._c_instance.application()
                return None

            def song(self) -> Any:
                if self._c_instance and hasattr(self._c_instance, "song"):
                    return self._c_instance.song()
                return None

            def log_message(self, msg: str) -> None:
                if self._c_instance and hasattr(self._c_instance, "log_message"):
                    self._c_instance.log_message(msg)
                else:
                    sys.stderr.write(f"[Live12Bridge] {msg}\n")

            def show_message(self, msg: str) -> None:
                if self._c_instance and hasattr(self._c_instance, "show_message"):
                    self._c_instance.show_message(msg)

            def update_display(self) -> None:
                pass

            def disconnect(self) -> None:
                pass


from .handlers import BridgeHandlers, dispatch_tool_call

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 11246
DISCOVERY_PATH = "/tmp/ableton_live12_bridge.json"
MAX_QUEUE_DRAIN_PER_TICK = 64
# Live.Base.Timer interval (milliseconds). Live dispatches every tick to the main
# thread, and a 5 ms tick burns ~60% of a whole CPU core inside Ableton Live 12,
# which starves the audio engine (silent output / dropped meter updates).
# 20 ms keeps the MCP round trip comfortably below the perceptual floor while
# leaving the engine headroom. Override with LIVE12_BRIDGE_TIMER_MS.
TIMER_INTERVAL_MS = max(5, int(os.environ.get("LIVE12_BRIDGE_TIMER_MS", "20") or 20))


class BridgeJob:
    """Encapsulates an RPC request to be dispatched onto Ableton's main thread."""

    def __init__(self, req_id: Any, method: str, params: Dict[str, Any]):
        self.req_id = req_id
        self.method = method
        self.params = params
        self.done_event = threading.Event()
        self.result: Any = None
        self.error: Optional[Dict[str, Any]] = None


class Live12ControlSurface(ControlSurface):
    """
    Main Control Surface implementation for Ableton Live 12.
    Spawns background TCP listener and dispatches commands onto Live's main thread.
    """

    def __init__(self, c_instance: Any):
        super().__init__(c_instance)
        self._c_instance = c_instance
        self._handlers = BridgeHandlers(self)
        self._request_queue: queue.Queue[BridgeJob] = queue.Queue()
        self._running = True
        self._active_connections: Set[socket.socket] = set()
        self._conn_lock = threading.Lock()
        self._timer: Any = None
        self._server_socket: Optional[socket.socket] = None
        self._server_thread: Optional[threading.Thread] = None
        self._port: int = DEFAULT_PORT

        self._start_server()
        self._setup_timer()

        self.log_message(
            f"Live12Bridge: Control surface initialized successfully on {DEFAULT_HOST}:{self._port} (PID: {os.getpid()})"
        )
        self.show_message(f"Live 12 Bridge active on port {self._port}")

    # -------------------------------------------------------------------------
    # Server & IPC Lifecycle
    # -------------------------------------------------------------------------

    def _start_server(self) -> None:
        """Binds TCP socket and starts background listener thread."""
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # Try default port, fallback dynamically if occupied
        bound = False
        target_ports = [DEFAULT_PORT, 11247, 11248, 11249, 0]
        for p in target_ports:
            try:
                self._server_socket.bind((DEFAULT_HOST, p))
                self._port = self._server_socket.getsockname()[1]
                self._server_socket.listen(16)
                bound = True
                break
            except OSError:
                continue

        if not bound:
            raise RuntimeError("Live12Bridge: Failed to bind TCP listener on any candidate port")

        self._write_discovery_file()

        self._server_thread = threading.Thread(
            target=self._run_tcp_server,
            name="Live12Bridge-TCP-Server",
            daemon=True,
        )
        self._server_thread.start()

    def _write_discovery_file(self) -> None:
        """Writes bridge discovery metadata to /tmp/ableton_live12_bridge.json."""
        meta = {
            "pid": os.getpid(),
            "port": self._port,
            "host": DEFAULT_HOST,
            "live_version": "12.4.6",
            "status": "ready",
            "started_at": time.time(),
        }
        tmp_path = f"{DISCOVERY_PATH}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
            os.replace(tmp_path, DISCOVERY_PATH)
        except Exception as e:
            self.log_message(f"Live12Bridge: Failed to write discovery file: {e}")

    def _run_tcp_server(self) -> None:
        """Accepts incoming TCP connections and spawns client handler threads."""
        while self._running and self._server_socket:
            try:
                conn, _ = self._server_socket.accept()
                with self._conn_lock:
                    self._active_connections.add(conn)
                t = threading.Thread(
                    target=self._handle_client,
                    args=(conn,),
                    name=f"Live12Bridge-Client-{conn.fileno()}",
                    daemon=True,
                )
                t.start()
            except Exception:
                if not self._running:
                    break

    def _handle_client(self, conn: socket.socket) -> None:
        """Processes line-delimited JSON-RPC 2.0 frames for a single client connection."""
        conn.settimeout(60.0)
        buffer = b""
        max_buffer_size = 10 * 1024 * 1024  # 10MB limit to prevent memory exhaustion
        try:
            while self._running:
                data = conn.recv(8192)
                if not data:
                    break
                buffer += data
                if len(buffer) > max_buffer_size:
                    self.log_message("Live12Bridge: Buffer limit exceeded 10MB")
                    err_resp = {
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {"code": -32600, "message": "Request entity too large: buffer exceeded 10MB limit"},
                    }
                    self._send_response(conn, err_resp)
                    break
                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    self._process_raw_frame(conn, line)
        except (socket.timeout, ConnectionResetError, BrokenPipeError):
            pass
        except Exception as e:
            self.log_message(f"Live12Bridge: Error in client connection: {e}")
        finally:
            with self._conn_lock:
                self._active_connections.discard(conn)
            try:
                conn.close()
            except Exception:
                pass

    def _process_raw_frame(self, conn: socket.socket, line: bytes) -> None:
        """Parses a single JSON-RPC line and enqueues it to the main-thread queue."""
        try:
            req_json = json.loads(line.decode("utf-8"))
        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error", "data": str(e)},
            }
            self._send_response(conn, err_resp)
            return

        if not isinstance(req_json, dict):
            err_resp = {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Invalid Request: batch not supported or not an object"},
                "id": None,
            }
            self._send_response(conn, err_resp)
            return

        req_id = req_json.get("id")
        method = req_json.get("method")
        params = req_json.get("params") or {}

        if not method or not isinstance(method, str):
            err_resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32600, "message": "Invalid Request: missing or invalid 'method'"},
            }
            self._send_response(conn, err_resp)
            return

        job = BridgeJob(req_id=req_id, method=method, params=params)
        self._request_queue.put(job)

        # Wait for main-thread execution
        completed = job.done_event.wait(timeout=20.0)
        if not completed:
            err_resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32000,
                    "message": f"Execution timed out on Ableton main thread for method '{method}'",
                },
            }
            self._send_response(conn, err_resp)
            return

        if job.error:
            resp = {"jsonrpc": "2.0", "id": req_id, "error": job.error}
        else:
            resp = {"jsonrpc": "2.0", "id": req_id, "result": job.result}

        self._send_response(conn, resp)

    def _send_response(self, conn: socket.socket, resp: Dict[str, Any]) -> None:
        """Encodes and sends a newline-delimited JSON response."""
        try:
            payload = json.dumps(resp).encode("utf-8") + b"\n"
            conn.sendall(payload)
        except TypeError as e:
            self.log_message(f"Live12Bridge: Non-serializable response: {e}")
            req_id = resp.get("id") if isinstance(resp, dict) else None
            fallback_resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": f"Internal error: non-serializable response: {e}"},
            }
            try:
                payload = json.dumps(fallback_resp).encode("utf-8") + b"\n"
                conn.sendall(payload)
            except Exception as e2:
                self.log_message(f"Live12Bridge: Failed to send fallback error response: {e2}")
        except Exception as e:
            self.log_message(f"Live12Bridge: Failed to send response: {e}")

    # -------------------------------------------------------------------------
    # Main-Thread Scheduler & Execution Queue
    # -------------------------------------------------------------------------

    def _setup_timer(self) -> None:
        """Initializes Live.Base.Timer for main-thread queue polling.

        The interval is deliberately conservative (see TIMER_INTERVAL_MS): every
        tick is a main-thread message inside Live, and an aggressive interval
        starves the audio engine.
        """
        if Live and hasattr(Live, "Base") and hasattr(Live.Base, "Timer"):
            try:
                self._timer = Live.Base.Timer(
                    callback=self._process_queue,
                    interval=TIMER_INTERVAL_MS,
                    repeat=True,
                )
                self._timer.start()
                self.log_message(
                    f"Live12Bridge: Live.Base.Timer active ({TIMER_INTERVAL_MS}ms loop)."
                )
            except Exception as e:
                self.log_message(f"Live12Bridge: Failed to initialize Live.Base.Timer: {e}")
        else:
            self.log_message("Live12Bridge: Native Live.Base.Timer not available in current environment.")

    def _process_queue(self) -> None:
        """
        High-frequency callback invoked on Ableton's main thread by Live.Base.Timer.
        Strictly catches all exceptions so the C++ timer never stops.
        """
        try:
            self._drain_queue()
        except Exception:
            try:
                self.log_message(f"Live12Bridge: Unhandled error in _process_queue:\n{traceback.format_exc()}")
            except Exception:
                pass

    def _drain_queue(self) -> None:
        """Drains and executes pending jobs from the request queue inside component_guard."""
        drained = 0
        while drained < MAX_QUEUE_DRAIN_PER_TICK:
            try:
                job = self._request_queue.get_nowait()
            except queue.Empty:
                break

            drained += 1
            try:
                with self._guard():
                    res = dispatch_tool_call(self._handlers, job.method, job.params)
                    job.result = res
            except (IndexError, ValueError, KeyError, PermissionError, AttributeError, TypeError, RuntimeError) as e:
                # Normal client validation/boundary error - return clean RPC error without dumping traceback to host Log.txt
                job.error = {
                    "code": -32603,
                    "message": str(e),
                    "data": {
                        "exception_type": type(e).__name__,
                    },
                }
            except Exception as e:
                tb = traceback.format_exc()
                self.log_message(f"Live12Bridge: Exception executing '{job.method}': {tb}")
                job.error = {
                    "code": -32603,
                    "message": str(e),
                    "data": {
                        "exception_type": type(e).__name__,
                        "traceback": tb,
                    },
                }
            finally:
                job.done_event.set()

    @contextlib.contextmanager
    def _guard(self) -> Any:
        """Wraps mutations inside Ableton's component_guard if provided by ControlSurface."""
        if hasattr(self, "component_guard") and callable(self.component_guard):
            with self.component_guard():
                yield
        else:
            yield

    def update_display(self) -> None:
        """
        Periodic GUI hook called by Live on the main UI thread.
        Acts as secondary companion drain to guarantee request execution.
        """
        try:
            super().update_display()
        except Exception:
            pass

        try:
            self._drain_queue()
        except Exception:
            try:
                self.log_message(f"Live12Bridge: Error in update_display drain:\n{traceback.format_exc()}")
            except Exception:
                pass

    # -------------------------------------------------------------------------
    # Graceful Teardown
    # -------------------------------------------------------------------------

    def disconnect(self) -> None:
        """Clean teardown on script unload or Ableton shutdown."""
        self._running = False

        if self._timer:
            try:
                self._timer.stop()
            except Exception:
                pass
            self._timer = None

        if self._server_socket:
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None

        with self._conn_lock:
            for conn in list(self._active_connections):
                try:
                    conn.close()
                except Exception:
                    pass
            self._active_connections.clear()

        if os.path.exists(DISCOVERY_PATH):
            try:
                os.remove(DISCOVERY_PATH)
            except Exception:
                pass

        self.log_message("Live12Bridge: Control surface disconnected cleanly.")
        try:
            super().disconnect()
        except Exception:
            pass


# Compatibility aliases
Live12Bridge = Live12ControlSurface
