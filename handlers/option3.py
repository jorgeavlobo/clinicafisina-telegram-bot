from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states.menu_states import MenuStates

router = Router()


@router.callback_query(MenuStates.main, F.data == "opt3")
async def enter_option3(callback: CallbackQuery, state: FSMContext):
    """Enter Option 3 submenu via inline button."""
    await state.set_state(MenuStates.option3)

    ib = InlineKeyboardBuilder()
    ib.button(text="Sub-option 3.1", callback_data="3.1")
    ib.button(text="Sub-option 3.2", callback_data="3.2")
    ib.button(text="Back", callback_data="back")
    ib.adjust(2, 1)                           # 2 buttons first row, 1 second
    sub_inline_kb = ib.as_markup()

    await callback.message.edit_text(
        "Option 3 menu: choose a sub‑option or go back.",
        reply_markup=sub_inline_kb,
    )
    await callback.answer()


@router.callback_query(MenuStates.option3, F.data == "3.1")
async def option3_sub1(callback: CallbackQuery):
    await callback.message.answer("You selected sub-option 3.1")
    await callback.answer()


@router.callback_query(MenuStates.option3, F.data == "3.2")
async def option3_sub2(callback: CallbackQuery):
    await callback.message.answer("You selected sub-option 3.2")
    await callback.answer()


@router.callback_query(MenuStates.option3, F.data == "back")
async def exit_option3(callback: CallbackQuery, state: FSMContext):
    """Return from Option 3 submenu to main inline menu."""
    await state.set_state(MenuStates.main)

    ib = InlineKeyboardBuilder()
    ib.button(text="Option 3", callback_data="opt3")
    ib.button(text="Option 4", callback_data="opt4")
    ib.adjust(2)
    main_inline_kb = ib.as_markup()

    await callback.message.edit_text(
        "Select an inline option:", reply_markup=main_inline_kb
    )
    await callback.answer()
