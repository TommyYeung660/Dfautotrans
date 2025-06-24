#!/usr/bin/env python3
"""Dead Frontier Auto Trading System - Main Entry Point"""

import asyncio
import argparse
from pathlib import Path

from src.dfautotrans.app import DeadFrontierAutoTrader
from src.dfautotrans.config.settings import Settings
from src.dfautotrans.utils.logger import setup_logging


async def main():
    """Main program entry point"""
    parser = argparse.ArgumentParser(description="Dead Frontier Auto Trader")
    parser.add_argument("--config", type=str, help="Configuration file path")
    parser.add_argument("--headless", action="store_true", help="Run in headless mode")
    parser.add_argument("--dry-run", action="store_true", help="Test mode (no actual trades)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    
    args = parser.parse_args()
    
    # Load configuration
    config = Settings()
    if args.config:
        config = Settings(_env_file=args.config)
    
    if args.headless:
        config.browser.headless = True
    
    if args.debug:
        config.log_level = "DEBUG"
    
    # Setup logging
    setup_logging(config.log_level, config.log_file)
    
    # Start trading system
    trader = DeadFrontierAutoTrader(config)
    await trader.start()


if __name__ == "__main__":
    asyncio.run(main()) 