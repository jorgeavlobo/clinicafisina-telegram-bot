"""
/start – identifica o utilizador ou inicia onboarding.
"""

import logging
from aiogram import Router, types, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from shared.dal import get_user_by_telegram_id, link_telegram_to_user
from handlers.common.keyboards import share_phone_kb, role_choice_kb

logger = logging.getLogger(__name__)
router = Router(name="auth_start")


@router.message(CommandStart())
async def cmd_start(msg: types.Message, state: FSMContext) -> None:
    """Processa /start:
       1. vê se já temos telegram_user_id na BD
       2. senão, pede nº de telefone
    """
    await state.clear()

    user = await get_user_by_telegram_id(msg.from_user.id)
    if user:
        # Já registado → mostrar escolha de role (se >1) ou menu de role único
        roles = user["roles"]                           # ex.: ["patient"] ou ["patient","caregiver"]
        if len(roles) == 1:
            await router.emit(
                types.Message(chat=msg.chat, from_user=msg.from_user, text=f"/menu_{roles[0]}"),
                msg.bot
            )
        else:
            await msg.answer(
                "Que perfil pretende utilizar no momento?",
                reply_markup=role_choice_kb(roles)
            )
        return

    # Não encontrado → onboarding
    await msg.answer(
        "👋 Bem‑vindo à Clínica Fisina!\n"
        "Para o reconhecer preciso que partilhe o seu nº de telemóvel.",
        reply_markup=share_phone_kb()
    )
