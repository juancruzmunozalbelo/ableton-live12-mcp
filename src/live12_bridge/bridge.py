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
import select
import socket
import sys
import threading
import time
import traceback
import uuid
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


from . import handlers as handlers_mod
from .handlers import BridgeHandlers, dispatch_tool_call

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 11246
DISCOVERY_PATH = "/tmp/ableton_live12_bridge.json"
MAX_REQUEST_QUEUE_SIZE = 256
MAX_QUEUE_DRAIN_PER_TICK = 64
MAX_DRAIN_SECONDS_PER_TICK = 0.012
BRIDGE_TIMEOUT_SECONDS = 25.0
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
        self._lock = threading.Lock()
        self.state: str = "pending"
        self.done_event = threading.Event()
        self.cancelled = threading.Event()
        self.result: Any = None
        self.error: Optional[Dict[str, Any]] = None

    def try_start(self) -> bool:
        """Atomically transitions pending -> running if not already cancelled."""
        with self._lock:
            if self.state != "pending" or self.cancelled.is_set():
                if self.state == "pending":
                    self.state = "cancelled"
                return False
            self.state = "running"
            return True

    def try_cancel(self) -> bool:
        """Atomically transitions pending -> cancelled. Returns False if already running/done."""
        with self._lock:
            if self.state != "pending":
                return False
            self.state = "cancelled"
            self.cancelled.set()
            return True

    def mark_done(self) -> None:
        """Marks a running job as done and signals waiting callers."""
        with self._lock:
            if self.state != "cancelled":
                self.state = "done"
        self.done_event.set()


class Live12ControlSurface(ControlSurface):
    """
    Main Control Surface implementation for Ableton Live 12.
    Spawns background TCP listener and dispatches commands onto Live's main thread.
    """

    def __init__(self, c_instance: Any):
        super().__init__(c_instance)
        self._c_instance = c_instance
        self._handlers = BridgeHandlers(self)
        self._request_queue: queue.Queue[BridgeJob] = queue.Queue(maxsize=MAX_REQUEST_QUEUE_SIZE)
        self._running = True
        self._active_connections: Set[socket.socket] = set()
        self._conn_lock = threading.Lock()
        self._drain_lock = threading.Lock()
        self._timer: Any = None
        self._server_socket: Optional[socket.socket] = None
        self._server_thread: Optional[threading.Thread] = None
        self._port: int = DEFAULT_PORT

        try:
            self._start_server()
            self._setup_timer()
        except Exception:
            self.disconnect()
            raise

        self.log_message(
            f"Live12Bridge: Control surface initialized successfully on {DEFAULT_HOST}:{self._port} (PID: {os.getpid()})"
        )
        self.show_message(f"Live 12 Bridge active on port {self._port}")

    # -------------------------------------------------------------------------
    # Server & IPC Lifecycle
    # -------------------------------------------------------------------------

    def _start_server(self) -> None:
        """Binds TCP socket and starts background listener thread."""
        # Try default port, fallback dynamically if occupied
        bound = False
        target_ports = [DEFAULT_PORT, 11247, 11248, 11249, 0]
        for p in target_ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((DEFAULT_HOST, p))
                self._port = sock.getsockname()[1]
                sock.listen(16)
                self._server_socket = sock
                bound = True
                break
            except OSError:
                try:
                    sock.close()
                except Exception:
                    pass
                continue
            except Exception:
                try:
                    sock.close()
                except Exception:
                    pass
                raise

        if not bound:
            raise RuntimeError("Live12Bridge: Failed to bind TCP listener on any candidate port")

        self._write_discovery_file()

        self._server_thread = threading.Thread(
            target=self._run_tcp_server,
            name="Live12Bridge-TCP-Server",
            daemon=True,
        )
        self._server_thread.start()

    def _get_live_version(self) -> str:
        """Queries the active Ableton Live version from Application when available."""
        app = self.application()
        if app is not None:
            if (
                hasattr(app, "get_major_version")
                and hasattr(app, "get_minor_version")
                and hasattr(app, "get_bugfix_version")
            ):
                try:
                    major = app.get_major_version()
                    minor = app.get_minor_version()
                    bugfix = app.get_bugfix_version()
                    return f"{major}.{minor}.{bugfix}"
                except Exception as e:
                    self.log_message(f"Live12Bridge: Failed to query Live version: {e}")
            if hasattr(app, "get_version_string"):
                try:
                    ver = str(app.get_version_string()).strip()
                    if ver:
                        return ver
                except Exception:
                    pass
        return "12.4.6"

    def _write_discovery_file(self) -> None:
        """Writes bridge discovery metadata to /tmp/ableton_live12_bridge.json with 0o600 permissions."""
        meta = {
            "pid": os.getpid(),
            "port": self._port,
            "host": DEFAULT_HOST,
            "live_version": self._get_live_version(),
            "status": "ready",
            "started_at": time.time(),
        }
        nonce = uuid.uuid4().hex[:8]
        tmp_path = f"{DISCOVERY_PATH}.tmp.{os.getpid()}.{self._port}.{nonce}"
        try:
            fd = os.open(tmp_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=2)
            os.chmod(tmp_path, 0o600)
            os.replace(tmp_path, DISCOVERY_PATH)
        except Exception as e:
            self.log_message(f"Live12Bridge: Failed to write discovery file: {e}")
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except Exception:
                pass

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
                    if not self._process_raw_frame(conn, line):
                        return
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

    @staticmethod
    def _is_socket_closed(conn: socket.socket) -> bool:
        """Non-blocking probe to detect if the peer reset or aborted the TCP socket.

        Does NOT treat a peer SHUT_WR half-close (EOF b"") as dead so the bridge
        still delivers the pending JSON-RPC reply to half-closed clients, and
        forces non-blocking mode during MSG_PEEK so a 60s socket timeout never stalls.
        """
        try:
            if conn.fileno() < 0:
                return True
            if conn.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR) != 0:
                return True
            rlist, _, xlist = select.select([conn], [], [conn], 0.0)
            if xlist:
                return True
            if rlist:
                flags = socket.MSG_PEEK | getattr(socket, "MSG_DONTWAIT", 0)
                prev_timeout = conn.gettimeout() if hasattr(conn, "gettimeout") else None
                try:
                    if prev_timeout is not None and prev_timeout != 0.0 and hasattr(conn, "settimeout"):
                        conn.settimeout(0.0)
                    conn.recv(1, flags)
                    # b"" indicates client write-side EOF (e.g. SHUT_WR); reply can still be sent.
                    return False
                except (BlockingIOError, InterruptedError):
                    return False
                except (ConnectionResetError, BrokenPipeError, OSError):
                    return True
                finally:
                    if prev_timeout is not None and prev_timeout != 0.0 and hasattr(conn, "settimeout"):
                        try:
                            conn.settimeout(prev_timeout)
                        except (OSError, ValueError):
                            pass
        except (OSError, ValueError):
            return True
        return False

    def _wait_for_job(self, conn: socket.socket, job: BridgeJob, timeout: float = BRIDGE_TIMEOUT_SECONDS) -> Tuple[bool, bool]:
        """Waits for job completion, cancelling on timeout or client disconnect.

        Returns (completed, socket_closed).
        """
        if not isinstance(conn, socket.socket):
            completed = job.done_event.wait(timeout=timeout)
            if not completed:
                if not job.try_cancel() and job.done_event.is_set():
                    return True, False
            return completed, False

        deadline = time.monotonic() + timeout
        while self._running:
            remaining = deadline - time.monotonic()
            if remaining <= 0.0:
                if not job.try_cancel() and job.done_event.is_set():
                    return True, False
                return False, False
            if job.done_event.wait(timeout=min(0.25, remaining)):
                return True, False
            if self._is_socket_closed(conn):
                job.try_cancel()
                return False, True
        job.try_cancel()
        return False, True

    def _process_raw_frame(self, conn: socket.socket, line: bytes) -> bool:
        """Parses a single JSON-RPC line and enqueues it to the main-thread queue."""
        try:
            req_json = json.loads(line.decode("utf-8"))
        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error", "data": str(e)},
            }
            return self._send_response(conn, err_resp)

        if not isinstance(req_json, dict):
            err_resp = {
                "jsonrpc": "2.0",
                "error": {"code": -32600, "message": "Invalid Request: batch not supported or not an object"},
                "id": None,
            }
            return self._send_response(conn, err_resp)

        req_id = req_json.get("id")
        method = req_json.get("method")
        raw_params = req_json.get("params")
        if raw_params is None:
            params: Dict[str, Any] = {}
        elif isinstance(raw_params, dict):
            params = raw_params
        else:
            err_resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32602,
                    "message": f"Invalid params: expected object, got {type(raw_params).__name__}",
                },
            }
            return self._send_response(conn, err_resp)

        if not method or not isinstance(method, str):
            err_resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32600, "message": "Invalid Request: missing or invalid 'method'"},
            }
            return self._send_response(conn, err_resp)

        job = BridgeJob(req_id=req_id, method=method, params=params)
        try:
            self._request_queue.put_nowait(job)
        except queue.Full:
            err_resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32001,
                    "message": "Server busy: request queue is full",
                },
            }
            return self._send_response(conn, err_resp)

        # Wait for main-thread execution; cancel if timed out or client disconnected
        completed, sock_closed = self._wait_for_job(conn, job, timeout=BRIDGE_TIMEOUT_SECONDS)
        if sock_closed:
            return False
        if not completed:
            err_resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32000,
                    "message": f"Execution timed out on Ableton main thread for method '{method}'",
                },
            }
            return self._send_response(conn, err_resp)

        if job.error:
            resp = {"jsonrpc": "2.0", "id": req_id, "error": job.error}
        else:
            resp = {"jsonrpc": "2.0", "id": req_id, "result": job.result}

        return self._send_response(conn, resp)

    def _send_response(self, conn: socket.socket, resp: Dict[str, Any]) -> bool:
        """Encodes and sends a newline-delimited JSON response. Returns False if connection failed."""
        try:
            payload = json.dumps(resp).encode("utf-8") + b"\n"
            conn.sendall(payload)
            return True
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
                return True
            except Exception as e2:
                self.log_message(f"Live12Bridge: Failed to send fallback error response: {e2}")
                return False
        except Exception as e:
            self.log_message(f"Live12Bridge: Failed to send response: {e}")
            return False

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
        if not self._drain_lock.acquire(blocking=False):
            return
        try:
            drained = 0
            steps = 0
            max_steps = MAX_QUEUE_DRAIN_PER_TICK * 16
            deadline = time.monotonic() + MAX_DRAIN_SECONDS_PER_TICK
            while drained < MAX_QUEUE_DRAIN_PER_TICK and steps < max_steps:
                if steps > 0 and time.monotonic() >= deadline:
                    break
                try:
                    job = self._request_queue.get_nowait()
                except queue.Empty:
                    break

                steps += 1
                if not job.try_start():
                    job.done_event.set()
                    continue

                drained += 1
                try:
                    with self._guard():
                        res = handlers_mod.dispatch_tool_call(self._handlers, job.method, job.params)
                        job.result = res
                except (IndexError, ValueError, KeyError, PermissionError) as e:
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
                    job.mark_done()
        finally:
            self._drain_lock.release()

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
                self._server_socket.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self._server_socket.close()
            except Exception:
                pass
            self._server_socket = None

        with self._conn_lock:
            for conn in list(self._active_connections):
                try:
                    conn.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass
                try:
                    conn.close()
                except Exception:
                    pass
            self._active_connections.clear()

        while True:
            try:
                pending_job = self._request_queue.get_nowait()
            except queue.Empty:
                break
            if pending_job.try_cancel():
                pending_job.error = {
                    "code": -32000,
                    "message": "Bridge disconnected before request could execute",
                }
            pending_job.done_event.set()

        if self._server_thread is not None and self._server_thread.is_alive():
            if threading.current_thread() is not self._server_thread:
                self._server_thread.join(timeout=1.0)
        self._server_thread = None

        if self._handlers and hasattr(self._handlers, "close_open_undo_steps"):
            try:
                self._handlers.close_open_undo_steps()
            except Exception as e:
                self.log_message(f"Live12Bridge: Error closing open undo steps on disconnect: {e}")

        if os.path.exists(DISCOVERY_PATH):
            try:
                with open(DISCOVERY_PATH, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                if (
                    isinstance(meta, dict)
                    and meta.get("pid") == os.getpid()
                    and meta.get("port") == self._port
                ):
                    os.remove(DISCOVERY_PATH)
            except Exception as e:
                self.log_message(f"Live12Bridge: Failed to remove discovery file: {e}")

        self.log_message("Live12Bridge: Control surface disconnected cleanly.")
        try:
            super().disconnect()
        except Exception:
            pass


# Compatibility aliases
Live12Bridge = Live12ControlSurface
