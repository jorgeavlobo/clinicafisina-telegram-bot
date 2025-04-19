from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states.menu_states import MenuStates

router = Router()

async def _close_inline(cb: CallbackQuery, summary: str):
    """Edit current message to summary text and remove inline keyboard."""
    await cb.message.edit_text(summary, reply_markup=None)

@router.callback_query(MenuStates.main, F.data == "opt1")
async def enter_option1(cb: CallbackQuery, state: FSMContext):
    # 🔒 stale-menu guard
    data = await state.get_data()
    if cb.message.message_id != data.get("menu_msg_id"):
        await cb.answer(
            "This menu is outdated. Please send /start again.",
            show_alert=True
        )
        return

    await state.set_state(MenuStates.option1)

    kb = InlineKeyboardBuilder()
    kb.button(text="Sub-option 1.1", callback_data="1.1")
    kb.button(text="Sub-option 1.2", callback_data="1.2")
    kb.button(text="Back", callback_data="back")
    kb.adjust(2, 1)
    await cb.message.edit_text("Option 1 menu:", reply_markup=kb.as_markup())
    await cb.answer()

@router.callback_query(MenuStates.option1, F.data.in_(["1.1", "1.2"]))
async def option1_final(cb: CallbackQuery, state: FSMContext):
    await _close_inline(cb, f"You selected sub-option {cb.data}")
    await state.clear()
    await cb.answer()

@router.callback_query(MenuStates.option1, F.data.startswith("back"))
async def option1_back(cb: CallbackQuery, state: FSMContext):
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
    await cb.message.edit_text(
        "Main menu: choose an option.", reply_markup=kb.as_markup()
    )
    await cb.answer()
