from aiogram import Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging

from states.menu_states import MenuStates

router = Router(name="main_menu")
logger = logging.getLogger(__name__)

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """
    Show the all‑inline main menu.
    If there’s an old menu stored in state, delete it first (and log any failure).
    """
    data = await state.get_data()
    prev_id = data.get("menu_msg_id")
    if prev_id:
        try:
            await message.bot.delete_message(
                chat_id=message.chat.id, message_id=prev_id
            )
            logger.info(
                "Old main menu deleted",
                extra={
                    "telegram_user_id": message.from_user.id,
                    "chat_id": message.chat.id,
                    "is_system": False,
                },
            )
        except TelegramBadRequest as e:
            logger.warning(
                "Could not delete old menu (expired or already deleted): %s", e,
                extra={
                    "telegram_user_id": message.from_user.id,
                    "chat_id": message.chat.id,
                    "is_system": False,
                },
            )

    # Now clear any lingering state/data before showing a fresh menu
    await state.clear()
    await state.set_state(MenuStates.main)

    # Build and send the new inline menu
    kb = InlineKeyboardBuilder()
    for text, cd in [
        ("Option 1", "opt1"),
        ("Option 2", "opt2"),
        ("Option 3", "opt3"),
        ("Option 4", "opt4"),
    ]:
        kb.button(text=text, callback_data=cd)
    kb.adjust(2)

    menu_msg = await message.answer(
        "Main menu: choose an option.", reply_markup=kb.as_markup()
    )
    # Persist this message_id so the stale‑menu guard in your handlers can refer to it
    await state.update_data(menu_msg_id=menu_msg.message_id)

    logger.info(
        "Main menu displayed",
        extra={
            "telegram_user_id": message.from_user.id,
            "chat_id": message.chat.id,
            "is_system": False,
        },
    )

    # Tidy up the /start command message
    await message.delete()
