#!/usr/bin/env python3
"""
Paper Trading CLI Runner

Usage:
    python scripts/run_paper_trading.py --create-session "My Session"
    python scripts/run_paper_trading.py --session-id 1 --run
    python scripts/run_paper_trading.py --session-id 1 --summary
"""
import argparse
import logging
import sys
import time
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent.parent)
sys.path.insert(0, project_root)

from paper_trading import PaperTradingEngine, PaperTradingConfig

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_session(engine: PaperTradingEngine, name: str):
    """Create a new trading session"""
    session = engine.create_session(name=name)
    print(f"\nCreated session:")
    print(f"  ID: {session.id}")
    print(f"  Name: {session.name}")
    print(f"  Balance: {session.current_balance:,.2f} {session.currency}")
    return session


def show_summary(engine: PaperTradingEngine, session_id: int):
    """Show session summary"""
    summary = engine.get_session_summary(session_id)

    if not summary:
        print(f"Session {session_id} not found")
        return

    print(f"\n{'='*50}")
    print(f"Session: {summary['session_name']} (ID: {summary['session_id']})")
    print(f"{'='*50}")
    print(f"Status: {summary['status']}")
    print(f"\nPortfolio:")
    print(f"  Initial Balance: {summary['initial_balance']:>15,.2f}")
    print(f"  Current Cash:    {summary['cash_available']:>15,.2f}")
    print(f"  Invested Value:  {summary['invested_value']:>15,.2f}")
    print(f"  Total Value:     {summary['total_value']:>15,.2f}")
    print(f"\nPerformance:")
    print(f"  Total P&L:       {summary['total_pnl']:>15,.2f} ({summary['total_pnl_pct']:+.2f}%)")
    print(f"  Open Positions:  {summary['num_open_positions']:>15}")
    print(f"  Total Trades:    {summary['total_trades']:>15}")
    print(f"  Win Rate:        {summary['win_rate']:>14.1f}%")
    print(f"{'='*50}\n")


def run_engine(engine: PaperTradingEngine, session_id: int, interval_seconds: int = 60):
    """Run the paper trading engine"""
    print(f"\nStarting paper trading engine for session {session_id}")
    print(f"Checking every {interval_seconds} seconds")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            # Check exits
            exits = engine.check_exits(session_id)
            for exit in exits:
                print(f"[EXIT] {exit['symbol']}: {exit['reason']} @ {exit['exit_price']:.2f} ({exit['pnl_pct']:+.2f}%)")

            # Show periodic summary
            summary = engine.get_session_summary(session_id)
            print(f"[{time.strftime('%H:%M:%S')}] Value: {summary['total_value']:,.2f} | P&L: {summary['total_pnl']:+,.2f} ({summary['total_pnl_pct']:+.2f}%) | Positions: {summary['num_open_positions']}")

            time.sleep(interval_seconds)

    except KeyboardInterrupt:
        print("\nStopping engine...")
        show_summary(engine, session_id)


def main():
    parser = argparse.ArgumentParser(description="Paper Trading CLI")
    parser.add_argument("--create-session", type=str, help="Create a new session with given name")
    parser.add_argument("--session-id", type=int, help="Session ID to use")
    parser.add_argument("--run", action="store_true", help="Run the trading engine")
    parser.add_argument("--summary", action="store_true", help="Show session summary")
    parser.add_argument("--interval", type=int, default=60, help="Check interval in seconds")
    parser.add_argument("--db", type=str, default="sqlite:///paper_trading.db", help="Database URL")

    args = parser.parse_args()

    # Initialize config and engine
    config = PaperTradingConfig()
    config.database_url = args.db
    engine = PaperTradingEngine(config)

    if args.create_session:
        create_session(engine, args.create_session)

    elif args.session_id and args.summary:
        show_summary(engine, args.session_id)

    elif args.session_id and args.run:
        run_engine(engine, args.session_id, args.interval)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
