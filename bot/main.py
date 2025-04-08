import asyncio
import logging
from typing import Optional, Dict, List

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup,
    InlineKeyboardButton, InputMediaPhoto
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.redis import RedisStorage

from database import Database
from parsers.cian import CianParser
from parsers.avito import AvitoParser
from parsers.telegram import TelegramParser
from payment import PaymentSystem
from config import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Инициализация хранилища состояний
storage = RedisStorage.from_url(f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}")
dp = Dispatcher(storage=storage)

# Инициализация базы данных
db = Database(
    db_url=f"postgresql://{settings.DB_USER}:{settings.DB_PASSWORD}@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
)

# Инициализация платежной системы
payment = PaymentSystem(yoomoney_token=settings.YOOMONEY_TOKEN)

# Инициализация парсеров
cian_parser = CianParser(db=db)
avito_parser = AvitoParser(db=db)
telegram_parser = TelegramParser(db=db)

# Состояния для FSM
class UserStates(StatesGroup):
    SET_FILTERS = State()
    SET_PRICE = State()
    SET_AREA = State()
    SET_ROOMS = State()
    SET_DISTRICTS = State()
    SET_PROPERTY_TYPE = State()

# Класс для управления ботом
class PollyParserBot:
    def __init__(self, token: str):
        self.bot = Bot(token=token, parse_mode=ParseMode.HTML)
        self.active_parsers = {
            'cian': cian_parser,
            'avito': avito_parser,
            'telegram': telegram_parser
        }

    async def start(self):
        await dp.start_polling(self.bot)

    # Регистрация обработчиков
    def register_handlers(self):
        dp.message.register(self.handle_start, CommandStart())
        dp.message.register(self.handle_help, Command('help'))
        dp.callback_query.register(self.handle_main_menu, F.data.in_([
            'main_menu', 'search', 'filters', 'tariffs', 'promo', 'ref', 'support'
        ]))
        dp.callback_query.register(self.handle_show_contact, F.data.startswith('contact_'))
        dp.callback_query.register(self.handle_payment, F.data.startswith('pay_'))

    # Обработчики команд
    async def handle_start(self, message: Message):
        user_id = message.from_user.id
        username = message.from_user.username
        ref_code = message.text.split()[1] if len(message.text.split()) > 1 else None

        # Регистрация пользователя
        await db.register_user(user_id, username, ref_code)

        # Отправка главного меню
        await message.answer(
            "🏠 <b>Polly Parser</b> - умный поиск недвижимости в Краснодаре\n\n"
            "Я помогу найти лучшие предложения от частных собственников на ЦИАН, Авито и в Telegram-чатах.",
            reply_markup=self.main_menu_kb()
        )

    async def handle_help(self, message: Message):
        await message.answer(
            "ℹ️ <b>Как использовать бота:</b>\n\n"
            "1. Нажмите <b>Найти объявления</b> для поиска по сохраненным фильтрам\n"
            "2. В <b>Мои фильтры</b> настройте параметры поиска\n"
            "3. Выберите подходящий тариф в разделе <b>Тарифы</b>\n\n"
            "По всем вопросам обращайтесь в <b>Поддержку</b>",
            reply_markup=self.main_menu_kb()
        )

    # Обработчики callback-запросов
    async def handle_main_menu(self, callback: CallbackQuery):
        action = callback.data

        if action == 'main_menu':
            await callback.message.edit_text(
                "🏠 <b>Главное меню</b>",
                reply_markup=self.main_menu_kb()
            )
        elif action == 'search':
            await self.handle_search(callback)
        elif action == 'filters':
            await self.handle_filters(callback)
        elif action == 'tariffs':
            await self.handle_tariffs(callback)
        elif action == 'promo':
            await self.handle_promo(callback)
        elif action == 'ref':
            await self.handle_ref(callback)
        elif action == 'support':
            await self.handle_support(callback)

    async def handle_search(self, callback: CallbackQuery):
        user_id = callback.from_user.id
        
        # Проверка подписки
        if not await db.check_subscription(user_id):
            await callback.answer("❌ У вас нет активной подписки!", show_alert=True)
            await self.handle_tariffs(callback)
            return

        # Проверка лимита запросов
        if await db.get_daily_requests(user_id) >= 100:
            await callback.answer("❌ Вы исчерпали дневной лимит запросов!", show_alert=True)
            return

        # Получение сохраненных фильтров
        filters = await db.get_user_filters(user_id)
        if not filters:
            await callback.answer("ℹ️ Сначала настройте фильтры!", show_alert=True)
            await self.handle_filters(callback)
            return

        # Поиск объявлений
        await callback.message.edit_text("🔍 Ищу подходящие объявления...")
        listings = await db.get_listings(filters)

        if not listings:
            await callback.message.edit_text(
                "😕 По вашим фильтрам ничего не найдено",
                reply_markup=self.main_menu_kb()
            )
            return

        # Отправка результатов
        await self.send_listings(callback.message, listings[:25])
        await db.increment_requests(user_id)

    async def handle_filters(self, callback: CallbackQuery):
        await callback.message.edit_text(
            "⚙️ <b>Настройка фильтров</b>\n\n"
            "Выберите параметр для изменения:",
            reply_markup=self.filters_menu_kb()
        )

    async def handle_tariffs(self, callback: CallbackQuery):
        user_id = callback.from_user.id
        sub_info = await db.get_subscription_info(user_id)

        text = "💰 <b>Тарифы</b>\n\n"
        if sub_info:
            text += f"✅ Ваша подписка активна до: {sub_info['expires_at']}\n\n"

        text += (
            "1. <b>24 часа</b> - 300₽\n"
            "2. <b>30 дней</b> - 2900₽ (экономия 10%)\n"
            "3. <b>365 дней</b> - 23000₽ (экономия 35%)\n\n"
            "После оплаты доступ активируется автоматически"
        )

        await callback.message.edit_text(
            text,
            reply_markup=self.tariffs_menu_kb()
        )

    async def handle_promo(self, callback: CallbackQuery):
        await callback.message.edit_text(
            "🎁 <b>Промокод</b>\n\n"
            "Введите промокод для активации:",
            reply_markup=self.back_to_menu_kb()
        )
        # Здесь нужно добавить обработку ввода промокода через FSM

    async def handle_ref(self, callback: CallbackQuery):
        user_id = callback.from_user.id
        ref_link = f"https://t.me/{settings.BOT_USERNAME}?start=ref{user_id}"
        ref_count = await db.get_ref_count(user_id)
        ref_balance = await db.get_ref_balance(user_id)

        await callback.message.edit_text(
            "👥 <b>Реферальная программа</b>\n\n"
            f"Ваша ссылка: <code>{ref_link}</code>\n\n"
            f"Приглашено: <b>{ref_count}</b> пользователей\n"
            f"Ваш баланс: <b>{ref_balance}₽</b>\n\n"
            "За каждого приглашенного вы получаете 10% от его платежей",
            reply_markup=self.back_to_menu_kb()
        )

    async def handle_support(self, callback: CallbackQuery):
        await callback.message.edit_text(
            "🛠 <b>Поддержка</b>\n\n"
            "По всем вопросам пишите @polly_support\n"
            "Время ответа: до 24 часов",
            reply_markup=self.back_to_menu_kb()
        )

    async def handle_show_contact(self, callback: CallbackQuery):
        listing_id = int(callback.data.split('_')[1])
        contact = await db.get_listing_contact(listing_id)

        if not contact:
            await callback.answer("Контакт не найден", show_alert=True)
            return

        # Создаем временную ссылку для защиты от скрейпинга
        temp_link = await self.generate_temp_contact_link(contact)
        await callback.answer()
        await callback.message.answer(
            f"📞 Контакт: {temp_link}\n\n"
            "⚠️ Используйте только для личного обращения",
            disable_web_page_preview=True
        )

    async def handle_payment(self, callback: CallbackQuery):
        tariff = callback.data.split('_')[1]
        user_id = callback.from_user.id

        payment_url = await payment.create_payment_link(
            user_id=user_id,
            amount=self.get_tariff_price(tariff),
            description=f"Подписка Polly Parser ({tariff})"
        )

        await callback.message.edit_text(
            "💳 <b>Оплата подписки</b>\n\n"
            f"Тариф: <b>{self.get_tariff_name(tariff)}</b>\n"
            f"Сумма: <b>{self.get_tariff_price(tariff)}₽</b>\n\n"
            "Нажмите кнопку ниже для оплаты:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Оплатить", url=payment_url)],
                [InlineKeyboardButton(text="Проверить оплату", callback_data=f"check_pay_{tariff}")],
                [InlineKeyboardButton(text="Назад", callback_data="tariffs")]
            ])
        )

    # Вспомогательные методы
    def main_menu_kb(self):
        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(text="🔍 Найти объявления", callback_data="search"),
            InlineKeyboardButton(text="⚙️ Мои фильтры", callback_data="filters"),
            InlineKeyboardButton(text="💰 Тарифы", callback_data="tariffs"),
            InlineKeyboardButton(text="🎁 Промокод", callback_data="promo"),
            InlineKeyboardButton(text="👥 Рефералка", callback_data="ref"),
            InlineKeyboardButton(text="🛠 Поддержка", callback_data="support")
        )
        builder.adjust(2)
        return builder.as_markup()

    def filters_menu_kb(self):
        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(text="💰 Цена", callback_data="set_price"),
            InlineKeyboardButton(text="📏 Площадь", callback_data="set_area"),
            InlineKeyboardButton(text="🚪 Комнаты", callback_data="set_rooms"),
            InlineKeyboardButton(text="🗺 Районы", callback_data="set_districts"),
            InlineKeyboardButton(text="🏘 Тип жилья", callback_data="set_property_type"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")
        )
        builder.adjust(2)
        return builder.as_markup()

    def tariffs_menu_kb(self):
        builder = InlineKeyboardBuilder()
        builder.add(
            InlineKeyboardButton(text="24 часа - 300₽", callback_data="pay_day"),
            InlineKeyboardButton(text="30 дней - 2900₽", callback_data="pay_month"),
            InlineKeyboardButton(text="365 дней - 23000₽", callback_data="pay_year"),
            InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")
        )
        builder.adjust(1)
        return builder.as_markup()

    def back_to_menu_kb(self):
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main_menu")]
        ])

    async def send_listings(self, message: Message, listings: List[Dict]):
        for listing in listings:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="📞 Показать контакт",
                    callback_data=f"contact_{listing['id']}"
                )]
            ])

            text = (
                f"🏠 <b>{listing['source']}</b>\n"
                f"💰 <b>{listing['price']:,}₽</b>\n"
                f"📍 <b>{listing['district']}</b>\n"
                f"📏 <b>{listing['area']}м²</b> ({listing['rooms']}к)\n"
                f"🏢 <b>{listing['floor']}/{listing['total_floors']} этаж</b>\n"
                f"🕒 <i>{listing['posted_at']}</i>"
            )

            if listing.get('photo_urls'):
                media = InputMediaPhoto(
                    media=listing['photo_urls'][0],
                    caption=text
                )
                await message.answer_media_group([media])
                await message.answer("↗️", reply_markup=kb)
            else:
                await message.answer(text, reply_markup=kb)

            await asyncio.sleep(0.5)  # Защита от флуда

    async def generate_temp_contact_link(self, contact: str) -> str:
        # Реализация генерации временной ссылки
        token = await db.create_temp_contact_token(contact)
        return f"{settings.WEBHOOK_URL}/contact/{token}"

    def get_tariff_name(self, tariff: str) -> str:
        names = {
            'day': '24 часа',
            'month': '30 дней',
            'year': '365 дней'
        }
        return names.get(tariff, '')

    def get_tariff_price(self, tariff: str) -> int:
        prices = {
            'day': 300,
            'month': 2900,
            'year': 23000
        }
        return prices.get(tariff, 0)

    # Методы для работы с парсерами
    async def start_parsers(self):
        for name, parser in self.active_parsers.items():
            asyncio.create_task(self.run_parser(name, parser))

    async def run_parser(self, name: str, parser):
        while True:
            try:
                logger.info(f"Запуск парсера {name}")
                await parser.run()
            except Exception as e:
                logger.error(f"Ошибка в парсере {name}: {e}")
                await self.notify_admin(f"🚨 Парсер {name} упал с ошибкой: {e}")
            
            # Ожидание перед следующим запуском
            delay = 1800 if name != 'telegram' else 600  # 30 или 10 минут
            await asyncio.sleep(delay)

    async def notify_admin(self, text: str):
        await self.bot.send_message(settings.ADMIN_ID, text)

# Запуск бота
async def main():
    bot = PollyParserBot(token=settings.BOT_TOKEN)
    bot.register_handlers()
    
    # Инициализация базы данных
    await db.init_db()
    
    # Запуск парсеров
    await bot.start_parsers()
    
    # Запуск бота
    await bot.start()

if __name__ == "__main__":
    asyncio.run(main())