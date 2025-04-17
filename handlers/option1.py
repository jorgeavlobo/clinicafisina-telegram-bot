from aiogram import Router, F, Bot
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from states.menu_states import MenuStates

router = Router()


@router.message(MenuStates.main, F.text == "Option 1")
async def enter_option1(message: Message, state: FSMContext, bot: Bot):
    """Enter Option 1 submenu."""
    data = await state.get_data()
    inline_msg_id = data.get("inline_msg_id")
    if inline_msg_id:
        await bot.delete_message(message.chat.id, inline_msg_id)

    await state.set_state(MenuStates.option1)

    # submenu reply keyboard
    rb = ReplyKeyboardBuilder()
    rb.button(text="Sub-option 1.1")
    rb.button(text="Sub-option 1.2")
    rb.button(text="Back")
    rb.adjust(2, 1)                                # two buttons first row, one second
    sub_reply_kb = rb.as_markup(resize_keyboard=True)

    sub_menu_msg = await message.answer(
        "You are now in the Option 1 menu. Select a sub‑option or go back.",
        reply_markup=sub_reply_kb,
    )
    await state.update_data(option1_msg_id=sub_menu_msg.message_id)


@router.message(MenuStates.option1, F.text == "Sub-option 1.1")
async def option1_sub1(message: Message, state: FSMContext):
    await message.answer("You selected sub-option 1.1")


@router.message(MenuStates.option1, F.text == "Sub-option 1.2")
async def option1_sub2(message: Message, state: FSMContext):
    await message.answer("You selected sub-option 1.2")


@router.message(MenuStates.option1, F.text == "Back")
async def exit_option1(message: Message, state: FSMContext, bot: Bot):
    """Return to main menu from Option 1 submenu."""
    data = await state.get_data()
    sub_msg_id = data.get("option1_msg_id")
    if sub_msg_id:
        await bot.delete_message(message.chat.id, sub_msg_id)

    await state.set_state(MenuStates.main)

    # rebuild main reply keyboard
    rb = ReplyKeyboardBuilder()
    rb.button(text="Option 1")
    rb.button(text="Option 2")
    rb.adjust(2)
    main_reply_kb = rb.as_markup(resize_keyboard=True)

    main_inline_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Option 3", callback_data="opt3"),
                InlineKeyboardButton(text="Option 4", callback_data="opt4"),
            ]
        ]
    )

    reply_msg = await message.answer(
        "Back to main menu. Use the keyboard for Option 1/2.",
        reply_markup=main_reply_kb,
    )
    inline_msg = await message.answer(
        "Select an inline option:", reply_markup=main_inline_kb
    )
    await state.update_data(inline_msg_id=inline_msg.message_id)

    await message.delete()
    await reply_msg.delete()
