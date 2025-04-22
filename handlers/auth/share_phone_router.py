"""
Recebe o contacto partilhado e tenta encontrar o utilizador pelo phone_number.
"""

import logging
from aiogram import Router, types, F
from shared.dal import link_telegram_by_phone, get_roles_for_user
from handlers.common.keyboards import role_choice_kb, visitor_main_kb

logger = logging.getLogger(__name__)
router = Router(name="auth_share_phone")


@router.message(F.contact)
async def handle_contact(msg: types.Message) -> None:
    phone = msg.contact.phone_number.lstrip("+")  # normaliza
    user = await link_telegram_by_phone(phone, msg.from_user.id)

    if not user:
        # Número não existe → visitante identificado mas não registado
        await msg.answer(
            "🙁 Ainda não encontramos esse nº na nossa base de dados.\n"
            "Pode contactar a clínica para se registar.",
            reply_markup=visitor_main_kb()
        )
        return

    # Encontrado → mostrar menu(s) consoante role
    roles = await get_roles_for_user(user["user_id"])
    if len(roles) == 1:
        await router.emit(
            types.Message(chat=msg.chat, from_user=msg.from_user, text=f"/menu_{roles[0]}"),
            msg.bot
        )
    else:
        await msg.answer(
            "Perfil associado encontrado. Qual quer utilizar agora?",
            reply_markup=role_choice_kb(roles)
        )
