import os
import redis
from rq import Worker, Queue
from src.config import settings
import logging

logger = logging.getLogger(__name__)

listen = ['default']

def start_worker():
    redis_url = settings.REDIS_URL
    conn = redis.from_url(redis_url)

    worker = Worker([Queue(q, connection=conn) for q in listen], connection=conn)
    worker.work()

if __name__ == '__main__':
    logger.info("Starting RQ Worker...")
    start_worker()
