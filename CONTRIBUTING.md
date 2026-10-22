# Contributing to Ableton Live 12 MCP

Thank you for your interest in contributing to **Ableton Live 12 MCP** (`ableton-live12-mcp`), the production-grade Model Context Protocol server and Remote Script bridge for Ableton Live 12.4.6 Suite.

*Repository:* [https://github.com/juancruzmunozalbelo/ableton-live12-mcp](https://github.com/juancruzmunozalbelo/ableton-live12-mcp)  
*Documentation:* [https://juancruzmunozalbelo.github.io/ableton-live12-mcp/](https://juancruzmunozalbelo.github.io/ableton-live12-mcp/)

---

## 1. Code of Conduct

All contributors and participants are expected to adhere to our [Code of Conduct](CODE_OF_CONDUCT.md) (Contributor Covenant v2.1).

---

## 2. Core Architectural Invariants

### A. Pure Python Standard Library (MCP Server)
The MCP server in `src/ableton_live12_mcp/` must have **zero external pip runtime dependencies**. It must run cleanly on stock Python 3.11+ using standard library modules (`json`, `socket`, `argparse`, `sys`, `typing`, `logging`, `pathlib`).

### B. Main-Thread Execution Invariant (Remote Script Bridge)
Ableton's Live Object Model (LOM) C++ Boost.Python bindings are strictly **not thread-safe**.
- All mutations (creating tracks, editing clips, setting parameters, modifying warp markers) must execute on Ableton's main thread.
- Thread dispatching must use the 5ms `Live.Base.Timer` queue in `src/live12_bridge/bridge.py`.
- Never execute LOM calls directly from background socket worker threads.

### C. Pointer Validation (`liveobj_valid`)
Always check `liveobj_valid(obj)` before accessing attributes or invoking methods on LOM objects to guard against deleted references and prevent C++ access violations.

### D. Clean Stderr Logging
Stdout is strictly reserved for newline-delimited JSON-RPC 2.0 messages. All logging, telemetry, and diagnostics must write strictly to `sys.stderr`.

---

## 3. Development & Verification Workflow

### Running the Test Suite (Offline Mock Mode)
```bash
PYTHONPATH=src pytest tests/ -v
```

### Running the Test Suite (Live Ableton Instance)
```bash
./scripts/run_live_tests.sh --live -v
```

### Checking Python Bytecode Compilation
```bash
python3 -m py_compile src/live12_bridge/*.py src/ableton_live12_mcp/*.py src/ableton_live12_mcp/tools/*.py
```

---

## 4. Submitting Pull Requests

1. Fork and create a branch off `main` (e.g., `feat/groove-pool-mcp`, `fix/take-lane-comp`).
2. Follow conventional commit messages (`feat: ...`, `fix: ...`, `docs: ...`).
3. Ensure all tests pass with code coverage maintained.
4. Verify bytecode compilation across Python 3.11, 3.12, and 3.13.
