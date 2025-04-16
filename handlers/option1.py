from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram import Bot

from states.menu_states import MenuStates

router = Router()

# Handler for selecting "Option 1" from the main menu (reply keyboard).
@router.message(MenuStates.main, F.text == "Option 1")
async def enter_option1(message: Message, state: FSMContext, bot: Bot):
    """
    Transitions to the Option 1 submenu. This will remove the main menu's inline buttons and show Option 1 sub-options.
    """
    # Retrieve the main menu inline message ID and delete that message to hide Options 3 & 4 (inline) when entering Option 1 submenu.
    data = await state.get_data()
    inline_msg_id = data.get("inline_msg_id")
    if inline_msg_id:
        await bot.delete_message(chat_id=message.chat.id, message_id=inline_msg_id)

    # Set FSM state to Option 1 submenu
    await state.set_state(MenuStates.option1)

    # Build reply keyboard for Option 1 submenu: two sub-options and a "Back" button
    sub_reply_kb = ReplyKeyboardMarkup(resize_keyboard=True)
    sub_reply_kb.add(KeyboardButton("Sub-option 1.1"), KeyboardButton("Sub-option 1.2"))
    sub_reply_kb.add(KeyboardButton("Back"))

    # Send a message to user with the Option 1 submenu and new keyboard
    sub_menu_msg = await message.answer(
        "You are now in the Option 1 menu. Select a sub-option or go back.",
        reply_markup=sub_reply_kb
    )

    # Store this submenu message ID to delete it when exiting Option 1 menu (for cleanliness)
    await state.update_data(option1_msg_id=sub_menu_msg.message_id)
    # (We leave the user's "Option 1" message visible; only commands are auto-deleted for cleanliness.)
    
# Handler for sub-option 1.1 selection in Option 1 submenu
@router.message(MenuStates.option1, F.text == "Sub-option 1.1")
async def option1_sub1(message: Message, state: FSMContext):
    """
    Handles the selection of sub-option 1.1 in the Option 1 submenu.
    """
    # Simply acknowledge the selection. In a real bot, you could perform some action here.
    await message.answer("You selected sub-option 1.1")
    # (Remain in MenuStates.option1 so the user can choose another sub-option or go back.)
    
# Handler for sub-option 1.2 selection in Option 1 submenu
@router.message(MenuStates.option1, F.text == "Sub-option 1.2")
async def option1_sub2(message: Message, state: FSMContext):
    """
    Handles the selection of sub-option 1.2 in the Option 1 submenu.
    """
    await message.answer("You selected sub-option 1.2")
    # (Remain in MenuStates.option1.)
    
# Handler for the "Back" button in Option 1 submenu to return to main menu
@router.message(MenuStates.option1, F.text == "Back")
async def exit_option1(message: Message, state: FSMContext, bot: Bot):
    """
    Exits Option 1 submenu and returns to the main menu.
    """
    # Delete the Option 1 submenu message to clean up the chat
    data = await state.get_data()
    sub_msg_id = data.get("option1_msg_id")
    if sub_msg_id:
        await bot.delete_message(chat_id=message.chat.id, message_id=sub_msg_id)

    # Set state back to main menu
    await state.set_state(MenuStates.main)

    # Re-create the main menu keyboards (reply and inline)
    main_reply_kb = ReplyKeyboardMarkup(resize_keyboard=True)
    main_reply_kb.add(KeyboardButton("Option 1"), KeyboardButton("Option 2"))
    main_inline_kb = InlineKeyboardMarkup()
    main_inline_kb.add(
        InlineKeyboardButton(text="Option 3", callback_data="opt3"),
        InlineKeyboardButton(text="Option 4", callback_data="opt4")
    )

    # Send the main menu again
    reply_msg = await message.answer(
        "Back to main menu. Use the keyboard for Option 1/2.",
        reply_markup=main_reply_kb
    )
    inline_msg = await message.answer(
        "Select an inline option:",
        reply_markup=main_inline_kb
    )
    # Update stored inline message ID for future use (the main menu inline message is new)
    await state.update_data(inline_msg_id=inline_msg.message_id)

    # Clean up the user's "Back" message and the temporary reply_msg to keep UI clean
    await message.delete()
    await reply_msg.delete()
