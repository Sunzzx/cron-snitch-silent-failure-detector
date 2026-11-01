"""
cron_snitch.cli
===============
CLI tool for cron-snitch-silent-failure-detector.
"""

from __future__ import annotations

import argparse
import sys
from .core import CronSnitchMonitor, SnitchStatus


def main():
    parser = argparse.ArgumentParser(
        prog="cron-snitch",
        description="Silent Cron Failure & Dead Man's Snitch Watchdog.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Subcommands")

    # ping
    ping_p = subparsers.add_parser("ping", help="Record a heartbeat ping for a job")
    ping_p.add_argument("name", help="Job name / identifier")
    ping_p.add_argument("--detail", "-d", default="", help="Optional execution detail or message")

    # check
    check_p = subparsers.add_parser("check", help="Check if a job missed its heartbeat")
    check_p.add_argument("name", help="Job name / identifier")
    check_p.add_argument("--interval", "-i", type=float, default=3600, help="Expected interval in seconds")
    check_p.add_argument("--grace", "-g", type=float, default=300, help="Grace period in seconds")

    # wrap
    wrap_p = subparsers.add_parser("wrap", help="Wrap and execute command with auto-ping")
    wrap_p.add_argument("--name", "-n", required=True, help="Job name")
    wrap_p.add_argument("cmd", nargs="+", help="Command to run")

    # status
    subparsers.add_parser("status", help="List all tracked snitches")

    args = parser.parse_args()
    monitor = CronSnitchMonitor()

    if not args.subcommand or args.subcommand == "status":
        data = monitor._load_ledger()
        print(f"⚡ CRONSNITCH TELEMETRY WATCHDOG ({len(data)} tracked job(s)):")
        if not data:
            print("  No active heartbeat entries found. Run 'cron-snitch ping <name>' to record one.")
        for k, v in data.items():
            print(f"  • {k}: status={v.get('status')} | detail={v.get('detail', '')}")
        sys.exit(0)

    elif args.subcommand == "ping":
        monitor.record_heartbeat(args.name, SnitchStatus.HEALTHY, detail=args.detail)
        print(f"✓ Recorded heartbeat ping for: {args.name}")

    elif args.subcommand == "check":
        res = monitor.check_health(args.name, args.interval, args.grace)
        print(f"[{res.status.value.upper()}] {res.job_name}: {res.detail}")
        sys.exit(0 if res.status == SnitchStatus.HEALTHY else 1)

    elif args.subcommand == "wrap":
        cmd_str = " ".join(args.cmd)
        code = monitor.run_wrapped(args.name, cmd_str)
        sys.exit(code)


if __name__ == "__main__":
    main()
