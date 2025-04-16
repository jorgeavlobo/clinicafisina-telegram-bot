from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram import Bot

from states.menu_states import MenuStates

router = Router()

# Handler for selecting "Option 2" from the main menu (reply keyboard).
@router.message(MenuStates.main, F.text == "Option 2")
async def enter_option2(message: Message, state: FSMContext, bot: Bot):
    """
    Transitions to the Option 2 submenu. Removes main menu inline buttons and shows Option 2 sub-options.
    """
    # Remove main menu inline message (Options 3 & 4) now that we enter Option 2
    data = await state.get_data()
    inline_msg_id = data.get("inline_msg_id")
    if inline_msg_id:
        await bot.delete_message(chat_id=message.chat.id, message_id=inline_msg_id)

    # Set FSM state to Option 2 submenu
    await state.set_state(MenuStates.option2)

    # Build reply keyboard for Option 2 submenu
    sub_reply_kb = ReplyKeyboardMarkup(resize_keyboard=True)
    sub_reply_kb.add(KeyboardButton("Sub-option 2.1"), KeyboardButton("Sub-option 2.2"))
    sub_reply_kb.add(KeyboardButton("Back"))

    # Send submenu message with new keyboard
    sub_menu_msg = await message.answer(
        "You are now in the Option 2 menu. Select a sub-option or go back.",
        reply_markup=sub_reply_kb
    )
    await state.update_data(option2_msg_id=sub_menu_msg.message_id)
    
# Handler for sub-option 2.1 selection
@router.message(MenuStates.option2, F.text == "Sub-option 2.1")
async def option2_sub1(message: Message, state: FSMContext):
    await message.answer("You selected sub-option 2.1")
    
# Handler for sub-option 2.2 selection
@router.message(MenuStates.option2, F.text == "Sub-option 2.2")
async def option2_sub2(message: Message, state: FSMContext):
    await message.answer("You selected sub-option 2.2")

# Handler for "Back" in Option 2 submenu
@router.message(MenuStates.option2, F.text == "Back")
async def exit_option2(message: Message, state: FSMContext, bot: Bot):
    # Delete the Option 2 submenu message
    data = await state.get_data()
    sub_msg_id = data.get("option2_msg_id")
    if sub_msg_id:
        await bot.delete_message(chat_id=message.chat.id, message_id=sub_msg_id)

    await state.set_state(MenuStates.main)  # back to main menu state

    # Recreate main menu keyboards
    main_reply_kb = ReplyKeyboardMarkup(resize_keyboard=True)
    main_reply_kb.add(KeyboardButton("Option 1"), KeyboardButton("Option 2"))
    main_inline_kb = InlineKeyboardMarkup()
    main_inline_kb.add(
        InlineKeyboardButton(text="Option 3", callback_data="opt3"),
        InlineKeyboardButton(text="Option 4", callback_data="opt4")
    )
    # Send main menu again
    reply_msg = await message.answer("Back to main menu. Use the keyboard for Option 1/2.", reply_markup=main_reply_kb)
    inline_msg = await message.answer("Select an inline option:", reply_markup=main_inline_kb)
    await state.update_data(inline_msg_id=inline_msg.message_id)
    # Remove the user's "Back" message and the temporary reply_msg for cleanliness
    await message.delete()
    await reply_msg.delete()
