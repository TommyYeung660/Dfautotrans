"""Logging utilities for Dead Frontier Auto Trading System."""

import sys
from pathlib import Path
from loguru import logger
from typing import Optional

from ..config.settings import Settings


def setup_logging(settings: Optional[Settings] = None) -> None:
    """Setup logging configuration.
    
    Args:
        settings: Application settings. If None, will create default settings.
    """
    if settings is None:
        settings = Settings()
    
    # Remove default handler
    logger.remove()
    
    # Console handler with colors
    logger.add(
        sys.stdout,
        level=settings.logging.level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=True,
        backtrace=True,
        diagnose=True
    )
    
    # File handler
    log_file = settings.logs_dir / settings.logging.file
    logger.add(
        log_file,
        level=settings.logging.level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        backtrace=True,
        diagnose=True
    )
    
    # Add specific handlers for different components
    
    # Trading operations log
    trading_log = settings.logs_dir / "trading.log"
    logger.add(
        trading_log,
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        filter=lambda record: "trading" in record["extra"],
        rotation="5 MB",
        retention="90 days"
    )
    
    # Browser operations log
    browser_log = settings.logs_dir / "browser.log"
    logger.add(
        browser_log,
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {message}",
        filter=lambda record: "browser" in record["extra"],
        rotation="5 MB",
        retention="7 days"
    )
    
    # Error log
    error_log = settings.logs_dir / "errors.log"
    logger.add(
        error_log,
        level="ERROR",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
        rotation="1 MB",
        retention="180 days"
    )


def get_logger(name: str, **extra_context):
    """Get a logger with specific context.
    
    Args:
        name: Logger name
        **extra_context: Additional context to bind to logger
        
    Returns:
        Configured logger instance
    """
    return logger.bind(name=name, **extra_context)


# Specialized loggers for different components
def get_trading_logger():
    """Get trading operations logger."""
    return get_logger("trading", trading=True)


def get_browser_logger():
    """Get browser operations logger."""
    return get_logger("browser", browser=True)


def get_market_logger():
    """Get market analysis logger."""
    return get_logger("market", trading=True)


def get_risk_logger():
    """Get risk management logger."""
    return get_logger("risk", trading=True) 