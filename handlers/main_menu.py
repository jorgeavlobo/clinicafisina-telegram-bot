from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder

from states.menu_states import MenuStates

router = Router()

# Handler for the /start command. This will initialize the FSM state and show the main menu.
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """
    Handles /start command: resets state, sets main menu state, and displays the main menu.
    """
    # Clear any existing state and switch to the main menu state
    await state.clear()  # Clear any previous FSM data/state
    await state.set_state(MenuStates.main)

    # Build a custom reply keyboard for Options 1 and 2 (main menu)
    rb = ReplyKeyboardBuilder()
    rb.button(text="Option 1")
    rb.button(text="Option 2")
    main_reply_kb = rb.as_markup(resize_keyboard=True)
    main_reply_kb.add(KeyboardButton("Option 1"), KeyboardButton("Option 2"))

    # Build an inline keyboard for Options 3 and 4 (main menu)
    main_inline_kb = InlineKeyboardMarkup()
    main_inline_kb.add(
        InlineKeyboardButton(text="Option 3", callback_data="opt3"),
        InlineKeyboardButton(text="Option 4", callback_data="opt4")
    )

    # Send the main menu to the user.
    # We send two messages: one to display the reply keyboard (Options 1 & 2) and one for the inline options (3 & 4).
    reply_msg = await message.answer(
        "Main menu loaded. Use the keyboard for Option 1 or 2.",
        reply_markup=main_reply_kb
    )
    inline_msg = await message.answer(
        "Select an inline option:",
        reply_markup=main_inline_kb
    )

    # Store the inline message ID in FSM data for later (so we can edit or delete it when navigating).
    await state.update_data(inline_msg_id=inline_msg.message_id)

    # Delete the user's /start command message and the bot's first reply to keep the chat UI clean
    await message.delete()
    await reply_msg.delete()
