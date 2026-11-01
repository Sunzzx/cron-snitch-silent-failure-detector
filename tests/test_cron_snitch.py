"""
Unit tests for cron-snitch-silent-failure-detector
"""

import tempfile
import time
from pathlib import Path
import pytest

from cron_snitch.core import CronSnitchMonitor, SnitchStatus


def test_record_and_check_healthy():
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = Path(tmpdir) / "ledger.json"
        monitor = CronSnitchMonitor(ledger_path=ledger)

        monitor.record_heartbeat("backup-job", SnitchStatus.HEALTHY, detail="Dumped 20MB")
        res = monitor.check_health("backup-job", interval_seconds=10.0, grace_seconds=2.0)
        assert res.status == SnitchStatus.HEALTHY
        assert "Healthy" in res.detail


def test_missed_heartbeat_detection():
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = Path(tmpdir) / "ledger.json"
        monitor = CronSnitchMonitor(ledger_path=ledger)

        # Record heartbeat artificially back in time
        data = {
            "stuck-job": {
                "last_ping": time.time() - 200,
                "status": "healthy",
                "detail": "old run"
            }
        }
        monitor._save_ledger(data)

        # Check with 60s threshold
        res = monitor.check_health("stuck-job", interval_seconds=50.0, grace_seconds=10.0)
        assert res.status == SnitchStatus.MISSED
        assert "Silent failure detected" in res.detail


def test_wrap_execution():
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger = Path(tmpdir) / "ledger.json"
        monitor = CronSnitchMonitor(ledger_path=ledger)

        code = monitor.run_wrapped("test-echo", "echo 'hello world'")
        assert code == 0

        res = monitor.check_health("test-echo", interval_seconds=60.0)
        assert res.status == SnitchStatus.HEALTHY
