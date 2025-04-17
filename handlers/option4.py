from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states.menu_states import MenuStates

router = Router()


@router.callback_query(MenuStates.main, F.data == "opt4")
async def enter_option4(callback: CallbackQuery, state: FSMContext):
    """Enter Option 4 submenu via inline button."""
    await state.set_state(MenuStates.option4)

    ib = InlineKeyboardBuilder()
    ib.button(text="Sub-option 4.1", callback_data="4.1")
    ib.button(text="Sub-option 4.2", callback_data="4.2")
    ib.button(text="Back", callback_data="back")
    ib.adjust(2, 1)
    sub_inline_kb = ib.as_markup()

    await callback.message.edit_text(
        "Option 4 menu: choose a sub‑option or go back.",
        reply_markup=sub_inline_kb,
    )
    await callback.answer()


@router.callback_query(MenuStates.option4, F.data == "4.1")
async def option4_sub1(callback: CallbackQuery):
    await callback.message.answer("You selected sub-option 4.1")
    await callback.answer()


@router.callback_query(MenuStates.option4, F.data == "4.2")
async def option4_sub2(callback: CallbackQuery):
    await callback.message.answer("You selected sub-option 4.2")
    await callback.answer()


@router.callback_query(MenuStates.option4, F.data == "back")
async def exit_option4(callback: CallbackQuery, state: FSMContext):
    """Return from Option 4 submenu to main inline menu."""
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
