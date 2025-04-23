from aiogram import Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, Contact
from bot.states.auth_states import AuthStates
from bot.database import queries as q
from bot.database.connection import get_pool


async def start_onboarding(message: Message, state: FSMContext) -> None:
    """/start quando ainda não sabemos quem é o utilizador."""
    await state.set_state(AuthStates.WAITING_CONTACT)
    await message.answer(
        "Para continuar, por favor partilhe o seu número de telemóvel:",
        reply_markup=message.bot.reply_keyboard([[{"text": "📱 Enviar contacto", "request_contact": True}]]),
    )


async def handle_contact(message: Message, state: FSMContext) -> None:
    """Recebe o contacto e procura na BD."""
    phone: Contact = message.contact
    pool = await get_pool()
    user = await q.get_user_by_phone(pool, phone.phone_number)

    if user:
        # guarda info no state para a próxima etapa
        await state.update_data(db_user_id=str(user["user_id"]))
        await state.set_state(AuthStates.CONFIRMING_LINK)
        await message.answer(
            f"Encontrámos um perfil para {user['first_name']} {user['last_name']}. "
            "É você?",
            reply_markup=message.bot.inline_keyboard(
                [[{"text": "Sim ✅", "callback_data": "link_yes"},
                  {"text": "Não ❌", "callback_data": "link_no"}]]
            ),
        )
    else:
        await state.clear()
        await message.answer(
            "Não encontramos esse número na nossa base. "
            "Iremos contactá-lo assim que estiver registado."
        )


async def confirm_link(cb: CallbackQuery, state: FSMContext) -> None:
    """Callback 'Sim' – faz o link tele_id → utilizador."""
    data = await state.get_data()
    user_id = data["db_user_id"]
    pool = await get_pool()
    await q.link_telegram_id(pool, user_id, cb.from_user.id)

    roles = await q.get_user_roles(pool, user_id)
    await state.clear()

    # mostra menu conforme o 1.º role
    role = roles[0] if roles else "unregistered"
    await cb.message.edit_text("Ligação concluída! 🎉")
    # TODO: chamar função show_menu(role, cb.message)
