# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem ≥ 2 papéis.

• Mostra inline-keyboard (timeout generico em bot/menus/common.py)
• Edita a mensagem existente para transições suaves
• Mantém apenas uma mensagem de menu ativa
"""

from __future__ import annotations

from typing import Iterable

from aiogram import Router, types, exceptions, F
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus                     import show_menu
from bot.menus.common              import start_menu_timeout
from bot.states.menu_states        import MenuStates
from bot.states.admin_menu_states  import AdminMenuStates

router = Router(name="role_choice")

# Dicionário para traduzir os papéis para português
_LABELS_PT = {
    "patient":         "paciente",
    "caregiver":       "cuidador",
    "physiotherapist": "fisioterapeuta",
    "accountant":      "contabilista",
    "administrator":   "administrador",
}

def _label(role: str) -> str:
    """Retorna o rótulo traduzido do papel."""
    return _LABELS_PT.get(role.lower(), role.capitalize())

# ───────────────────────── ask_role ─────────────────────────
async def ask_role(
    bot: types.Bot,  # Parâmetro necessário para interagir com o Telegram
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],  # Lista de papéis disponíveis para o usuário
) -> None:
    """Envia ou edita o selector de perfis, mantendo apenas uma mensagem ativa."""
    # Cria o teclado inline com os papéis disponíveis
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(text=_label(r), callback_data=f"role:{r.lower()}")
        ] for r in roles]
    )
    text = "*Escolha o perfil:*"  # Texto em Markdown válido

    # Recupera os dados do estado para verificar se já existe uma mensagem
    data = await state.get_data()
    menu_msg_id = data.get("menu_msg_id")
    menu_chat_id = data.get("menu_chat_id")

    if menu_msg_id and menu_chat_id:
        try:
            # Tenta editar a mensagem existente
            await bot.edit_message_text(
                chat_id=menu_chat_id,
                message_id=menu_msg_id,
                text=text,
                reply_markup=kbd,
                parse_mode="Markdown",
            )
            print(f"Mensagem editada: ID {menu_msg_id}, Chat {menu_chat_id}")
        except exceptions.TelegramBadRequest as e:
            print(f"Falha ao editar mensagem: {e}")
            # Fallback: envia uma nova mensagem se a edição falhar
            msg = await bot.send_message(
                chat_id,
                text,
                reply_markup=kbd,
                parse_mode="Markdown",
            )
            await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)
            print(f"Nova mensagem enviada: ID {msg.message_id}, Chat {msg.chat.id}")
    else:
        # Envia uma nova mensagem se não houver uma anterior
        msg = await bot.send_message(
            chat_id,
            text,
            reply_markup=kbd,
            parse_mode="Markdown",
        )
        await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)
        print(f"Menu enviado: ID {msg.message_id}, Chat {msg.chat.id}")

    # Define o estado para aguardar a escolha do papel
    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(roles=[r.lower() for r in roles])
    start_menu_timeout(bot, msg, state)  # Inicia o timeout do menu

# ─────────────────── callback «role:…» ────────────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    F.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext):
    role = cb.data.split(":", 1)[1].lower()  # Extrai o papel selecionado
    await state.update_data(active_role=role)  # Atualiza o estado com o papel
    
    # Define o estado consoante o papel
    if role == "administrator":
        await state.set_state(AdminMenuStates.MAIN)
    else:
        await state.set_state(None)
    
    # Chama show_menu com os IDs para editar a mensagem existente
    await show_menu(
        cb.bot,
        cb.from_user.id,
        state,
        [role],
        edit_message_id=cb.message.message_id,  # ID da mensagem atual
        edit_chat_id=cb.message.chat.id,        # ID do chat atual
    )
    await cb.answer(f"Perfil {role} selecionado!")

    await cb.answer(f"Perfil {_label(role)} seleccionado!")
