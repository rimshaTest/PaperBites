# cli.py
import argparse
import asyncio
import logging
import os
from typing import Optional

from config import Config
from utils.logging import setup_logging
from paper.latest import get_latest_papers, CATEGORIES
from db import upsert_papers


async def fetch_latest_command(category: Optional[str], days: int, limit: int, sort_by: str = "date") -> int:
    """Fetch papers for one or all known categories and upsert them into MongoDB."""
    logger = logging.getLogger("paperbites.cli")
    categories = [category] if category else CATEGORIES
    total = 0

    for cat in categories:
        papers = await get_latest_papers(cat, days_back=days, limit=limit, sort_by=sort_by)
        written = upsert_papers(papers)
        total += written
        logger.info(f"'{cat}': fetched {len(papers)} papers, upserted {written}")

    return total


def main():
    """Main entry point for the CLI application."""
    parser = argparse.ArgumentParser(description="Fetch research papers into the PaperBites feed")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    fetch_parser = subparsers.add_parser("fetch-latest", help="Fetch latest papers from free APIs into MongoDB")
    fetch_parser.add_argument("--category", help="Single category to fetch (default: all known categories)", default=None)
    fetch_parser.add_argument("--days", help="How many days back to look", type=int, default=7)
    fetch_parser.add_argument("--limit", help="Max papers per category per source", type=int, default=20)
    fetch_parser.add_argument(
        "--sort-by", help="'date' for the latest papers, 'citations' for the most-cited in the window",
        choices=["date", "citations"], default="date",
    )
    fetch_parser.add_argument("--config", "-c", help="Path to config file", default="config.json")

    args = parser.parse_args()

    logger = setup_logging()
    config = Config(args.config)
    os.makedirs(config.get("paths.temp_dir"), exist_ok=True)

    async def run():
        if args.command == "fetch-latest":
            total = await fetch_latest_command(args.category, args.days, args.limit, sort_by=args.sort_by)
            logger.info(f"Upserted {total} papers total")
        else:
            parser.print_help()

    asyncio.run(run())

if __name__ == "__main__":
    main()
