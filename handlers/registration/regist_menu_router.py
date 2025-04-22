"""
Menu «Sou paciente / Sou cuidador» – apenas para visitantes identificados.
"""

import logging
from aiogram import Router, types, F
from handlers.common.keyboards import regist_menu_kb
from aiogram.filters import Text
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)
router = Router(name="regist_menu")


@router.message(F.text == "📝 Registar‑me")
async def ask_role(msg: types.Message, state: FSMContext) -> None:
    await state.set_state("awaiting_regist_choice")
    await msg.answer(
        "Como se pretende registar?",
        reply_markup=regist_menu_kb()
    )


@router.callback_query(Text("regist_back"))
async def back_to_visitor(cb: types.CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await cb.message.delete()
