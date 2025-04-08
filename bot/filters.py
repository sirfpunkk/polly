from aiogram import BaseMiddleware
from typing import Dict, Any, Callable, Awaitable
from aiogram.types import TelegramObject

class SubscriptionFilter(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = data.get("event_from_user")
        if not user:
            return await handler(event, data)
        
        # Проверка подписки
        if not await data['db'].check_subscription(user.id):
            await event.answer(
                "❌ У вас нет активной подписки!",
                reply_markup=data['keyboards'].tariffs_kb()
            )
            return
        
        return await handler(event, data)
