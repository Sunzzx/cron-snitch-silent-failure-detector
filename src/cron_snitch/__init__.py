"""
cron-snitch-silent-failure-detector
==================================
Dead man's snitch and silent failure watchdog for scheduled jobs.
"""

from .core import CronSnitchMonitor, SnitchStatus

__version__ = "0.1.0"
__all__ = ["CronSnitchMonitor", "SnitchStatus"]
