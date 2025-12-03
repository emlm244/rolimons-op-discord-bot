#!/usr/bin/env python3
"""Startup script for RISniper bot."""

import sys
import logging

# Configure logging before imports
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("risniper.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("risniper")


def main() -> int:
    """Main entry point."""
    logger.info("Starting RISniper...")

    # Validate configuration
    from src.config import config

    errors = config.validate()
    if errors:
        for error in errors:
            logger.error(f"Config error: {error}")
        logger.error("Please check your .env file")
        return 1

    logger.info("Configuration validated")
    logger.info(f"Purchase mode: {config.purchase_mode.value}")
    logger.info(f"Strategies: {[s.value for s in config.strategy_flags]}")
    logger.info(f"UGC mode: {config.ugc_mode.value}")
    logger.info(f"Snipe threshold: {config.snipe_threshold}")
    logger.info(f"Max price per item: {config.max_price_per_item:,} R$")
    logger.info(f"Total budget: {config.total_budget:,} R$")

    # Run the bot
    from src.bot import run_bot

    try:
        run_bot()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
