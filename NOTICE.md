# NOTICE

## Ableton Live 12 MCP (`ableton-live12-mcp`)

*Repository:* [https://github.com/juancruzmunozalbelo/ableton-live12-mcp](https://github.com/juancruzmunozalbelo/ableton-live12-mcp)  
*Documentation:* [https://juancruzmunozalbelo.github.io/ableton-live12-mcp/](https://juancruzmunozalbelo.github.io/ableton-live12-mcp/)

Copyright (c) 2026 Juan Cruz Muñoz Albelo and Ableton Live 12 MCP Contributors.

This product is dual-licensed under the MIT License and the Apache License, Version 2.0.
See `LICENSE-MIT` and `LICENSE-APACHE` for details.

---

### Clean-Room Engineering & Interoperability Research Provenance

Ableton Live 12 MCP is an independent, clean-room software bridge and Model Context Protocol (MCP) server engineered specifically to enable autonomous AI agent interaction with Ableton Live 12.4.6 Suite on macOS.

1. **Interoperability Exceptions & Legal Basis**:
   The technical analysis and API surface cataloging (`docs/lom_surface_12_4_6.json`, `docs/LOM_REFERENCE.md`, `docs/ABLETON_12_MANUAL_COVERAGE.md`) were conducted exclusively for the purpose of achieving interoperability between an independently created computer program and the host software, in strict accordance with:
   - **United States Code Title 17, Section 1201(f)** (Reverse Engineering Exception for Interoperability).
   - **European Union Directive 2009/24/EC, Article 6** (Decompilation for Interoperability).

2. **Independent Implementation**:
   - The MCP server (`src/ableton_live12_mcp/`) is authored in 100% pure Python standard library code with zero third-party pip runtime dependencies.
   - The Remote Script Control Surface bridge (`src/live12_bridge/`) uses documented and standard MIDI Remote Script hooks (`create_instance`, `Live.Base.Timer`).
   - This repository contains **zero proprietary binaries, decompiled C++ source files, SDKs, or copyrighted audio samples from Ableton AG or Cycling '74**.

---

### Trademark Disclaimer & Nominative Fair Use

- **"Ableton"**, **"Ableton Live"**, **"Live Suite"**, **"Push"**, **"Meld"**, **"Roar"**, **"Drift"**, **"Simpler"**, **"Wavetable"**, and **"Max for Live"** are registered trademarks or service marks of **Ableton AG** in Germany, the United States, and other jurisdictions.
- **"Max"**, **"RNBO"**, and **"Cycling '74"** are registered trademarks of **Cycling '74 / Cycling '74 LLC**.
- **Ableton Live 12 MCP is an independent open-source project and is NOT affiliated with, sponsored by, endorsed by, or associated in any way with Ableton AG or Cycling '74.**
- Any use of the terms "Ableton", "Ableton Live", or related product designations within this repository, documentation, or code comments is strictly for **nominative, comparative, interoperability, and architectural educational purposes** under applicable fair use principles to accurately describe workflow compatibility and engineering methodology.
