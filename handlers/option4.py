from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    ReplyKeyboardRemove,
    Message,
)
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from states.menu_states import MenuStates
from handlers.option1 import _close_inline  # helper that removes inline kb

router = Router()

# ---------- inline submenu ----------

@router.callback_query(MenuStates.main, F.data == "opt4")
async def enter_option4(cb: CallbackQuery, state: FSMContext):
    """Enter Option 4 submenu via inline button."""
    await state.set_state(MenuStates.option4)

    kb = InlineKeyboardBuilder()
    kb.button(text="Sub-option 4.1", callback_data="4.1")
    kb.button(text="Sub-option 4.2", callback_data="4.2")
    kb.button(text="Back", callback_data="back")
    kb.adjust(2, 1)
    await cb.message.edit_text("Option 4 menu:", reply_markup=kb.as_markup())
    await cb.answer()


# ---------- 4.1 (final) ----------

@router.callback_query(MenuStates.option4, F.data == "4.1")
async def option4_1(cb: CallbackQuery, state: FSMContext):
    await _close_inline(cb)
    await cb.message.answer("You selected sub-option 4.1")
    await state.clear()
    await cb.answer()


# ---------- 4.2 → opens reply keyboard ----------

@router.callback_query(MenuStates.option4, F.data == "4.2")
async def option4_2(cb: CallbackQuery, state: FSMContext):
    # hide inline keyboard
    await cb.message.edit_reply_markup(None)

    # build reply keyboard 4.2.1‑4
    rb = ReplyKeyboardBuilder()
    for i in range(1, 5):
        rb.button(text=f"4.2.{i}")
    rb.adjust(2, 2)

    await cb.message.answer(
        "Choose a sub‑option from 4.2:",
        reply_markup=rb.as_markup(resize_keyboard=True),
    )
    await state.set_state(MenuStates.option42)
    await cb.answer()


# ---------- Back from Option 4 ----------

@router.callback_query(MenuStates.option4, F.data.startswith("back"))
async def option4_back(cb: CallbackQuery, state: FSMContext):
    """Return to main inline menu."""
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


# ---------- handlers for 4.2.x (reply keyboard) ----------

@router.message(MenuStates.option42, F.text.regexp(r"^4\.2\.[1-4]$"))
async def option42_final(msg: Message, state: FSMContext):
    await msg.answer(
        f"You selected {msg.text}", reply_markup=ReplyKeyboardRemove()
    )
    await state.clear()
    await msg.delete()  # remove user's button press for clean chat
