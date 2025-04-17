from aiogram import Router, F
from aiogram.types import (
    CallbackQuery,
    ReplyKeyboardRemove,
    Message,
)
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from states.menu_states import MenuStates
from handlers.option1 import _close_inline

router = Router()

# ---------- inline submenu ----------


@router.callback_query(MenuStates.main, F.data == "opt4")
async def enter_option4(cb: CallbackQuery, state: FSMContext):
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
    await _close_inline(cb)
    await cb.message.answer("You selected sub-option 4.1")
    await state.clear()
    await cb.answer()

# ---------- 4.2 opens REPLY keyboard ----------


@router.callback_query(MenuStates.option4, F.data == "4.2")
async def option4_2(cb: CallbackQuery, state: FSMContext):
    # close inline keyboard first
    await cb.message.edit_reply_markup(None)

    # build reply keyboard with 4 buttons
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


# -------- handlers for 4.2.x (reply keyboard) --------


@router.message(MenuStates.option42, F.text.regexp(r"^4\.2\.[1-4]$"))
async def option42_final(msg: Message, state: FSMContext):
    await msg.answer(
        f"You selected {msg.text}", reply_markup=ReplyKeyboardRemove()
    )
    await state.clear()
    # delete user's button press for clean UI
    await msg.delete()
