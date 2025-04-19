from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.exceptions import TelegramBadRequest
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
    chat_id = message.chat.id

    # 1. Pull out the old menu ID (if any)…
    data = await state.get_data()
    old_msg_id = data.get("menu_msg_id")

    if old_msg_id:
        try:
            # 2. …try deleting it (48 h limit errors are caught)…
            await message.bot.delete_message(chat_id, old_msg_id)
            logger.info(
                "Old main menu deleted %s", old_msg_id,
                extra={"telegram_user_id": message.from_user.id, "chat_id": chat_id, "is_system": False}
            )
        except TelegramBadRequest as e:
            # 3. …log _why_ it failed
            logger.warning(
                "Could not delete old main menu %s: %s", old_msg_id, e,
                extra={"telegram_user_id": message.from_user.id, "chat_id": chat_id, "is_system": False}
            )

    # 4. Reset the FSM *state* but keep the stored data (so menu_msg_id stays available)
    await state.reset_state(with_data=False)
    # 5. Now move into the “main” state
    await state.set_state(MenuStates.main)

    # 6. Build & send a brand‑new menu
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
        "Main menu: choose an option.",
        reply_markup=kb.as_markup()
    )

    # 7. Store the new menu’s message_id
    await state.update_data(menu_msg_id=menu_msg.message_id)

    logger.info(
        "Main menu displayed %s", menu_msg.message_id,
        extra={"telegram_user_id": message.from_user.id, "chat_id": chat_id, "is_system": False}
    )

    # 8. Clean up the “/start” command message
    await message.delete()
