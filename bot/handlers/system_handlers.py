# bot/handlers/system_handlers.py
"""
Global handlers for system-level interactions (not specific to a single user role).
Includes handlers for choosing active role when a user has multiple roles.
"""
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.filters import StateFilter

from bot.menus import show_menu
from bot.states.menu_states import MenuStates

router = Router(name="system")

# Handler para escolha de perfil (role) quando o utilizador tem vários roles
@router.callback_query(StateFilter(MenuStates.WAIT_ROLE_CHOICE), F.data.startswith("role:"))
async def choose_role_callback(cb: CallbackQuery, state: FSMContext):
    """
    CallbackQuery handler para selecionar o perfil de utilizador quando há múltiplos roles disponíveis.
    Ao selecionar, exibe o menu principal do role escolhido.
    """
    await cb.answer()  # reconhecimento rápido da seleção
    # Determinar o role escolhido a partir da callback data (formato "role:<nome_role>")
    role_chosen = cb.data.split(":", 1)[1]
    # Obter lista de roles disponíveis armazenada (se necessário para referência ou validação)
    data = await state.get_data()
    roles = data.get("roles", [])
    # Exibir o menu principal correspondente ao perfil escolhido
    # (A função show_menu irá definir o estado FSM apropriado e a mensagem de menu ativa)
    await show_menu(cb.bot, cb.from_user.id, state, roles, requested=role_chosen)
