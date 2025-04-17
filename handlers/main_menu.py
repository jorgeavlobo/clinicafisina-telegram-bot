from aiogram import Router, F
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from states.menu_states import MenuStates

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """
    Handles /start: resets FSM and shows the main menu.
    """
    await state.clear()
    await state.set_state(MenuStates.main)

    # --- reply keyboard (Options 1‑2) via builder ---
    rb = ReplyKeyboardBuilder()
    rb.button(text="Option 1")
    rb.button(text="Option 2")
    rb.adjust(2)                                   # two buttons in one row
    main_reply_kb = rb.as_markup(resize_keyboard=True)

    # --- inline keyboard (Options 3‑4) ---
    main_inline_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Option 3", callback_data="opt3"),
                InlineKeyboardButton(text="Option 4", callback_data="opt4"),
            ]
        ]
    )

    # send both keyboards
    reply_msg = await message.answer(
        "Main menu loaded. Use the keyboard for Option 1 or 2.",
        reply_markup=main_reply_kb,
    )
    inline_msg = await message.answer(
        "Select an inline option:", reply_markup=main_inline_kb
    )

    # remember inline‑menu message id
    await state.update_data(inline_msg_id=inline_msg.message_id)

    # clean up user command and bot's first reply
    await message.delete()
    await reply_msg.delete()
