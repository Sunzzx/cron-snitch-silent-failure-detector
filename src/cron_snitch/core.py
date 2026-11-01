"""
cron_snitch.core
================
Core telemetry watchdog logic and schedule calculation.
"""

from __future__ import annotations

import enum
import json
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


class SnitchStatus(enum.Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    MISSED = "missed"
    ERROR = "error"


@dataclass
class SnitchCheckResult:
    job_name: str
    status: SnitchStatus
    last_ping_seconds_ago: float
    expected_interval_seconds: float
    grace_period_seconds: float
    detail: str


class CronSnitchMonitor:
    """Evaluates cron heartbeats and executes wrapped commands with automatic telemetry."""

    def __init__(self, ledger_path: Optional[Path] = None):
        self.ledger_path = ledger_path or (Path.home() / ".hermes" / "state" / "cron_snitch_ledger.json")

    def _load_ledger(self) -> Dict[str, Any]:
        if self.ledger_path.exists():
            try:
                return json.loads(self.ledger_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save_ledger(self, data: Dict[str, Any]):
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def record_heartbeat(self, job_name: str, status: SnitchStatus = SnitchStatus.HEALTHY, detail: str = ""):
        data = self._load_ledger()
        data[job_name] = {
            "last_ping": time.time(),
            "status": status.value,
            "detail": detail,
        }
        self._save_ledger(data)

    def check_health(self, job_name: str, interval_seconds: float, grace_seconds: float = 60.0) -> SnitchCheckResult:
        data = self._load_ledger()
        if job_name not in data:
            return SnitchCheckResult(
                job_name=job_name,
                status=SnitchStatus.WARNING,
                last_ping_seconds_ago=-1,
                expected_interval_seconds=interval_seconds,
                grace_period_seconds=grace_seconds,
                detail="No heartbeats recorded yet.",
            )

        info = data[job_name]
        elapsed = time.time() - info["last_ping"]
        max_allowed = interval_seconds + grace_seconds

        if elapsed > max_allowed:
            status = SnitchStatus.MISSED
            detail = f"Silent failure detected! Elapsed {elapsed:.1f}s > threshold {max_allowed:.1f}s"
        else:
            status = SnitchStatus.HEALTHY
            detail = f"Healthy. Last ping {elapsed:.1f}s ago."

        return SnitchCheckResult(
            job_name=job_name,
            status=status,
            last_ping_seconds_ago=elapsed,
            expected_interval_seconds=interval_seconds,
            grace_period_seconds=grace_seconds,
            detail=detail,
        )

    def run_wrapped(self, job_name: str, cmd: List[str] | str, timeout: int = 300) -> int:
        """Run command and automatically ping on success, or record failure on error."""
        t0 = time.time()
        try:
            res = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True, timeout=timeout)
            duration = time.time() - t0
            if res.returncode == 0:
                self.record_heartbeat(job_name, SnitchStatus.HEALTHY, detail=f"Completed in {duration:.2f}s")
            else:
                self.record_heartbeat(job_name, SnitchStatus.ERROR, detail=f"Exited with code {res.returncode}: {res.stderr[:200]}")
            return res.returncode
        except Exception as e:
            self.record_heartbeat(job_name, SnitchStatus.ERROR, detail=f"Exception: {e}")
            return 1
