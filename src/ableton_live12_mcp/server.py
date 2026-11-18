"""
Ableton Live 12 MCP Server - Stdio JSON-RPC 2.0 Engine
======================================================
Implements pure Python stdlib Model Context Protocol (MCP) server:
- Newline-delimited JSON-RPC 2.0 framing over stdin/stdout.
- Clean stderr logging (zero stdout pollution).
- Lifecycle handshake: initialize (2024-11-05), notifications/initialized, ping.
- Discovery: tools/list (77 tools with Draft-07 schemas).
- Invocation: tools/call dispatching to Live12Client and macOS dialogs.
- Standard JSON-RPC error codes and MCP isError result handling.
- Graceful shutdown on EOF and POSIX signals (SIGINT, SIGTERM).
"""

from __future__ import annotations

import argparse
import inspect
import json
import logging
import os
import select
import signal
import sys
from typing import Any, Callable, Dict, List, Optional, TextIO, Union

from .client import DEFAULT_DISCOVERY_PATH, Live12Client, LiveTcpClient, ToolResult
from .tools import ValidationError, get_tool_catalog, validate_argument_dict, validate_tool_call
from .tools.take_lane_tools import TAKE_LANE_TOOLS
from . import dialogs
from .dialogs import DialogError

logger = logging.getLogger("ableton_live12_mcp.server")

MCP_PROTOCOL_VERSION = "2024-11-05"
SERVER_NAME = "ableton-live12-mcp"
SERVER_VERSION = "1.1.0"


class JsonRpcProtocolError(Exception):
    """JSON-RPC 2.0 protocol error with code and optional data."""

    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.data = data


class McpServer:
    """
    Pure Python standard library Model Context Protocol Server for Ableton Live 12.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        mode: str = "auto",
        discovery_path: Optional[str] = None,
    ):
        self.mode = mode.lower()  # "auto", "live", "mock"
        self.host = host
        self.port = port
        self.discovery_path = discovery_path or DEFAULT_DISCOVERY_PATH
        self._running = False
        self.initialized = False
        self._wakeup_r: Optional[int] = None
        self._wakeup_w: Optional[int] = None

        # Live TCP Client
        self._live_client: Optional[Live12Client] = None
        # Mock Bridge (only initialized in explicit mock mode)
        self._mock_bridge: Optional[Any] = None

        # Registered tool extensions (e.g. live12_take_lane_create_audio_clip)
        self._registered_tools: Dict[str, Dict[str, Any]] = {t["name"]: t for t in TAKE_LANE_TOOLS}

        self._init_backend()

    def register_tool(self, tool_def: Dict[str, Any]) -> None:
        """Registers an additional tool definition into the server instance."""
        self._registered_tools[tool_def["name"]] = tool_def

    def _init_backend(self) -> None:
        """Initializes client connectors and evaluates mock/live execution mode."""
        env_mode = os.environ.get("ABLETON_TEST_MODE", "").lower()
        if self.mode == "mock" or (self.mode == "auto" and env_mode == "mock"):
            self.mode = "mock"
            self._mock_bridge = self._init_mock_bridge()
            logger.info("McpServer initialized in MOCK mode.")
            return

        if self.mode not in ("auto", "live"):
            raise ValueError(f"Invalid server mode {self.mode!r}; expected 'auto', 'live', or 'mock'.")

        # Never silently fall back to MockAbletonBridge when Ableton Live is closed.
        # Keep live routing active so Live12Client dynamically discovers Live whenever it starts.
        self.mode = "live"
        self._live_client = Live12Client(
            host=self.host, port=self.port, discovery_path=self.discovery_path
        )
        logger.info(
            f"McpServer initialized in LIVE mode targeting {self._live_client.host}:{self._live_client.port}"
        )

    def _init_mock_bridge(self) -> Optional[Any]:
        """Loads MockAbletonBridge from tests.harness with repo path resolution."""
        try:
            from tests.harness import MockAbletonBridge
            return MockAbletonBridge()
        except ImportError:
            repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
            if repo_root not in sys.path:
                sys.path.insert(0, repo_root)
            try:
                from tests.harness import MockAbletonBridge
                return MockAbletonBridge()
            except ImportError as e:
                logger.warning(f"Unable to load MockAbletonBridge: {e}")
                return None

    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Dispatches tool execution to the appropriate backend."""
        # 0. Upfront OS tools path validation (enforced uniformly across live and mock modes)
        if name in {"live12_os_save_set", "live12_os_open_set", "live12_os_export_audio"}:
            try:
                if name == "live12_os_save_set":
                    dialogs.validate_als_save_path(arguments.get("destination_path", ""))
                elif name == "live12_os_open_set":
                    dialogs.validate_als_open_path(arguments.get("als_path", ""))
                elif name == "live12_os_export_audio":
                    dialogs.validate_wav_export_path(arguments.get("destination_wav_path", ""))
            except Exception as e:
                err_payload = {"error": str(e), "type": type(e).__name__}
                if hasattr(e, "code"):
                    err_payload["code"] = getattr(e, "code")
                return ToolResult(
                    is_error=True,
                    content=[{"type": "text", "text": json.dumps(err_payload)}],
                    raw=err_payload,
                )

        # 1. Mock mode routing
        if self.mode == "mock":
            if not self._mock_bridge:
                self._mock_bridge = self._init_mock_bridge()
            if self._mock_bridge:
                return self._mock_bridge.execute_tool(name, arguments)
            return ToolResult(
                is_error=True,
                content=[{
                    "type": "text",
                    "text": json.dumps({
                        "code": -32000,
                        "message": f"Bridge unreachable and MockAbletonBridge unavailable for tool '{name}'",
                    })
                }],
                raw={"code": -32000, "message": "Backend unavailable"}
            )

        # 2. Live mode OS-level tools routing (direct to dialogs.py)
        if name in {"live12_os_save_set", "live12_os_open_set", "live12_os_export_audio"}:
            try:
                if name == "live12_os_save_set":
                    result = dialogs.save_set(
                        destination_path=arguments["destination_path"],
                        timeout_sec=arguments.get("timeout_sec", 10.0),
                        overwrite=arguments.get("overwrite", True),
                    )
                elif name == "live12_os_open_set":
                    result = dialogs.open_set(
                        als_path=arguments["als_path"],
                        timeout_sec=arguments.get("timeout_sec", 10.0),
                        discard_unsaved=arguments.get("discard_unsaved", True),
                    )
                elif name == "live12_os_export_audio":
                    result = dialogs.export_audio(
                        destination_wav_path=arguments["destination_wav_path"],
                        render_settings=arguments.get("render_settings"),
                        timeout_sec=arguments.get("timeout_sec", 30.0),
                    )
                else:
                    result = {}
                return ToolResult(
                    is_error=False,
                    content=[{"type": "text", "text": json.dumps(result)}],
                    raw=result,
                )
            except Exception as e:
                err_payload = {"error": str(e), "type": type(e).__name__}
                if hasattr(e, "code"):
                    err_payload["code"] = getattr(e, "code")
                return ToolResult(
                    is_error=True,
                    content=[{"type": "text", "text": json.dumps(err_payload)}],
                    raw=err_payload,
                )

        # 3. Live mode LOM tools routing (via TCP to Remote Script)
        if not self._live_client:
            self._live_client = Live12Client(
                host=self.host, port=self.port, discovery_path=self.discovery_path
            )
        return self._live_client.call_tool(name, arguments)

    # -------------------------------------------------------------------------
    # Core JSON-RPC 2.0 Dispatchers
    # -------------------------------------------------------------------------

    def _handle_initialize(self, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        self.initialized = True
        return {
            "protocolVersion": MCP_PROTOCOL_VERSION,
            "capabilities": {
                "tools": {},
            },
            "serverInfo": {
                "name": SERVER_NAME,
                "version": SERVER_VERSION,
            },
        }

    def _handle_ping(self, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        return {}

    def _handle_tools_list(self, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        merged: Dict[str, Dict[str, Any]] = {t["name"]: t for t in get_tool_catalog()}
        merged.update(self._registered_tools)
        return {"tools": list(merged.values())}

    def _handle_tools_call(self, params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(params, dict):
            raise JsonRpcProtocolError(-32602, "Invalid params: 'params' must be a JSON object")

        tool_name = params.get("name")
        if not tool_name or not isinstance(tool_name, str):
            raise JsonRpcProtocolError(-32602, "Invalid params: 'name' is required and must be a string")

        arguments = params.get("arguments")
        if arguments is None:
            arguments = {}
        elif not isinstance(arguments, dict):
            raise JsonRpcProtocolError(-32602, "Invalid params: 'arguments' must be a JSON object if provided")

        try:
            if tool_name in self._registered_tools:
                validate_argument_dict(
                    self._registered_tools[tool_name].get("inputSchema", {}),
                    arguments,
                    path=tool_name,
                )
            else:
                validate_tool_call(tool_name, arguments)
        except ValidationError as e:
            err_dict = {
                "error": str(e),
                "type": "ValidationError",
            }
            return {
                "content": [{"type": "text", "text": json.dumps(err_dict)}],
                "isError": True,
            }

        tool_result = self.execute_tool(tool_name, arguments)
        return {
            "content": tool_result.content,
            "isError": tool_result.is_error,
        }

    def _handle_notification(self, method: str, params: Optional[Dict[str, Any]]) -> None:
        if method == "notifications/initialized":
            self.initialized = True
            logger.info("Client initialization acknowledged (notifications/initialized).")
        else:
            logger.debug(f"Received notification: {method}")

    def dispatch_request(self, req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Processes a single parsed JSON-RPC request object."""
        req_id = req.get("id")
        is_notification = "id" not in req

        if req.get("jsonrpc") != "2.0":
            if is_notification:
                return None
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: 'jsonrpc' must be exactly '2.0'",
                },
            }

        method = req.get("method")
        if not method or not isinstance(method, str):
            if is_notification:
                return None
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: 'method' must be a non-empty string",
                },
            }

        if is_notification or method.startswith("notifications/"):
            self._handle_notification(method, req.get("params"))
            return None

        params = req.get("params")
        if params is not None and not isinstance(params, (dict, list)):
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32602,
                    "message": "Invalid params: Must be an object or array if provided",
                },
            }

        try:
            if method == "initialize":
                result = self._handle_initialize(params)
            elif method == "ping":
                result = self._handle_ping(params)
            elif method == "tools/list":
                result = self._handle_tools_list(params)
            elif method == "tools/call":
                result = self._handle_tools_call(params)
            else:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32601,
                        "message": f"Method not found: '{method}'",
                    },
                }

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result,
            }
        except JsonRpcProtocolError as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "data": e.data,
                },
            }
        except Exception as e:
            logger.error(f"Internal error processing method '{method}': {e}", exc_info=True)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32603,
                    "message": f"Internal error: {str(e)}",
                },
            }

    def handle_line(self, line: str) -> Optional[Union[Dict[str, Any], List[Dict[str, Any]]]]:
        """Parses and handles a single line from stdin."""
        try:
            data = json.loads(line)
        except Exception as e:
            logger.warning(f"Parse error: {e}")
            return {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32700,
                    "message": f"Parse error: {str(e)}",
                },
            }

        if isinstance(data, list):
            if len(data) == 0:
                return {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32600,
                        "message": "Invalid Request: empty batch",
                    },
                }
            responses = []
            for item in data:
                if isinstance(item, dict):
                    resp = self.dispatch_request(item)
                    if resp is not None:
                        responses.append(resp)
                else:
                    responses.append({
                        "jsonrpc": "2.0",
                        "id": None,
                        "error": {
                            "code": -32600,
                            "message": "Invalid Request: Batch element is not an object",
                        },
                    })
            return responses if responses else None
        elif isinstance(data, dict):
            return self.dispatch_request(data)
        else:
            return {
                "jsonrpc": "2.0",
                "id": None,
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: Payload must be a JSON object or array",
                },
            }

    def _write_response(self, stdout: TextIO, resp: Union[Dict[str, Any], List[Dict[str, Any]]]) -> None:
        payload = json.dumps(resp, separators=(",", ":"))
        stdout.write(payload + "\n")
        stdout.flush()

    def run(self, stdin: TextIO = sys.stdin, stdout: TextIO = sys.stdout) -> None:
        """Main stdio loop reading line-by-line from stdin and writing to stdout."""
        if hasattr(stdin, "reconfigure"):
            try:
                stdin.reconfigure(encoding="utf-8")
            except Exception:
                pass
        if hasattr(stdout, "reconfigure"):
            try:
                stdout.reconfigure(encoding="utf-8")
            except Exception:
                pass

        self._running = True
        logger.info(f"Ableton Live 12 MCP Server running over stdio (mode={self.mode}).")

        stdin_fd: Optional[int] = None
        if hasattr(stdin, "fileno"):
            try:
                stdin_fd = stdin.fileno()
            except Exception:
                stdin_fd = None

        if stdin_fd is not None:
            self._wakeup_r, self._wakeup_w = os.pipe()
            buf = b""
            try:
                while self._running:
                    try:
                        readable, _, _ = select.select([stdin_fd, self._wakeup_r], [], [])
                    except InterruptedError:
                        continue
                    except KeyboardInterrupt:
                        logger.info("KeyboardInterrupt received. Stopping.")
                        break

                    if not self._running or self._wakeup_r in readable:
                        break

                    if stdin_fd in readable:
                        chunk = os.read(stdin_fd, 65536)
                        if not chunk:
                            if buf.strip():
                                try:
                                    stripped = buf.decode("utf-8").strip()
                                    if stripped:
                                        response = self.handle_line(stripped)
                                        if response is not None:
                                            self._write_response(stdout, response)
                                except UnicodeDecodeError as e:
                                    err_resp = {
                                        "jsonrpc": "2.0",
                                        "id": None,
                                        "error": {"code": -32700, "message": f"Parse error: invalid UTF-8: {e}"},
                                    }
                                    self._write_response(stdout, err_resp)
                            logger.info("EOF encountered on stdin. Terminating server loop.")
                            break

                        buf += chunk
                        while b"\n" in buf and self._running:
                            raw_line, buf = buf.split(b"\n", 1)
                            try:
                                stripped = raw_line.decode("utf-8").strip()
                            except UnicodeDecodeError as e:
                                logger.warning(f"UnicodeDecodeError on stdin: {e}")
                                err_resp = {
                                    "jsonrpc": "2.0",
                                    "id": None,
                                    "error": {"code": -32700, "message": f"Parse error: invalid UTF-8: {e}"},
                                }
                                self._write_response(stdout, err_resp)
                                continue
                            if not stripped:
                                continue
                            response = self.handle_line(stripped)
                            if response is not None:
                                self._write_response(stdout, response)
            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt received. Stopping.")
            except Exception as e:
                logger.error(f"Unexpected error in server loop: {e}", exc_info=True)
            finally:
                for pipe_fd in (self._wakeup_r, self._wakeup_w):
                    if pipe_fd is not None:
                        try:
                            os.close(pipe_fd)
                        except OSError:
                            pass
                self._wakeup_r = None
                self._wakeup_w = None
                self.stop()
            return

        while self._running:
            try:
                line = stdin.readline()
                if not line:
                    logger.info("EOF encountered on stdin. Terminating server loop.")
                    break
                stripped = line.strip()
                if not stripped:
                    continue

                response = self.handle_line(stripped)
                if response is not None:
                    self._write_response(stdout, response)
            except UnicodeDecodeError as e:
                logger.warning(f"UnicodeDecodeError on stdin: {e}")
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: invalid UTF-8: {e}"},
                }
                self._write_response(stdout, err_resp)
                continue
            except KeyboardInterrupt:
                logger.info("KeyboardInterrupt received. Stopping.")
                break
            except Exception as e:
                logger.error(f"Unexpected error in server loop: {e}", exc_info=True)
                break

        self.stop()

    def stop(self) -> None:
        """Signals server termination and wakes up the stdio loop (signal-safe)."""
        self._running = False
        wakeup_w = self._wakeup_w
        if wakeup_w is not None:
            try:
                os.write(wakeup_w, b"\x00")
            except OSError:
                pass


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entry point for running the MCP server."""
    parser = argparse.ArgumentParser(
        prog="ableton-live12-mcp",
        description="Ableton Live 12 Model Context Protocol (MCP) Server"
    )
    parser.add_argument("--host", default=None, help="Ableton bridge host (default: 127.0.0.1 or discovery)")
    parser.add_argument("--port", type=int, default=None, help="Ableton bridge port (default: 11246 or discovery)")
    parser.add_argument("--mock", action="store_true", help="Force offline mock mode")
    parser.add_argument("--live", action="store_true", help="Force live connection mode")
    parser.add_argument("--probe", action="store_true", help="Probe if live bridge is reachable and exit")
    parser.add_argument("--debug", action="store_true", help="Enable verbose debug logging to stderr")
    parser.add_argument("--version", action="version", version=f"{SERVER_NAME} {SERVER_VERSION}")

    args = parser.parse_args(argv)

    log_level = logging.DEBUG if args.debug or os.environ.get("DEBUG") else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="[%(asctime)s] [%(levelname)s] [ableton-live12-mcp] %(message)s",
        stream=sys.stderr
    )

    if args.probe:
        client = Live12Client(host=args.host, port=args.port)
        reachable = client.is_reachable(probe_timeout=0.5)
        if reachable:
            sys.stderr.write(f"Live bridge reachable at {client.host}:{client.port}\n")
            return 0
        else:
            sys.stderr.write(f"Live bridge not reachable at {client.host}:{client.port}\n")
            return 1

    if args.live:
        mode = "live"
    elif args.mock or os.environ.get("ABLETON_TEST_MODE", "").lower() == "mock":
        mode = "mock"
    else:
        mode = "auto"

    server = McpServer(host=args.host, port=args.port, mode=mode)

    def _sig_handler(sig, frame):
        server.stop()

    try:
        signal.signal(signal.SIGINT, _sig_handler)
        signal.signal(signal.SIGTERM, _sig_handler)
    except (ValueError, AttributeError):
        pass  # When not in main thread

    server.run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
