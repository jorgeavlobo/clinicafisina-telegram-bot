from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states.menu_states import MenuStates
from handlers.option1 import _close_inline  # reuse

router = Router()

@router.callback_query(MenuStates.main, F.data == "opt4")
async def enter_option4(cb: CallbackQuery, state: FSMContext):
    # 🔒 stale-menu guard
    data = await state.get_data()
    if cb.message.message_id != data.get("menu_msg_id"):
        await cb.answer(
            "This menu is outdated. Please send /start again.",
            show_alert=True
        )
        return

    await state.set_state(MenuStates.option4)

    kb = InlineKeyboardBuilder()
    kb.button(text="Sub-option 4.1", callback_data="4.1")
    kb.button(text="Sub-option 4.2", callback_data="4.2")
    kb.button(text="Back", callback_data="back")
    kb.adjust(2, 1)
    await cb.message.edit_text("Option 4 menu:", reply_markup=kb.as_markup())
    await cb.answer()

@router.callback_query(MenuStates.option4, F.data == "4.1")
async def option4_1(cb: CallbackQuery, state: FSMContext):
    await _close_inline(cb, "You selected sub-option 4.1")
    await state.clear()
    await cb.answer()

@router.callback_query(MenuStates.option4, F.data == "4.2")
async def option4_2(cb: CallbackQuery, state: FSMContext):
    await state.set_state(MenuStates.option42)

    kb = InlineKeyboardBuilder()
    for i in range(1, 4):
        kb.button(text=f"4.2.{i}", callback_data=f"4.2.{i}")
    kb.button(text="Back", callback_data="back42")
    kb.adjust(3, 1)

    await cb.message.edit_text("Sub‑option 4.2 menu:", reply_markup=kb.as_markup())
    await cb.answer()

@router.callback_query(MenuStates.option42, F.data.regexp(r"^4\.2\.[1-3]$"))
async def option42_final(cb: CallbackQuery, state: FSMContext):
    await _close_inline(cb, f"You selected {cb.data}")
    await state.clear()
    await cb.answer()

@router.callback_query(MenuStates.option42, F.data == "back42")
async def option42_back(cb: CallbackQuery, state: FSMContext):
    await state.set_state(MenuStates.option4)

    kb = InlineKeyboardBuilder()
    kb.button(text="Sub-option 4.1", callback_data="4.1")
    kb.button(text="Sub-option 4.2", callback_data="4.2")
    kb.button(text="Back", callback_data="back")
    kb.adjust(2, 1)

    await cb.message.edit_text("Option 4 menu:", reply_markup=kb.as_markup())
    await cb.answer()

@router.callback_query(MenuStates.option4, F.data.startswith("back"))
async def option4_back(cb: CallbackQuery, state: FSMContext):
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
