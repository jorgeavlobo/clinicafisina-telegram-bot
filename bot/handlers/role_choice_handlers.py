# bot/handlers/role_choice_handlers.py
"""
Handlers para a seleção de perfil (role) após login.

Este módulo define o handler de CallbackQuery para a escolha de um perfil ativo quando
o utilizador tem múltiplos roles. Após o utilizador selecionar um role, este é armazenado
como `active_role` no FSM e o menu correspondente é exibido. Qualquer menu de seleção 
anterior é removido do chat.
"""
from aiogram import Router, types, F, exceptions
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.states.menu_states import MenuStates
from bot.states.admin_menu_states import AdminMenuStates

router = Router(name="role_choice")

@router.callback_query(StateFilter(MenuStates.WAIT_ROLE_CHOICE), F.data.startswith("role:"))
async def handle_role_choice(callback: CallbackQuery, state: FSMContext) -> None:
    """
    Handler chamado quando o utilizador escolhe um role no menu de seleção de perfis.
    Define o role escolhido como ativo, limpa o estado de seleção de perfil e apresenta o menu correspondente.
    """
    # Extrair o código/nome do role do callback_data (após "role:")
    role_code = callback.data.split(":", 1)[1]
    # Obter a lista de roles do utilizador armazenada no FSM (definida durante o /start)
    data = await state.get_data()
    roles_list = data.get("roles", [])
    # Validar que o role selecionado pertence de facto aos roles do utilizador
    if role_code.lower() not in [r.lower() for r in roles_list]:
        # Se o role não estiver autorizado, informar o utilizador e ignorar
        await callback.answer("Perfil inválido ou não autorizado.", show_alert=True)
        return

    # Armazena o role escolhido como ativo no FSM antes de prosseguir
    await state.update_data(active_role=role_code)
    # Sair do estado de seleção de perfil (encerra MenuStates.WAIT_ROLE_CHOICE, mantendo os dados)
    await state.set_state(None)

    # Remover a mensagem de seleção de perfil agora que já há escolha
    try:
        await callback.message.delete()
    except exceptions.TelegramBadRequest:
        # Ignorar erro se a mensagem já não existir ou não puder ser apagada
        pass

    # Determinar se o role escolhido requer definir um estado específico de menu
    if role_code == "administrator":
        # Utilizador escolheu perfil de Administrador – definir estado MAIN do menu admin
        await state.set_state(AdminMenuStates.MAIN)
        # Construir o menu principal do Administrador (teclado inline)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📅 Agenda", callback_data="admin:agenda")],
                [InlineKeyboardButton(text="👥 Utilizadores", callback_data="admin:users")],
                [InlineKeyboardButton(text="✉️ Mensagens", callback_data="admin:messages")]
            ]
        )
        # Enviar mensagem do menu de Administrador
        menu_msg = await callback.message.answer(
            "Menu Administrador – selecione uma opção:",
            reply_markup=keyboard
        )
    elif role_code == "patient":
        # Perfil de Paciente – permanece no estado padrão (nenhum estado específico definido)
        # Construir menu principal de Paciente (exemplo de opções)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📆 Minhas Consultas", callback_data="patient:appointments")],
                [InlineKeyboardButton(text="💊 Terapia", callback_data="patient:therapy")]
            ]
        )
        menu_msg = await callback.message.answer(
            "Menu Paciente – selecione uma opção:",
            reply_markup=keyboard
        )
    elif role_code == "caregiver":
        # Perfil de Cuidador – permanece no estado padrão
        # Construir menu principal de Cuidador (exemplo de opções)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="👤 Paciente Assistido", callback_data="caregiver:patient_info")],
                [InlineKeyboardButton(text="💬 Mensagens", callback_data="caregiver:messages")]
            ]
        )
        menu_msg = await callback.message.answer(
            "Menu Cuidador – selecione uma opção:",
            reply_markup=keyboard
        )
    else:
        # Outros perfis (fallback): simplesmente confirmar a ativação do perfil
        menu_msg = await callback.message.answer(
            f"Perfil *{role_code}* ativado.",
            parse_mode="Markdown"
        )
    # Armazenar o novo menu enviado como menu ativo (menu_msg_id e menu_chat_id) para callbacks futuros
    await state.update_data(menu_msg_id=menu_msg.message_id, menu_chat_id=menu_msg.chat.id)
    # A partir deste ponto, o menu apropriado foi exibido e o utilizador pode interagir com ele.
