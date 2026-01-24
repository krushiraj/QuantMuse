"""Background scheduler for automated paper trading tasks."""
import logging
from datetime import datetime, time
from typing import Optional, Callable, List
import pytz

try:
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    from apscheduler.triggers.interval import IntervalTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    BackgroundScheduler = None

logger = logging.getLogger(__name__)


class TradingScheduler:
    """Scheduler for automated trading tasks."""

    def __init__(self, timezone: str = "Asia/Kolkata"):
        if not APSCHEDULER_AVAILABLE:
            raise ImportError("apscheduler required: pip install apscheduler")

        self.timezone = pytz.timezone(timezone)
        self.scheduler = BackgroundScheduler(timezone=self.timezone)
        self._jobs = {}
        self._running = False

    def start(self) -> None:
        """Start the scheduler."""
        if not self._running:
            self.scheduler.start()
            self._running = True
            logger.info("Trading scheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        if self._running:
            self.scheduler.shutdown()
            self._running = False
            logger.info("Trading scheduler stopped")

    def is_running(self) -> bool:
        """Check if scheduler is running."""
        return self._running

    def add_interval_job(
        self,
        job_id: str,
        func: Callable,
        minutes: int = 15,
        **kwargs
    ) -> str:
        """Add a job that runs at fixed intervals."""
        if job_id in self._jobs:
            self.remove_job(job_id)

        job = self.scheduler.add_job(
            func,
            trigger=IntervalTrigger(minutes=minutes),
            id=job_id,
            **kwargs
        )
        self._jobs[job_id] = job
        logger.info(f"Added interval job '{job_id}' every {minutes} minutes")
        return job_id

    def add_cron_job(
        self,
        job_id: str,
        func: Callable,
        hour: int,
        minute: int = 0,
        day_of_week: str = "mon-fri",
        **kwargs
    ) -> str:
        """Add a cron-style scheduled job."""
        if job_id in self._jobs:
            self.remove_job(job_id)

        job = self.scheduler.add_job(
            func,
            trigger=CronTrigger(
                hour=hour,
                minute=minute,
                day_of_week=day_of_week,
                timezone=self.timezone
            ),
            id=job_id,
            **kwargs
        )
        self._jobs[job_id] = job
        logger.info(f"Added cron job '{job_id}' at {hour:02d}:{minute:02d} ({day_of_week})")
        return job_id

    def add_market_hours_job(
        self,
        job_id: str,
        func: Callable,
        minutes: int = 15,
        market_open: time = time(9, 15),
        market_close: time = time(15, 30),
        **kwargs
    ) -> str:
        """Add a job that only runs during market hours."""
        def wrapped_func():
            now = datetime.now(self.timezone).time()
            if market_open <= now <= market_close:
                func()
            else:
                logger.debug(f"Skipping '{job_id}' - outside market hours")

        return self.add_interval_job(job_id, wrapped_func, minutes, **kwargs)

    def remove_job(self, job_id: str) -> bool:
        """Remove a scheduled job."""
        if job_id in self._jobs:
            try:
                self.scheduler.remove_job(job_id)
                del self._jobs[job_id]
                logger.info(f"Removed job '{job_id}'")
                return True
            except Exception as e:
                logger.error(f"Error removing job '{job_id}': {e}")
        return False

    def get_jobs(self) -> List[dict]:
        """Get list of scheduled jobs."""
        return [
            {
                "id": job.id,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                "trigger": str(job.trigger),
            }
            for job in self.scheduler.get_jobs()
        ]

    def run_job_now(self, job_id: str) -> bool:
        """Trigger a job to run immediately."""
        if job_id in self._jobs:
            job = self._jobs[job_id]
            job.func()
            return True
        return False


class PaperTradingJobs:
    """Pre-configured jobs for paper trading."""

    def __init__(
        self,
        scheduler: TradingScheduler,
        engine=None,
        strategy_runner=None,
        performance_tracker=None,
        db_session_factory=None,
    ):
        self.scheduler = scheduler
        self.engine = engine
        self.strategy_runner = strategy_runner
        self.performance_tracker = performance_tracker
        self.db_session_factory = db_session_factory
        self._session_id: Optional[int] = None

    def set_session(self, session_id: int) -> None:
        """Set the active trading session."""
        self._session_id = session_id

    def setup_nse_jobs(self) -> None:
        """Set up jobs for NSE market."""
        # Check exits every 15 minutes during market hours
        self.scheduler.add_market_hours_job(
            "nse_exit_check",
            self._check_exits,
            minutes=15,
            market_open=time(9, 15),
            market_close=time(15, 30),
        )

        # Generate signals every 30 minutes
        self.scheduler.add_market_hours_job(
            "nse_signal_generation",
            self._generate_signals,
            minutes=30,
            market_open=time(9, 15),
            market_close=time(15, 30),
        )

        # Daily snapshot at market close
        self.scheduler.add_cron_job(
            "nse_daily_snapshot",
            self._record_daily_snapshot,
            hour=15,
            minute=35,
            day_of_week="mon-fri",
        )

        logger.info("NSE jobs configured")

    def setup_crypto_jobs(self) -> None:
        """Set up jobs for crypto market (24/7)."""
        # Check exits every 5 minutes
        self.scheduler.add_interval_job(
            "crypto_exit_check",
            self._check_exits,
            minutes=5,
        )

        # Generate signals every 15 minutes
        self.scheduler.add_interval_job(
            "crypto_signal_generation",
            self._generate_signals,
            minutes=15,
        )

        # Hourly snapshot
        self.scheduler.add_interval_job(
            "crypto_hourly_snapshot",
            self._record_daily_snapshot,
            minutes=60,
        )

        logger.info("Crypto jobs configured")

    def _check_exits(self) -> None:
        """Check all positions for exit conditions."""
        if not self._session_id or not self.engine:
            return

        try:
            exits = self.engine.check_exits(self._session_id)
            if exits:
                logger.info(f"Processed {len(exits)} exits")
        except Exception as e:
            logger.error(f"Exit check error: {e}")

    def _generate_signals(self) -> None:
        """Generate trading signals."""
        if not self._session_id or not self.strategy_runner:
            return

        try:
            # This would be called with actual data providers
            logger.info("Signal generation triggered")
        except Exception as e:
            logger.error(f"Signal generation error: {e}")

    def _record_daily_snapshot(self) -> None:
        """Record daily performance snapshot."""
        if not self._session_id or not self.performance_tracker:
            return

        try:
            self.performance_tracker.record_daily_snapshot(self._session_id)
            logger.info("Daily snapshot recorded")
        except Exception as e:
            logger.error(f"Snapshot error: {e}")
