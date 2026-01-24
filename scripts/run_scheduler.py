#!/usr/bin/env python3
"""Run the paper trading scheduler."""
import argparse
import logging
import signal
import sys
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Run Paper Trading Scheduler")
    parser.add_argument("--session-id", type=int, required=True, help="Trading session ID")
    parser.add_argument("--market", choices=["nse", "crypto", "both"], default="both", help="Market to trade")
    args = parser.parse_args()

    from paper_trading.scheduler import TradingScheduler, PaperTradingJobs, APSCHEDULER_AVAILABLE

    if not APSCHEDULER_AVAILABLE:
        logger.error("APScheduler not installed. Run: pip install apscheduler")
        sys.exit(1)

    from paper_trading.engine import PaperTradingEngine
    from paper_trading.performance_tracker import PerformanceTracker
    from paper_trading.models import SessionLocal
    from paper_trading.config import PaperTradingConfig

    # Initialize components
    db = SessionLocal()
    config = PaperTradingConfig()
    engine = PaperTradingEngine(config)
    tracker = PerformanceTracker(db)

    scheduler = TradingScheduler()
    jobs = PaperTradingJobs(
        scheduler=scheduler,
        engine=engine,
        performance_tracker=tracker,
    )
    jobs.set_session(args.session_id)

    # Set up jobs based on market
    if args.market in ["nse", "both"]:
        jobs.setup_nse_jobs()
    if args.market in ["crypto", "both"]:
        jobs.setup_crypto_jobs()

    # Handle shutdown
    def shutdown(signum, frame):
        logger.info("Shutting down scheduler...")
        scheduler.stop()
        db.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # Start scheduler
    scheduler.start()
    logger.info(f"Scheduler running for session {args.session_id}")
    logger.info(f"Markets: {args.market}")
    logger.info("Press Ctrl+C to stop")

    # Keep running
    while True:
        time.sleep(60)
        jobs_info = scheduler.get_jobs()
        logger.debug(f"Active jobs: {len(jobs_info)}")


if __name__ == "__main__":
    main()
