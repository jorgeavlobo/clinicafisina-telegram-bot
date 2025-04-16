from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from states.menu_states import MenuStates

router = Router()

# Handler for clicking "Option 4" (inline button) in the main menu.
@router.callback_query(MenuStates.main, F.data == "opt4")
async def enter_option4(callback: CallbackQuery, state: FSMContext):
    """Enters Option 4 submenu by editing the inline message to show Option 4 sub-options."""
    await state.set_state(MenuStates.option4)
    sub_inline_kb = InlineKeyboardMarkup()
    sub_inline_kb.add(
        InlineKeyboardButton(text="Sub-option 4.1", callback_data="4.1"),
        InlineKeyboardButton(text="Sub-option 4.2", callback_data="4.2")
    )
    sub_inline_kb.add(InlineKeyboardButton(text="Back", callback_data="back"))
    await callback.message.edit_text(
        "Option 4 menu: choose a sub-option or go back.",
        reply_markup=sub_inline_kb
    )
    await callback.answer()

# Handler for sub-option 4.1 selection
@router.callback_query(MenuStates.option4, F.data == "4.1")
async def option4_sub1(callback: CallbackQuery):
    await callback.message.answer("You selected sub-option 4.1")
    await callback.answer()

# Handler for sub-option 4.2 selection
@router.callback_query(MenuStates.option4, F.data == "4.2")
async def option4_sub2(callback: CallbackQuery):
    await callback.message.answer("You selected sub-option 4.2")
    await callback.answer()

# Handler for "Back" in Option 4 submenu
@router.callback_query(MenuStates.option4, F.data == "back")
async def exit_option4(callback: CallbackQuery, state: FSMContext):
    """Exits Option 4 submenu and returns to main menu (inline)."""
    await state.set_state(MenuStates.main)
    main_inline_kb = InlineKeyboardMarkup()
    main_inline_kb.add(
        InlineKeyboardButton(text="Option 3", callback_data="opt3"),
        InlineKeyboardButton(text="Option 4", callback_data="opt4")
    )
    await callback.message.edit_text(
        "Select an inline option:",
        reply_markup=main_inline_kb
    )
    await callback.answer()
    # (Reply keyboard with Options 1/2 is still available, no need to resend it.)
