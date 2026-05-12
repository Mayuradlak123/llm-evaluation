import os
import redis
from dotenv import load_dotenv

from .logger import logger

load_dotenv()

def get_redis_client():
    try:
        client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD", None),
            decode_responses=True
        )
        # Test connection
        client.ping()
        logger.info("Successfully connected to Redis")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {str(e)}")
        return None

import redis.asyncio as async_redis

def get_async_redis_client():
    try:
        client = async_redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASSWORD", None),
            decode_responses=True
        )
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Async Redis: {str(e)}")
        return None

redis_client = get_redis_client()
async_redis_client = get_async_redis_client()
