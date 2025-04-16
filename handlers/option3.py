from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from states.menu_states import MenuStates

router = Router()

# Handler for clicking "Option 3" (inline button) from the main menu.
@router.callback_query(MenuStates.main, F.data == "opt3")
async def enter_option3(callback: CallbackQuery, state: FSMContext):
    """
    Enters the Option 3 submenu via inline button. Edits the main menu inline message to show Option 3 sub-options.
    """
    # Set FSM state to Option 3 submenu
    await state.set_state(MenuStates.option3)

    # Build a new inline keyboard for Option 3's sub-options and a back button
    sub_inline_kb = InlineKeyboardMarkup()
    sub_inline_kb.add(
        InlineKeyboardButton(text="Sub-option 3.1", callback_data="3.1"),
        InlineKeyboardButton(text="Sub-option 3.2", callback_data="3.2")
    )
    sub_inline_kb.add(InlineKeyboardButton(text="Back", callback_data="back"))

    # Edit the existing inline menu message to display Option 3 submenu options
    await callback.message.edit_text(
        "Option 3 menu: choose a sub-option or go back.",
        reply_markup=sub_inline_kb
    )
    # Acknowledge the callback (this removes the "loading" indicator on the button)
    await callback.answer()
    # Note: The reply keyboard (Options 1 & 2) is still available to the user, but pressing those while in this state will have no effect unless they go back.

# Handler for selecting sub-option 3.1 (inline button)
@router.callback_query(MenuStates.option3, F.data == "3.1")
async def option3_sub1(callback: CallbackQuery):
    """Handles selection of sub-option 3.1 in Option 3 submenu."""
    # Send a confirmation message to the chat
    await callback.message.answer("You selected sub-option 3.1")
    # Acknowledge the callback (no popup message)
    await callback.answer()
    # (State remains MenuStates.option3 so user can select another option or back.)

# Handler for selecting sub-option 3.2
@router.callback_query(MenuStates.option3, F.data == "3.2")
async def option3_sub2(callback: CallbackQuery):
    await callback.message.answer("You selected sub-option 3.2")
    await callback.answer()

# Handler for "Back" button in Option 3 submenu (inline)
@router.callback_query(MenuStates.option3, F.data == "back")
async def exit_option3(callback: CallbackQuery, state: FSMContext):
    """
    Exits the Option 3 submenu and returns to the main menu (inline) by editing the message back.
    """
    # Set state back to main menu
    await state.set_state(MenuStates.main)

    # Rebuild the main menu inline keyboard for Options 3 and 4
    main_inline_kb = InlineKeyboardMarkup()
    main_inline_kb.add(
        InlineKeyboardButton(text="Option 3", callback_data="opt3"),
        InlineKeyboardButton(text="Option 4", callback_data="opt4")
    )

    # Edit the message back to the main menu inline options
    await callback.message.edit_text(
        "Select an inline option:",
        reply_markup=main_inline_kb
    )
    await callback.answer()
    # (The reply keyboard with Options 1 and 2 is still active from earlier, so the main menu is fully restored.)
