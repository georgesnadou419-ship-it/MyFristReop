import logging

from config import settings
from database import create_session_factory
from gpu_allocator import GpuAllocator
from queue_manager import QueueManager
from scheduler import Scheduler


def configure_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def main() -> None:
    configure_logging()
    session_factory = create_session_factory(settings.database_url)
    queue_manager = QueueManager(settings.redis_url)
    scheduler = Scheduler(
        session_factory=session_factory,
        queue_manager=queue_manager,
        allocator=GpuAllocator(),
        schedule_interval=settings.schedule_interval,
    )
    scheduler.run()


if __name__ == "__main__":
    main()
