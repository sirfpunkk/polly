from aiogram.utils.keyboard import (
    InlineKeyboardBuilder,
    ReplyKeyboardBuilder
)
from aiogram.types import (
    InlineKeyboardButton,
    ReplyKeyboardMarkup
)

def main_menu() -> ReplyKeyboardMarkup:
    builder = ReplyKeyboardBuilder()
    builder.button(text="🔍 Найти объявления")
    builder.button(text="⚙️ Мои фильтры")
    builder.button(text="💰 Тарифы")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def inline_listings_kb(listing_id: int) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.add(
        InlineKeyboardButton(
            text="📞 Показать контакт",
            callback_data=f"contact_{listing_id}"
        ),
        InlineKeyboardButton(
            text="❤️ В избранное",
            callback_data=f"fav_{listing_id}"
        )
    )
    return builder
