"""
Masterclasses Automated Orchestrator
====================================
Sequentially executes the reconstruction of all 6 masterclasses in Ableton Live 12 Suite:
1. HOLO Masterclass - Modulo 1: Concepto y Referencia
2. HOLO Masterclass - Modulo 2: Groove y Baterias
3. HOLO Masterclass - Modulo 3: Diseno Sonoro
4. HOLO Masterclass - Modulo 4: Bases Armonicas y Melodicas
5. HOLO Masterclass - Modulo 5: Arreglo Completo
6. Peak Time Techno - ClaSE PEAK jULIO 25

Performs in-process clean session reset between modules, saves verified .als Live Sets,
and renders non-silent PCM .wav bounces (duration >= 10s, RMS > -40 dBFS).
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
from typing import Any, Dict, List

from build_holo_m1 import HoloModule1Builder
from build_holo_m2 import HoloModule2Builder
from build_holo_m3 import HoloModule3Builder
from build_holo_m4 import HoloModule4Builder
from build_holo_m5 import HoloModule5Builder
from build_peak_class import PeakClassBuilder

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("masterclass.orchestrator")


def run_all() -> Dict[str, Any]:
    tasks = [
        ("HOLO Module 1 (Concepto y Referencia)", HoloModule1Builder, 64.0, 4),
        ("HOLO Module 2 (Groove y Baterias)", HoloModule2Builder, 64.0, 8),
        ("HOLO Module 3 (Diseno Sonoro)", HoloModule3Builder, 64.0, 7),
        ("HOLO Module 4 (Bases Armonicas y Melodicas)", HoloModule4Builder, 64.0, 7),
        ("HOLO Module 5 (Arreglo Completo)", HoloModule5Builder, 64.0, 25),
        ("Peak Time Class (ClaSE PEAK jULIO 25)", PeakClassBuilder, 64.0, 27),
    ]

    results: List[Dict[str, Any]] = []
    start_all = time.time()

    for idx, (name, builder_cls, dur_beats, min_tracks) in enumerate(tasks, 1):
        logger.info("\n" + "=" * 80)
        logger.info(">>> [%d/6] EXECUTING: %s", idx, name)
        logger.info("=" * 80)

        t0 = time.time()
        try:
            builder = builder_cls()
            res = builder.run(render_duration_beats=dur_beats, expected_min_tracks=min_tracks)
            elapsed = time.time() - t0
            res["elapsed_sec"] = elapsed
            res["module_name"] = name
            results.append(res)

            if not res.get("valid"):
                logger.error("FAILED verification for %s: %s", name, res)
                return {"success": False, "failed_module": name, "results": results}
            logger.info("SUCCESS [%d/6]: %s in %.2fs", idx, name, elapsed)
        except Exception as e:
            logger.exception("CRITICAL ERROR during %s: %s", name, e)
            return {"success": False, "failed_module": name, "error": str(e), "results": results}

        # Cool-down delay between builds for Live engine stabilization
        time.sleep(1.0)

    total_time = time.time() - start_all
    logger.info("\n" + "=" * 80)
    logger.info(">>> ALL 6 MASTERCLASSES RECONSTRUCTED & VERIFIED IN %.2fs", total_time)
    logger.info("=" * 80)

    summary = {
        "success": True,
        "total_time_seconds": total_time,
        "modules_built": len(results),
        "results": results,
    }
    return summary


if __name__ == "__main__":
    report = run_all()
    print("\nFINAL EXECUTION REPORT:\n" + json.dumps(report, indent=2))
    if not report.get("success"):
        sys.exit(1)
