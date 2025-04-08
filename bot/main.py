import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from config import settings
from .handlers import admin, payments, user_handlers
from .middlewares import ThrottlingMiddleware

# Настройка логгера
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Инициализация бота
bot = Bot(token=settings.BOT_TOKEN, parse_mode="HTML")
storage = RedisStorage.from_url(settings.REDIS_URL)
dp = Dispatcher(storage=storage)

# Регистрация middleware
dp.message.middleware(ThrottlingMiddleware())

# Регистрация роутеров
dp.include_router(admin.router)
dp.include_router(payments.router)
dp.include_router(user_handlers.router)

async def on_startup():
    await bot.send_message(
        settings.ADMIN_ID, 
        "Бот успешно запущен!"
    )

async def on_shutdown():
    await bot.send_message(
        settings.ADMIN_ID,
        "Бот остановлен!"
    )
