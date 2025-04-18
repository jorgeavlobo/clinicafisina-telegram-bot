from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging

from states.menu_states import MenuStates

router = Router()
logger = logging.getLogger(__name__)

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """
    Show the all‑inline main menu.
    If the user already has a menu message, delete it first to avoid duplicates.
    """
    prev = await state.get_data()
    prev_id = prev.get("menu_msg_id")
    if prev_id:
        try:
            await message.bot.delete_message(message.chat.id, prev_id)
            logger.info(
                "Old main menu deleted",
                extra={
                    "telegram_user_id": message.from_user.id,
                    "chat_id": message.chat.id,
                    "is_system": False,
                },
            )
        except Exception:
            pass  # message might be gone already

    await state.clear()
    await state.set_state(MenuStates.main)

    kb = InlineKeyboardBuilder()
    for text, cd in [
        ("Option 1", "opt1"),
        ("Option 2", "opt2"),
        ("Option 3", "opt3"),
        ("Option 4", "opt4"),
    ]:
        kb.button(text=text, callback_data=cd)
    kb.adjust(2)

    menu_msg = await message.answer(
        "Main menu: choose an option.", reply_markup=kb.as_markup()
    )
    await state.update_data(menu_msg_id=menu_msg.message_id)

    logger.info(
        "Main menu displayed",
        extra={
            "telegram_user_id": message.from_user.id,
            "chat_id": message.chat.id,
            "is_system": False,
        },
    )

    await message.delete()
