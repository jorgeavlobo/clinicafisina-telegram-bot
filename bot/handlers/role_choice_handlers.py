# bot/handlers/role_choice_handlers.py
from __future__ import annotations
import asyncio
import logging
from typing import Iterable

from aiogram import Router, types, exceptions
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus import show_menu
from bot.menus.common import start_menu_timeout
from bot.config import MESSAGE_TIMEOUT
from bot.states.menu_states import MenuStates
from bot.states.admin_menu_states import AdminMenuStates

router = Router(name="role_choice")

_LABELS_PT = {
    "patient": "🧑🏼‍🦯 Paciente",
    "caregiver": "🤝🏼 Cuidador",
    "physiotherapist": "👩🏼‍⚕️ Fisioterapeuta",
    "accountant": "📊 Contabilista",
    "administrator": "👨🏼‍💼 Administrador",
}
def _label(role: str) -> str: return _LABELS_PT.get(role.lower(), role.capitalize())


# ───────────────────────── ask_role ─────────────────────────
async def ask_role(bot: types.Bot, chat_id: int, state: FSMContext, roles: Iterable[str]) -> None:
    logging.debug(f"ask_role chamado: chat_id={chat_id}, roles={roles}")
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=_label(r), callback_data=f"role:{r.lower()}")]
            for r in roles
        ]
    )
    try:
        msg = await bot.send_message(chat_id, "🔰 *Escolha o perfil:*", reply_markup=kbd, parse_mode="Markdown")
        logging.info(f"Menu de seleção de perfil enviado: chat_id={chat_id}, msg_id={msg.message_id}")
    except exceptions.TelegramBadRequest as e:
        logging.error(f"Falha ao enviar menu de seleção de perfil: {e}")
        return

    # Verifica se há um menu antigo no estado
    data = await state.get_data()
    old_menu_id = data.get("menu_msg_id")
    if old_menu_id:
        logging.warning(f"Menu antigo detectado (ID: {old_menu_id}). Tentando limpar.")
        try:
            await bot.delete_message(chat_id, old_menu_id)
            logging.info(f"Menu antigo {old_menu_id} apagado.")
        except exceptions.TelegramBadRequest:
            logging.warning(f"Falha ao apagar menu antigo {old_menu_id}.")

    try:
        await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
        await state.update_data(
            roles=[r.lower() for r in roles],
            menu_msg_id=msg.message_id,
            menu_chat_id=msg.chat.id,
        )
        logging.debug(f"Estado atualizado: state={MenuStates.WAIT_ROLE_CHOICE}, menu_msg_id={msg.message_id}, menu_chat_id={msg.chat.id}")
        start_menu_timeout(bot, msg, state)
    except Exception as e:
        logging.error(f"Erro ao atualizar estado ou iniciar timeout: {e}")


# ─────────────────── callback “role:…” ───────────────────
@router.callback_query(StateFilter(MenuStates.WAIT_ROLE_CHOICE),
                       lambda c: c.data and c.data.startswith("role:"))
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    logging.debug(f"choose_role chamado: callback_data={cb.data}, chat_id={cb.message.chat.id}")
    
    # Verifica o estado atual
    current_state = await state.get_state()
    if current_state != MenuStates.WAIT_ROLE_CHOICE:
        logging.warning(f"Estado inesperado: {current_state}. Esperado: {MenuStates.WAIT_ROLE_CHOICE}")
        await cb.answer("Ação ignorada: menu inválido.", show_alert=True)
        return

    role = cb.data.split(":", 1)[1].lower()
    data = await state.get_data()
    roles = data.get("roles", [])

    if role not in roles:
        logging.warning(f"Perfil inválido selecionado: {role}, roles disponíveis: {roles}")
        await cb.answer("Perfil inválido.", show_alert=True)
        return

    selector_id = data.get("menu_msg_id")
    selector_chat = data.get("menu_chat_id")
    logging.debug(f"Menu a ser ocultado: selector_id={selector_id}, selector_chat={selector_chat}")

    # ─── 1. Oculta o título e os botões (remove teclado e altera texto) ───
    if selector_id and selector_chat:
        try:
            await cb.bot.edit_message_text(
                chat_id=selector_chat,
                message_id=selector_id,
                text="✅ Perfil selecionado...",
                parse_mode="Markdown",
                reply_markup=None,
            )
            logging.info(f"Mensagem {selector_id} editada para 'Perfil selecionado...'")
        except exceptions.TelegramBadRequest as e:
            logging.warning(f"Falha ao ocultar título/botões da mensagem {selector_id}: {e}")
        except Exception as e:
            logging.error(f"Erro inesperado ao ocultar título/botões da mensagem {selector_id}: {e}")

        # ─── 2. Substitui por caractere invisível após breve atraso ───
        await asyncio.sleep(0.5)  # Atraso para transição visual
        try:
            await cb.bot.edit_message_text(
                chat_id=selector_chat,
                message_id=selector_id,
                text="\u200B",  # ZERO WIDTH SPACE
                reply_markup=None,
            )
            logging.info(f"Mensagem {selector_id} editada para espaço invisível.")
        except exceptions.TelegramBadRequest as e:
            logging.warning(f"Falha ao substituir mensagem {selector_id} por espaço invisível: {e}")
        except Exception as e:
            logging.error(f"Erro inesperado ao substituir mensagem {selector_id}: {e}")

        # ─── 3. Tenta apagar a mensagem após outro breve atraso ───
        await asyncio.sleep(0.5)  # Atraso adicional para transição fluida
        try:
            await cb.bot.delete_message(selector_chat, selector_id)
            logging.info(f"Mensagem do menu {selector_id} apagada com sucesso.")
        except exceptions.TelegramBadRequest as e:
            logging.warning(f"Falha ao apagar mensagem {selector_id}: {e}")
        except Exception as e:
            logging.error(f"Erro inesperado ao apagar mensagem {selector_id}: {e}")

    # ─── Prossegue com a troca de perfil ───
    try:
        await state.clear()
        await state.update_data(active_role=role, roles=roles)
        logging.debug(f"Estado atualizado: active_role={role}, roles={roles}")

        if role == "administrator":
            await state.set_state(AdminMenuStates.MAIN)
            logging.debug("Estado definido para AdminMenuStates.MAIN")
        else:
            await state.set_state(None)
            logging.debug("Estado limpo (None)")

        await cb.answer(f"Perfil {_label(role)} seleccionado!")
        await show_menu(cb.bot, cb.message.chat.id, state, [role])
        logging.info(f"Novo menu exibido para perfil {role}, chat_id={cb.message.chat.id}")
    except Exception as e:
        logging.error(f"Erro ao processar troca de perfil ou exibir novo menu: {e}")
        await cb.answer("Erro ao selecionar perfil. Tente novamente.", show_alert=True)
