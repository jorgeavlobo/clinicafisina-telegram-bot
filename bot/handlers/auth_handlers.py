"""
Handlers de autenticação (/start + onboarding).

• Se o utilizador já estiver ligado, mostra imediatamente o menu
  (apagando o menu anterior caso exista).
• Se não estiver ligado, inicia o fluxo de onboarding (pedir contacto).
• A mensagem com o próprio comando “/start” é removida para que o chat
  fique limpo – aplica-se em qualquer dos cenários acima.
"""

from aiogram import Router, F, exceptions
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.auth import auth_flow as flow
from bot.states.auth_states import AuthStates
from bot.database.connection import get_pool
from bot.database import queries as q
from bot.menus import show_menu

# ───────────────────────────── router ─────────────────────────────
router = Router(name="auth")

# ───────────────────────────── /start ─────────────────────────────
@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    """
    Trata o /start:

    1. Se já existir ligação → limpa FSM (preservando o id do menu
       anterior, se existir), de seguida mostra o menu principal.
    2. Caso contrário → inicia o fluxo de onboarding (pedir contacto).
    3. Em ambos os casos remove do chat a mensagem “/start” para
       evitar clutter.
    """
    # 3.1  — apaga a própria mensagem /start (ignora erros se, p.ex.,
    #        o bot não tiver permissão para apagar mensagens alheias)
    try:
        await message.delete()
    except exceptions.TelegramBadRequest:
        # sem permissões ou mensagem demasiado antiga – continua
        pass

    pool = await get_pool()
    user = await q.get_user_by_telegram_id(pool, message.from_user.id)

    if user:
        roles = await q.get_user_roles(pool, user["user_id"])

        # ── limpa FSM mas preserva id do último menu ──
        data           = await state.get_data()
        last_menu_id   = data.get("menu_msg_id")
        last_menu_chat = data.get("menu_chat_id")
        await state.clear()

        if last_menu_id and last_menu_chat:
            await state.update_data(
                menu_msg_id  = last_menu_id,
                menu_chat_id = last_menu_chat,
            )

        # show_menu() apagará o menu velho (se ainda existir)
        await show_menu(
            bot     = message.bot,
            chat_id = message.chat.id,
            state   = state,
            roles   = roles,
        )
    else:
        # não ligado → inicia onboarding (pedir contacto)
        await flow.start_onboarding(message, state)

# ───────────────────── contacto partilhado ──────────────────────
@router.message(StateFilter(AuthStates.WAITING_CONTACT), F.contact)
async def contact_handler(message: Message, state: FSMContext):
    await flow.handle_contact(message, state)

# ─────────────────── confirmação ligação (YES/NO) ───────────────
@router.callback_query(StateFilter(AuthStates.CONFIRMING_LINK), F.data == "link_yes")
async def cb_confirm_yes(cb: CallbackQuery, state: FSMContext):
    await flow.confirm_link(cb, state)

@router.callback_query(StateFilter(AuthStates.CONFIRMING_LINK), F.data == "link_no")
async def cb_confirm_no(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("Operação cancelada.")
