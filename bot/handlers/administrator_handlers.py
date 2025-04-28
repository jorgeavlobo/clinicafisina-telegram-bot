# bot/handlers/administrator_handlers.py
"""
Handlers do menu de Administrador
(garante menu activo, timeout, placeholders, etc.)
"""
from __future__ import annotations

import asyncio
from typing import Iterable

from aiogram import Router, F, exceptions
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.filters.role_filter import RoleFilter
from bot.states.admin_menu_states import AdminMenuStates
from bot.menus.common import back_button, start_menu_timeout

router = Router(name="administrator")
router.callback_query.filter(RoleFilter("administrator"))


# ────────────── builders ──────────────
def _agenda_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📆 Geral",               callback_data="agenda:geral")],
            [InlineKeyboardButton(text="🩺 Escolher Fisioterapeuta", callback_data="agenda:fisios")],
            [back_button()],
        ]
    )

def _users_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Procurar", callback_data="users:search")],
            [InlineKeyboardButton(text="➕ Adicionar", callback_data="users:add")],
            [back_button()],
        ]
    )

# ────────────── helpers (menu activo / timeout) ──────────────
async def _ensure_active(cb: CallbackQuery, state: FSMContext) -> bool:
    data = await state.get_data()
    return cb.message.message_id == data.get("menu_msg_id")

async def _replace_menu(
    cb: CallbackQuery,
    state: FSMContext,
    text: str,
    kbd: InlineKeyboardMarkup,
) -> None:
    try:
        await cb.message.edit_text(text, reply_markup=kbd, parse_mode="Markdown")
    except exceptions.TelegramBadRequest:
        # se não conseguir editar, envia nova e apaga antiga
        await cb.message.delete()
        new_msg = await cb.message.answer(text, reply_markup=kbd, parse_mode="Markdown")
        await state.update_data(menu_msg_id=new_msg.message_id,
                                menu_chat_id=new_msg.chat.id)
        start_menu_timeout(cb.bot, new_msg, state)   # reinicia timeout


# ────────────── MAIN nav (Agenda / Utilizadores) ──────────────
@router.callback_query(
    StateFilter(AdminMenuStates.MAIN),
    F.data.in_(["admin:agenda", "admin:users"])        # ← sem “&”
)
async def admin_main_nav(cb: CallbackQuery, state: FSMContext):
    if not await _ensure_active(cb, state):
        await cb.answer("⚠️ Este menu já não está activo.", show_alert=True)
        return
    await cb.answer()

    if cb.data == "admin:agenda":
        await state.set_state(AdminMenuStates.AGENDA)
        await _replace_menu(cb, state, "📅 *Agenda* — seleccione:", _agenda_kbd())
    else:
        await state.set_state(AdminMenuStates.USERS)
        await _replace_menu(cb, state, "👥 *Utilizadores* — seleccione:", _users_kbd())


# ────────────── Agenda (placeholders) ──────────────
@router.callback_query(StateFilter(AdminMenuStates.AGENDA),
                       F.data.in_(["agenda:geral", "agenda:fisios"]))
async def agenda_placeholders(cb: CallbackQuery, state: FSMContext):
    if not await _ensure_active(cb, state):
        await cb.answer("⚠️ Este menu já não está activo.", show_alert=True)
        return

    await cb.answer("🚧 Placeholder – em desenvolvimento", show_alert=True)
    await cb.message.delete()
    await state.update_data(menu_msg_id=None, menu_chat_id=None)

@router.callback_query(StateFilter(AdminMenuStates.AGENDA), F.data == "back")
async def agenda_back(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminMenuStates.MAIN)
    # simula clique “admin:agenda” para reutilizar handler
    fake_cb = cb.copy(update={"data": "admin:agenda"})
    await admin_main_nav(fake_cb, state)


# ────────────── Utilizadores (placeholders) ──────────────
@router.callback_query(StateFilter(AdminMenuStates.USERS),
                       F.data.in_(["users:search", "users:add"]))
async def users_placeholders(cb: CallbackQuery, state: FSMContext):
    if not await _ensure_active(cb, state):
        await cb.answer("⚠️ Este menu já não está activo.", show_alert=True)
        return
    await cb.answer("🚧 Placeholder – em desenvolvimento", show_alert=True)
    await cb.message.delete()
    await state.update_data(menu_msg_id=None, menu_chat_id=None)

@router.callback_query(StateFilter(AdminMenuStates.USERS), F.data == "back")
async def users_back(cb: CallbackQuery, state: FSMContext):
    await state.set_state(AdminMenuStates.MAIN)
    fake_cb = cb.copy(update={"data": "admin:users"})
    await admin_main_nav(fake_cb, state)
