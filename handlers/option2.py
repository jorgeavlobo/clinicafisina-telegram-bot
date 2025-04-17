from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states.menu_states import MenuStates
from handlers.option1 import _close_inline  # reuse helper

router = Router()


@router.callback_query(MenuStates.main, F.data == "opt2")
async def enter_option2(cb: CallbackQuery, state: FSMContext):
    await state.set_state(MenuStates.option2)

    kb = InlineKeyboardBuilder()
    kb.button(text="Sub-option 2.1", callback_data="2.1")
    kb.button(text="Sub-option 2.2", callback_data="2.2")
    kb.button(text="Back", callback_data="back")
    kb.adjust(2, 1)
    await cb.message.edit_text("Option 2 menu:", reply_markup=kb.as_markup())
    await cb.answer()


@router.callback_query(MenuStates.option2, F.data.in_(["2.1", "2.2"]))
async def option2_final(cb: CallbackQuery, state: FSMContext):
    await _close_inline(cb, f"You selected sub-option {cb.data}")
    await state.clear()
    await cb.answer()


@router.callback_query(MenuStates.option2, F.data.startswith("back"))
async def option2_back(cb: CallbackQuery, state: FSMContext):
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
