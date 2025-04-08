from aiogram import BaseMiddleware
from aiogram.types import Message
from typing import Callable, Dict, Any, Awaitable
from cachetools import TTLCache

# Защита от флуда (10 сообщений в минуту)
class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self):
        self.cache = TTLCache(maxsize=1000, ttl=60)

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if user.id in self.cache:
            if self.cache[user.id] >= 10:
                await event.answer("Слишком много запросов! Подождите 1 минуту.")
                return
            self.cache[user.id] += 1
        else:
            self.cache[user.id] = 1
        
        return await handler(event, data)
