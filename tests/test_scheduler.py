"""Tests for trading scheduler."""
import pytest
from unittest.mock import MagicMock, patch
from datetime import time


def test_scheduler_import():
    """Test scheduler can be imported."""
    from paper_trading.scheduler import TradingScheduler, APSCHEDULER_AVAILABLE
    assert TradingScheduler is not None


@pytest.fixture
def scheduler():
    """Create test scheduler."""
    from paper_trading.scheduler import TradingScheduler, APSCHEDULER_AVAILABLE
    if not APSCHEDULER_AVAILABLE:
        pytest.skip("APScheduler not installed")
    return TradingScheduler()


def test_start_stop(scheduler):
    """Test scheduler start and stop."""
    scheduler.start()
    assert scheduler.is_running()

    scheduler.stop()
    assert not scheduler.is_running()


def test_add_interval_job(scheduler):
    """Test adding interval job."""
    func = MagicMock()
    scheduler.start()

    job_id = scheduler.add_interval_job("test_job", func, minutes=5)
    assert job_id == "test_job"
    assert "test_job" in scheduler._jobs

    scheduler.stop()


def test_add_cron_job(scheduler):
    """Test adding cron job."""
    func = MagicMock()
    scheduler.start()

    job_id = scheduler.add_cron_job("daily_job", func, hour=9, minute=15)
    assert job_id == "daily_job"

    scheduler.stop()


def test_remove_job(scheduler):
    """Test removing a job."""
    func = MagicMock()
    scheduler.start()

    scheduler.add_interval_job("remove_test", func, minutes=5)
    assert scheduler.remove_job("remove_test")
    assert "remove_test" not in scheduler._jobs

    scheduler.stop()


def test_get_jobs(scheduler):
    """Test getting job list."""
    func = MagicMock()
    scheduler.start()

    scheduler.add_interval_job("job1", func, minutes=5)
    scheduler.add_interval_job("job2", func, minutes=10)

    jobs = scheduler.get_jobs()
    assert len(jobs) == 2

    scheduler.stop()


def test_paper_trading_jobs():
    """Test PaperTradingJobs setup."""
    from paper_trading.scheduler import TradingScheduler, PaperTradingJobs, APSCHEDULER_AVAILABLE
    if not APSCHEDULER_AVAILABLE:
        pytest.skip("APScheduler not installed")

    scheduler = TradingScheduler()
    jobs = PaperTradingJobs(scheduler)
    jobs.set_session(1)

    scheduler.start()
    jobs.setup_nse_jobs()

    job_list = scheduler.get_jobs()
    job_ids = [j["id"] for j in job_list]

    assert "nse_exit_check" in job_ids
    assert "nse_signal_generation" in job_ids
    assert "nse_daily_snapshot" in job_ids

    scheduler.stop()
