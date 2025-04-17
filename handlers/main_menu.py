from aiogram import Router
from aiogram.types import Message
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states.menu_states import MenuStates

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Show the all‑inline main menu."""
    await state.clear()
    await state.set_state(MenuStates.main)

    kb = InlineKeyboardBuilder()
    kb.button(text="Option 1", callback_data="opt1")
    kb.button(text="Option 2", callback_data="opt2")
    kb.button(text="Option 3", callback_data="opt3")
    kb.button(text="Option 4", callback_data="opt4")
    kb.adjust(2)                 # 2 per row → rows: [1,2] [3,4]
    main_inline_kb = kb.as_markup()

    menu_msg = await message.answer(
        "Main menu: choose an option.", reply_markup=main_inline_kb
    )
    await state.update_data(menu_msg_id=menu_msg.message_id)

    # delete command for clean UI
    await message.delete()
