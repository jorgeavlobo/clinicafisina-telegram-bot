# bot/handlers/administrator_handlers.py
from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from bot.filters.role_filter import RoleFilter
from bot.states.admin_menu_states import AdminMenuStates

router = Router(name="administrator")

# ───────────── builders inline ─────────────
def kbd_agenda() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Geral", callback_data="adm:agenda:geral")],
        [InlineKeyboardButton(text="🩺 Escolher Fisioterapeuta",
                              callback_data="adm:agenda:physio")],
        [InlineKeyboardButton(text="🔙 Voltar", callback_data="adm:back")],
    ])

def kbd_agenda_interval(parent: str) -> InlineKeyboardMarkup:
    base = f"adm:{parent}:"
    rows = [
        [InlineKeyboardButton(text="📆 Hoje",           callback_data=base+"today"),
         InlineKeyboardButton(text="📆 Amanhã",         callback_data=base+"tomorrow")],
        [InlineKeyboardButton(text="📆 Ontem",          callback_data=base+"yesterday")],
        [InlineKeyboardButton(text="🗓 Esta Semana",    callback_data=base+"week")],
        [InlineKeyboardButton(text="🗓 Próxima Semana", callback_data=base+"nextweek")],
        [InlineKeyboardButton(text="🔙 Voltar",         callback_data="adm:back")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kbd_users() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔎 Procurar",   callback_data="adm:users:search")],
        [InlineKeyboardButton(text="➕ Adicionar",  callback_data="adm:users:add")],
        [InlineKeyboardButton(text="🔙 Voltar",     callback_data="adm:back")],
    ])

def kbd_users_add() -> InlineKeyboardMarkup:
    base = "adm:users:add:"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🩺 Fisioterapeuta", callback_data=base+"physio")],
        [InlineKeyboardButton(text="👤 Paciente",       callback_data=base+"patient")],
        [InlineKeyboardButton(text="🧑‍🦽 Cuidador",     callback_data=base+"caregiver")],
        [InlineKeyboardButton(text="💼 Contabilista",   callback_data=base+"accountant")],
        [InlineKeyboardButton(text="🛠 Administrador",  callback_data=base+"admin")],
        [InlineKeyboardButton(text="🔙 Voltar",         callback_data="adm:back")],
    ])

# ───────────── callbacks de navegação ─────────────
@router.callback_query(RoleFilter("administrator"), F.data.startswith("adm:"))
async def nav_admin(cb: CallbackQuery, state: FSMContext):
    parts = cb.data.split(":")[1:]          # strip 'adm'
    try:
        await cb.answer()
    except TelegramBadRequest:
        pass

    # fechar tudo
    if parts == ["close"]:
        await state.clear()
        await cb.message.delete()
        return

    # voltar
    if parts == ["back"]:
        await state.set_state(AdminMenuStates.MAIN, ttl=60)
        await cb.message.edit_reply_markup(reply_markup=cb.message.reply_markup)
        return

    # ─── Agenda ───
    if parts[0] == "agenda":
        if len(parts) == 1:
            await state.set_state(AdminMenuStates.AGENDA, ttl=60)
            await cb.message.edit_reply_markup(reply_markup=kbd_agenda())
            return
        parent = "agenda:" + parts[1]
        if len(parts) == 2:
            await cb.message.edit_reply_markup(reply_markup=kbd_agenda_interval(parent))
            return
        await cb.message.answer("🚧 (placeholder) Agenda – filtro não implementado.")
        return

    # ─── Utilizadores ───
    if parts[0] == "users":
        if len(parts) == 1:
            await state.set_state(AdminMenuStates.USERS, ttl=60)
            await cb.message.edit_reply_markup(reply_markup=kbd_users())
            return
        if parts[1] == "search":
            await cb.message.answer("🚧 (placeholder) Pesquisa de utilizadores.")
            return
        if parts[1] == "add":
            if len(parts) == 2:
                await state.set_state(AdminMenuStates.USERS_ADD, ttl=120)
                await cb.message.edit_reply_markup(reply_markup=kbd_users_add())
                return
            await cb.message.answer("🚧 (placeholder) Wizard de criação de utilizador.")
            return

    await cb.message.answer("❗ Opção não reconhecida.")
