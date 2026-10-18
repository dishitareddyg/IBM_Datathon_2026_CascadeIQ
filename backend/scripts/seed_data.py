"""
scripts/seed_data.py
---------------------
Seed script: runs the three bundled CascadeIQ scenarios end-to-end and
prints a summary table. Useful for smoke-testing the full pipeline without
a running HTTP server.

Usage (from backend/ directory):
    python scripts/seed_data.py
"""

from __future__ import annotations

import asyncio
import json
import sys
import os
import time

# Ensure app is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# The summary prints a few Unicode glyphs; make the console output portable
# across Windows code pages and POSIX terminals alike.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, ValueError):
    pass

from app.core.config import get_settings
from app.core.logging import configure_logging


SCENARIOS = [
    {
        "scenario_id": "seed_light",
        "seed": 42,
        "hospitals": [
            {"hospital_id": "H1", "name": "Victoria Hospital", "lat": 12.9612, "lon": 77.5726,
             "total_beds": 200, "available_beds": 80, "icu_beds": 20},
            {"hospital_id": "H2", "name": "Manipal Hospital", "lat": 12.9399, "lon": 77.6180,
             "total_beds": 300, "available_beds": 150, "icu_beds": 30},
        ],
        "ambulances": [
            {"ambulance_id": "A1", "lat": 12.9767, "lon": 77.5713, "is_available": True},
            {"ambulance_id": "A2", "lat": 12.9279, "lon": 77.6271, "is_available": True},
        ],
        "emergency_requests": [
            {"request_id": "R1", "origin_lat": 12.9500, "origin_lon": 77.5900, "priority": "HIGH"},
            {"request_id": "R2", "origin_lat": 12.9800, "origin_lon": 77.6000, "priority": "CRITICAL"},
        ],
        "road_disruptions": [],
        "simulation_steps": 5,
        "weather_mode": "synthetic",
    },
    {
        "scenario_id": "seed_heavy",
        "seed": 123,
        "hospitals": [
            {"hospital_id": "H1", "name": "Apollo Hospitals", "lat": 12.9263, "lon": 77.5985,
             "total_beds": 400, "available_beds": 60, "icu_beds": 40},
            {"hospital_id": "H2", "name": "NIMHANS", "lat": 12.9387, "lon": 77.5966,
             "total_beds": 200, "available_beds": 30, "icu_beds": 10},
            {"hospital_id": "H3", "name": "St Johns", "lat": 12.9256, "lon": 77.6242,
             "total_beds": 350, "available_beds": 100, "icu_beds": 25},
        ],
        "ambulances": [
            {"ambulance_id": "A1", "lat": 12.9784, "lon": 77.6408, "is_available": True},
            {"ambulance_id": "A2", "lat": 13.0351, "lon": 77.5967, "is_available": True},
            {"ambulance_id": "A3", "lat": 12.8458, "lon": 77.6643, "is_available": True},
        ],
        "emergency_requests": [
            {"request_id": f"R{i}", "origin_lat": 12.88 + i * 0.02, "origin_lon": 77.55 + i * 0.03, "priority": p}
            for i, p in enumerate(["CRITICAL", "HIGH", "HIGH", "MEDIUM", "MEDIUM", "LOW"])
        ],
        "road_disruptions": [
            {"edge_id": "silk_board_koramangala_0", "status": "CLOSED", "severity": 0.9,
             "confidence": 0.8, "cause": "Flooding", "estimated_by": "synthetic"},
            {"edge_id": "majestic_hebbal_0", "status": "DEGRADED", "severity": 0.5,
             "confidence": 0.7, "cause": "Waterlogging", "estimated_by": "synthetic"},
        ],
        "simulation_steps": 10,
        "weather_mode": "synthetic",
    },
    {
        "scenario_id": "seed_extreme",
        "seed": 999,
        "hospitals": [
            {"hospital_id": f"H{i}", "name": f"Hospital {i}", "lat": 12.85 + i*0.02, "lon": 77.55 + i*0.03,
             "total_beds": 100, "available_beds": max(5, 20 - i*3), "icu_beds": 5}
            for i in range(1, 6)
        ],
        "ambulances": [
            {"ambulance_id": f"A{i}", "lat": 12.90 + i*0.015, "lon": 77.58 + i*0.02, "is_available": True}
            for i in range(1, 6)
        ],
        "emergency_requests": [
            {"request_id": f"R{i}", "origin_lat": 12.88 + (i % 5)*0.025, "origin_lon": 77.55 + (i % 4)*0.04,
             "priority": ["CRITICAL", "HIGH", "HIGH", "MEDIUM", "LOW"][i % 5]}
            for i in range(10)
        ],
        "road_disruptions": [
            {"edge_id": f"edge_closed_{i}", "status": "CLOSED", "severity": 1.0,
             "confidence": 0.95, "cause": "Major flooding", "estimated_by": "synthetic"}
            for i in range(5)
        ],
        "simulation_steps": 15,
        "weather_mode": "synthetic",
    },
]


def _print_table(rows: list[dict]) -> None:
    headers = ["Scenario", "Steps", "Assignments", "Unreachable (final)", "Isolated (final)", "Time (s)"]
    col_widths = [max(len(h), max(len(str(r.get(h, ""))) for r in rows)) for h in headers]
    fmt = "  ".join(f"{{:<{w}}}" for w in col_widths)
    sep = "  ".join("-" * w for w in col_widths)
    print(fmt.format(*headers))
    print(sep)
    for row in rows:
        print(fmt.format(*[str(row.get(h, "")) for h in headers]))


async def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)

    # Initialize the cached road graph (bundled synthetic sample, no network).
    from app.services.graph_service import graph_service

    graph_service.load_bundled()

    from app.schemas.scenario import ScenarioInput
    from app.services.simulation_service import simulation_service

    results = []
    for sc_dict in SCENARIOS:
        scenario = ScenarioInput(**sc_dict)

        t0 = time.perf_counter()
        result, _state, _assignments = simulation_service.run(
            scenario, policy="cascadeiq", persist=False
        )
        elapsed = time.perf_counter() - t0
        sim_id = result.simulation_id

        final_step = result.steps[-1] if result.steps else None
        rows_entry = {
            "Scenario": sc_dict["scenario_id"],
            "Steps": len(result.steps),
            "Assignments": len(result.final_assignments),
            "Unreachable (final)": len(final_step.unreachable_requests) if final_step else "N/A",
            "Isolated (final)": len(final_step.isolated_facilities) if final_step else "N/A",
            "Time (s)": f"{elapsed:.3f}",
        }
        results.append(rows_entry)
        print(f"\n✓ {sc_dict['scenario_id']} — simulation_id: {sim_id}")
        if final_step:
            print(f"  Hospital loads: {final_step.hospital_loads}")
            print(f"  Cascade events (final step): {len(final_step.cascade_events)}")

    print("\n" + "=" * 70)
    print("SEED DATA SUMMARY")
    print("=" * 70)
    _print_table(results)
    print("\nAll scenarios completed. No real emergency data was used.")
    print("DISCLAIMER: All values are simulated for research/educational use only.")


if __name__ == "__main__":
    asyncio.run(main())
