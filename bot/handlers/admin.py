from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command

router = Router()

@router.message(Command("admin"))
async def admin_panel(message: Message):
    if message.from_user.id != config.ADMIN_ID:
        return
    
    await message.answer(
        "Панель администратора:",
        reply_markup=admin_kb()
    )

@router.callback_query(F.data == "statistics"))
async def show_stats(callback: CallbackQuery):
    stats = await db.get_stats()
    await callback.message.edit_text(
        f"📊 Статистика:\n\n"
        f"Пользователей: {stats['users']}\n"
        f"Активных подписок: {stats['active_subs']}\n"
        f"Запросов сегодня: {stats['daily_requests']}"
    )
