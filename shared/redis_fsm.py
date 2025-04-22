"""
Construtores auxiliares para Redis usado pelo FSM.
Mantém‑se separado para isolar dependências e facilitar testes.
"""

from redis.asyncio import Redis
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from shared.config import settings


def build_redis() -> Redis:
    """Devolve instância Redis asyncio‑friendly."""
    return Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=False,
    )


def build_redis_storage() -> RedisStorage:
    """
    Cria o RedisStorage usado pelo Aiogram:
      storage = build_redis_storage()
    """
    redis = build_redis()
    return RedisStorage(
        redis=redis,
        state_ttl=24 * 3600,
        data_ttl=24 * 3600,
        key_builder=DefaultKeyBuilder(
            prefix=settings.REDIS_PREFIX,
            with_bot_id=True,
        ),
    )
