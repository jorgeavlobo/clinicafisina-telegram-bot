# bot/handlers/auth_handlers.py
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
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.auth import auth_flow as flow
from bot.states.auth_states import AuthStates
from bot.states.menu_states import MenuStates
from bot.states.admin_menu_states import AdminMenuStates
from bot.database.connection import get_pool
from bot.database import queries as q
from bot.menus import show_menu
import asyncio

# ───────────────────────────── router ─────────────────────────────
router = Router(name="auth")

# ───────────────────────────── /start ─────────────────────────────
@router.message(CommandStart())
async def start(message: Message, state: FSMContext) -> None:
    """
    Trata o /start:

    1. Se já existir ligação → limpa FSM (removendo menus anteriores se existirem),
       de seguida pede escolha de perfil (se múltiplos) ou mostra o menu principal diretamente.
    2. Caso contrário → inicia o fluxo de onboarding (pedir contacto).
    3. Em ambos os casos remove do chat a mensagem “/start” para evitar clutter.
    """
    # 3.1 — apaga a própria mensagem /start (ignora erros se, p.ex.,
    #       o bot não tiver permissão para apagar mensagens alheias)
    try:
        await message.delete()
    except exceptions.TelegramBadRequest:
        # Sem permissões ou mensagem demasiado antiga – continua
        pass

    pool = await get_pool()
    user = await q.get_user_by_telegram_id(pool, message.from_user.id)

    if user:
        # Utilizador encontrado na BD, obter os roles associados
        roles = await q.get_user_roles(pool, user["user_id"])
        roles = [r.lower() for r in roles] if roles else []  # garantir roles em minúsculas

        # ── Limpa FSM e remove menu anterior (se existir) ──
        data = await state.get_data()
        last_menu_id = data.get("menu_msg_id")
        last_menu_chat = data.get("menu_chat_id")
        await state.clear()
        if last_menu_id and last_menu_chat:
            # Apagar o menu antigo para evitar botões obsoletos
            try:
                await message.bot.delete_message(last_menu_chat, last_menu_id)
            except exceptions.TelegramBadRequest:
                # Não foi possível apagar (p.ex. mensagem antiga ou falta de permissões)
                pass

        # ── Verifica roles do utilizador e atua conforme ──
        if not roles:
            # Utilizador não tem nenhum perfil atribuído
            await message.answer(
                "Ainda não tem permissões atribuídas. "
                "Contacte a receção/administração."
            )
            return

        elif len(roles) > 1:
            # Utilizador com vários roles: pedir para escolher um perfil ativo
            await state.set_state(MenuStates.WAIT_ROLE_CHOICE)    # define estado de espera da escolha
            await state.update_data(roles=roles)                 # guarda lista de roles no FSM para referência

            # Construir teclado inline com as opções de perfil
            buttons = []
            for role in roles:
                role_display = role.capitalize()  # Nome do role para exibição (pode ajustar para PT se necessário)
                buttons.append([InlineKeyboardButton(text=role_display, callback_data=f"role:{role}")])
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

            # Enviar mensagem para o utilizador selecionar o perfil
            selection_msg = await message.answer(
                "Por favor, escolha o perfil com que pretende operar:",
                reply_markup=keyboard
            )
            # Armazenar o ID da mensagem de seleção de perfil como menu ativo (para callbacks válidos)
            await state.update_data(menu_msg_id=selection_msg.message_id,
                                    menu_chat_id=selection_msg.chat.id)

            # Agendar remoção automática do menu de seleção após 60 segundos de inatividade
            async def remove_role_selection_after_timeout(bot, chat_id, message_id, fsm_state: FSMContext):
                await asyncio.sleep(60)
                # Se ainda não houve escolha de perfil (estado permanece WAIT_ROLE_CHOICE)
                if await fsm_state.get_state() == MenuStates.WAIT_ROLE_CHOICE.state:
                    # Apaga o menu de seleção expirado
                    try:
                        await bot.delete_message(chat_id, message_id)
                    except exceptions.TelegramBadRequest:
                        pass
                    # Notifica o utilizador que o menu foi fechado por inatividade (mensagem temporária)
                    try:
                        notice = await bot.send_message(
                            chat_id,
                            "⌛️ Seleção de perfil expirada por inatividade."
                        )
                        await asyncio.sleep(60)
                        await notice.delete()
                    except exceptions.TelegramBadRequest:
                        pass

            # Inicia tarefa em background para remover menu após timeout
            asyncio.create_task(remove_role_selection_after_timeout(message.bot,
                                                                     message.chat.id,
                                                                     selection_msg.message_id,
                                                                     state))

        else:
            # Utilizador com apenas um role: define perfil ativo e mostra menu correspondente
            active_role = roles[0]
            await state.update_data(active_role=active_role, roles=roles)  # guarda o role ativo no FSM
            if active_role == "administrator":
                # Define estado inicial do menu de administrador, se aplicável
                await state.set_state(AdminMenuStates.MAIN)
            # Mostra o menu principal do role (função show_menu cuidará do conteúdo específico)
            await show_menu(
                bot=message.bot,
                chat_id=message.chat.id,
                state=state,
                roles=roles
            )
    else:
        # Utilizador não ligado → inicia onboarding (pedir contacto)
        await flow.start_onboarding(message, state)
