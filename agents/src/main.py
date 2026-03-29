"""Agent runner — starts Scanner and Indexer agents concurrently.

Entry point for the agents service. Handles graceful shutdown
on SIGTERM and SIGINT signals.
"""

import asyncio
import signal
import sys

from agents.src.utils import Config, MetadataClient, setup_logging
from agents.src.scanner_agent import ScannerAgent
from agents.src.indexer_agent import IndexerAgent
from agents.src.recommender_agent import RecommenderAgent
from agents.src.guardian_agent import GuardianAgent

logger = setup_logging("agent-runner")


async def run() -> None:
    """Start all agents and run until shutdown signal."""
    config = Config()
    metadata_client = MetadataClient(config)

    scanner = ScannerAgent(config, metadata_client)
    indexer = IndexerAgent(config, metadata_client)
    recommender = RecommenderAgent(config, metadata_client)
    guardian = GuardianAgent(config, metadata_client)

    # Set up graceful shutdown
    shutdown_event = asyncio.Event()

    def handle_signal(sig: int, frame) -> None:
        sig_name = signal.Signals(sig).name
        logger.info(f"Received {sig_name} — shutting down agents...")
        shutdown_event.set()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    # Start agents as concurrent tasks
    logger.info("Starting AI agents (Scanner, Indexer, Recommender, Guardian)...")
    scanner_task = asyncio.create_task(scanner.start())
    indexer_task = asyncio.create_task(indexer.start())
    recommender_task = asyncio.create_task(recommender.start())
    guardian_task = asyncio.create_task(guardian.start())

    # Wait for shutdown signal
    await shutdown_event.wait()

    # Stop agents gracefully
    logger.info("Stopping agents...")
    await scanner.stop()
    await indexer.stop()
    await recommender.stop()
    await guardian.stop()

    # Cancel tasks
    scanner_task.cancel()
    indexer_task.cancel()
    recommender_task.cancel()
    guardian_task.cancel()

    try:
        await asyncio.gather(
            scanner_task, indexer_task, recommender_task, guardian_task,
            return_exceptions=True,
        )
    except asyncio.CancelledError:
        pass

    logger.info("All agents stopped. Goodbye.")


def main() -> None:
    """CLI entry point."""
    logger.info("AlephFileShare AI Agent Runner")
    logger.info(f"Python {sys.version}")
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        logger.info("Interrupted — exiting.")


if __name__ == "__main__":
    main()
