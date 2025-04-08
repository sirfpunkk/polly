from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

router = Router()

@router.callback_query(F.data.startswith("tariff_")))
async def select_tariff(callback: CallbackQuery):
    tariff = callback.data.split("_")[1]
    await callback.message.edit_text(
        f"Выбран тариф: {tariff}\n"
        "Перейдите по ссылке для оплаты:",
        reply_markup=payment_kb(tariff)
    )
