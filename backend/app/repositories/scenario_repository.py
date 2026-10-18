"""
In-memory repositories for scenarios and simulation runs.

Phase 3 can replace this class with a PostgreSQL/PostGIS implementation
without changing service call sites.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Optional

from app.schemas.simulation import SimulationResult

_MAX_ENTRIES = 200


class ScenarioRepository:
    def __init__(self) -> None:
        self._store: OrderedDict[str, SimulationResult] = OrderedDict()
        self._runtime: dict[str, dict[str, Any]] = {}

    def save_sync(self, result: SimulationResult) -> None:
        if len(self._store) >= _MAX_ENTRIES:
            oldest, _ = self._store.popitem(last=False)
            self._runtime.pop(oldest, None)
        self._store[result.simulation_id] = result

    async def save(self, result: SimulationResult) -> None:
        self.save_sync(result)

    def save_runtime(self, simulation_id: str, state: Any, assignments: Any, scenario: Any) -> None:
        self._runtime[simulation_id] = {
            "state": state,
            "assignments": assignments,
            "scenario": scenario,
        }

    def get_runtime(self, simulation_id: str) -> Optional[dict[str, Any]]:
        return self._runtime.get(simulation_id)

    async def get(self, simulation_id: str) -> Optional[SimulationResult]:
        return self._store.get(simulation_id)

    def get_sync(self, simulation_id: str) -> Optional[SimulationResult]:
        return self._store.get(simulation_id)

    async def list_all(self) -> list[SimulationResult]:
        return list(self._store.values())

    def list_ids(self) -> list[str]:
        return list(self._store.keys())

    async def delete(self, simulation_id: str) -> bool:
        self._runtime.pop(simulation_id, None)
        if simulation_id in self._store:
            del self._store[simulation_id]
            return True
        return False

    def __len__(self) -> int:
        return len(self._store)


scenario_repo = ScenarioRepository()
