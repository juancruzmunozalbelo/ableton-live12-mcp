"""
Live 12 Bridge - Client Connector
=================================
High-performance TCP client for communicating with the in-process
Ableton Live 12 Remote Script bridge via Newline-Delimited JSON-RPC 2.0.
Supports auto-discovery, connection retry, timeouts, and ToolResult formatting.
"""

from __future__ import annotations

import json
import os
import socket
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 11246
DEFAULT_DISCOVERY_PATH = "/tmp/ableton_live12_bridge.json"


class Live12ClientError(Exception):
    """Base exception for all Live 12 client operations."""
    pass


class Live12ConnectionError(Live12ClientError):
    """Raised when connection to the Live 12 Remote Script fails."""
    pass


class Live12TimeoutError(Live12ClientError):
    """Raised when an RPC request or connection attempt times out."""
    pass


class Live12RpcError(Live12ClientError):
    """Raised when Live 12 bridge responds with a JSON-RPC error."""

    def __init__(self, code: int, message: str, data: Any = None):
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.data = data


@dataclass
class ToolResult:
    """Standardized result envelope for MCP tool calls and test assertions."""
    is_error: bool
    content: List[Dict[str, Any]]
    raw: Dict[str, Any] = field(default_factory=dict)

    @property
    def data(self) -> Any:
        """Parses JSON payload from the first text content item if available."""
        if not self.content:
            return None
        text = self.content[0].get("text", "")
        if not text:
            return None
        try:
            return json.loads(text)
        except Exception:
            return text

    def get(self, key: str, default: Any = None) -> Any:
        d = self.data
        if isinstance(d, dict):
            return d.get(key, default)
        return default

    def __getitem__(self, key: str) -> Any:
        d = self.data
        if isinstance(d, dict):
            return d[key]
        raise KeyError(f"Data is not a dict: {type(d)}")


class Live12Client:
    """
    Robust TCP client that connects to the Ableton Live 12 Remote Script bridge.
    Reads active discovery metadata from /tmp/ableton_live12_bridge.json when available.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        timeout: float = 10.0,
        discovery_path: Optional[str] = None,
    ):
        self.timeout = timeout
        self.discovery_path = discovery_path or DEFAULT_DISCOVERY_PATH
        self._req_id = 0

        # Resolve host and port with priority: explicit arg > env var > discovery file > defaults
        resolved_host = host or os.environ.get("ABLETON_BRIDGE_HOST")
        resolved_port = port or (int(os.environ["ABLETON_BRIDGE_PORT"]) if "ABLETON_BRIDGE_PORT" in os.environ else None)

        if (resolved_host is None or resolved_port is None) and self.discovery_path and os.path.exists(self.discovery_path):
            try:
                with open(self.discovery_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    if resolved_port is None and "port" in meta:
                        resolved_port = int(meta["port"])
                    if resolved_host is None and "host" in meta:
                        resolved_host = str(meta["host"])
            except Exception:
                pass

        self.host = resolved_host or DEFAULT_HOST
        self.port = resolved_port or DEFAULT_PORT

    def is_reachable(self, probe_timeout: float = 0.3) -> bool:
        """Checks whether the Live 12 TCP bridge is reachable."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(probe_timeout)
            s.connect((self.host, self.port))
            s.close()
            return True
        except Exception:
            return False

    def call(
        self,
        method: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None,
    ) -> Any:
        """
        Executes a JSON-RPC 2.0 call against the bridge, raising Live12RpcError on failure.
        """
        self._req_id += 1
        req_id = self._req_id
        req_payload = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }
        data = (json.dumps(req_payload) + "\n").encode("utf-8")
        req_timeout = timeout or self.timeout

        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(req_timeout)
            s.connect((self.host, self.port))
            s.sendall(data)

            chunks = []
            while True:
                chunk = s.recv(8192)
                if not chunk:
                    break
                chunks.append(chunk)
                if b"\n" in chunk:
                    break
            s.close()

            raw_bytes = b"".join(chunks).strip()
            if not raw_bytes:
                raise Live12ConnectionError("Empty response received from Live 12 bridge")

            resp = json.loads(raw_bytes.decode("utf-8"))

            if "error" in resp:
                err = resp["error"]
                code = err.get("code", -32000)
                msg = err.get("message", "Unknown RPC error")
                data = err.get("data")
                raise Live12RpcError(code, msg, data)

            return resp.get("result")

        except socket.timeout as e:
            raise Live12TimeoutError(f"Request '{method}' timed out after {req_timeout}s") from e
        except ConnectionRefusedError as e:
            raise Live12ConnectionError(
                f"Connection refused to Live 12 bridge at {self.host}:{self.port}. Is Ableton Live running?"
            ) from e
        except json.JSONDecodeError as e:
            raise Live12ClientError(f"Failed to decode bridge JSON response: {e}") from e
        except (Live12ClientError, Live12RpcError):
            raise
        except Exception as e:
            raise Live12ClientError(f"Error during RPC call to '{method}': {e}") from e

    def call_tool(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        """
        MCP-compatible convenience method that wraps results into ToolResult envelope.
        Matches the interface expected by tests and MCP tools.
        """
        args = arguments or {}
        try:
            res = self.call(tool_name, args)
            return ToolResult(
                is_error=False,
                content=[{"type": "text", "text": json.dumps(res)}],
                raw=res if isinstance(res, dict) else {"result": res},
            )
        except Live12RpcError as e:
            err_dict = {
                "code": e.code,
                "message": e.message,
                "data": e.data,
            }
            return ToolResult(
                is_error=True,
                content=[{"type": "text", "text": json.dumps(err_dict)}],
                raw=err_dict,
            )
        except Exception as e:
            err_dict = {
                "code": -32000,
                "message": str(e),
                "type": type(e).__name__,
            }
            return ToolResult(
                is_error=True,
                content=[{"type": "text", "text": json.dumps(err_dict)}],
                raw=err_dict,
            )

    # -------------------------------------------------------------------------
    # Convenience LOM Helpers
    # -------------------------------------------------------------------------

    def lom_inspect(self, target_path: str) -> Dict[str, Any]:
        """Introspects properties, methods, and types of an object at target_path."""
        return self.call("live12_lom_inspect", {"target_path": target_path})

    def lom_get(self, target_path: str, property_name: str) -> Dict[str, Any]:
        """Reads a property value on an object at target_path."""
        return self.call("live12_lom_get", {"target_path": target_path, "property_name": property_name})

    def lom_set(self, target_path: str, property_name: str, value: Any) -> Dict[str, Any]:
        """Mutates a property value on an object at target_path."""
        return self.call(
            "live12_lom_set",
            {"target_path": target_path, "property_name": property_name, "value": value},
        )

    def lom_call(
        self,
        target_path: str,
        method_name: str,
        args: Optional[list] = None,
        kwargs: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """Invokes a method on an object at target_path."""
        return self.call(
            "live12_lom_call",
            {
                "target_path": target_path,
                "method_name": method_name,
                "args": args or [],
                "kwargs": kwargs or {},
            },
        )

    # -------------------------------------------------------------------------
    # Context Manager
    # -------------------------------------------------------------------------

    def __enter__(self) -> Live12Client:
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass


# Compatibility alias for harness
LiveTcpClient = Live12Client
