from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states.menu_states import MenuStates

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """
    Show the all‑inline main menu.
    If the user already has a menu message, delete it first to avoid duplicates.
    """
    # try to delete previous menu (before clearing storage!)
    prev = await state.get_data()
    prev_id = prev.get("menu_msg_id")
    if prev_id:
        try:
            await message.bot.delete_message(message.chat.id, prev_id)
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
    kb.adjust(2)  # two buttons per row

    menu_msg = await message.answer(
        "Main menu: choose an option.", reply_markup=kb.as_markup()
    )
    await state.update_data(menu_msg_id=menu_msg.message_id)

    # delete the /start command itself for a clean chat
    await message.delete()
