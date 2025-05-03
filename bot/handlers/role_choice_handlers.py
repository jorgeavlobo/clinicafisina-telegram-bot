# bot/handlers/role_choice_handlers.py
"""
Profile selector shown when the user has two or more roles.

Agora, quando o papel escolhido for «administrator», em vez de apagar a
mensagem‑selector e enviar outra nova, **editamos** essa mesma bolha
tal como já acontece dentro do menu de administrador — desaparece o
“salto” visual.  Para os restantes papéis o fluxo mantém‑se.

(Usamos a função _replace_menu() que já existe em administrator_handlers.)
"""

from __future__ import annotations

from contextlib import suppress
from typing import Iterable, List

from aiogram import Router, types, F, exceptions
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.menus                     import show_menu
from bot.menus.administrator_menu  import build_menu as _admin_menu_kbd
from bot.states.menu_states        import MenuStates
from bot.states.admin_menu_states  import AdminMenuStates
from bot.handlers.administrator_handlers import _replace_menu as _admin_replace_menu

router = Router(name="role_choice")

# ──────────────────────────── UI helpers ────────────────────────────
_LABELS_PT = {
    "patient":         "🧑🏼‍🦯 Paciente",
    "caregiver":       "🤝🏼 Cuidador",
    "physiotherapist": "👩🏼‍⚕️ Fisioterapeuta",
    "accountant":      "📊 Contabilista",
    "administrator":   "👨🏼‍💼 Administrador",
}
def _label(role: str) -> str:
    return _LABELS_PT.get(role.lower(), role.capitalize())

# ────────────────────────── ask_role (entry) ─────────────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: Iterable[str],
) -> None:
    """Show the profile selector and remember its message‑ID."""
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton(
                text=_label(r),
                callback_data=f"role:{r.lower()}",
            )
        ] for r in roles]
    )

    msg = await bot.send_message(
        chat_id,
        "🔰 *Escolha o perfil:*",
        reply_markup=kbd,
        parse_mode="Markdown",
    )

    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(
        roles=[r.lower() for r in roles],
        menu_ids=[msg.message_id],
        menu_msg_id=msg.message_id,
        menu_chat_id=msg.chat.id,
    )

# ─────────────────────── callback «role:…» ──────────────────────────
@router.callback_query(
    StateFilter(MenuStates.WAIT_ROLE_CHOICE),
    F.data.startswith("role:"),
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    role = cb.data.split(":", 1)[1].lower()
    data = await state.get_data()
    if role not in data.get("roles", []):
        await cb.answer("Perfil inválido.", show_alert=True)
        return

    # ─── ADMINISTRATOR: editar a própria bolha (sem salto) ──────────
    if role == "administrator":
        # 1) FSM → estado base admin
        await state.clear()
        await state.update_data(active_role=role)
        await state.set_state(AdminMenuStates.MAIN)

        # 2) substituir o selector pelo menu
        await _admin_replace_menu(
            cb,
            state,
            "💻 *Menu:*",
            _admin_menu_kbd(),
        )

        await cb.answer(f"Perfil {_label(role)} seleccionado!")
        return

    # ─── outros papéis (fluxo antigo) ───────────────────────────────
    # limpa tudo, guarda active_role e mostra menu “normal”
    for mid in data.get("menu_ids", []):
        with suppress(exceptions.TelegramBadRequest):
            await cb.bot.delete_message(cb.message.chat.id, mid)

    await state.clear()
    await state.update_data(active_role=role)
    await cb.answer(f"Perfil {_label(role)} seleccionado!")

    # show_menu criará uma nova mensagem (não faz mal aqui)
    await show_menu(cb.bot, cb.from_user.id, state, [role])
