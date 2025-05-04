# bot/handlers/role_choice_handlers.py
"""
Selector de perfil quando o utilizador tem ≥ 2 papéis.

– Mostra inline-keyboard com timeout (via ui_helpers.refresh_menu)
– Guarda o menu activo no FSM (menu_msg_id/menu_chat_id)
– Quando o utilizador escolhe, remove o selector e abre o menu do perfil escolhido
"""

from __future__ import annotations

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext

from bot.menus                     import show_menu
from bot.menus.ui_helpers          import refresh_menu, close_menu_with_alert
from bot.states.menu_states        import MenuStates

router = Router(name="role_choice")

# ───────────────────────── labels PT ─────────────────────────
_LABELS_PT = {
    "patient":         "🩹 Paciente",
    "caregiver":       "🫱🏼‍🫲🏽 Cuidador",
    "physiotherapist": "👩🏼‍⚕️ Fisioterapeuta",
    "accountant":      "📊 Contabilista",
    "administrator":   "👨🏼‍💻 Administrador",
}
def _label(role: str) -> str:
    return _LABELS_PT.get(role.lower(), role.capitalize())

# ───────────────────────── ask_role ─────────────────────────
async def ask_role(
    bot: types.Bot,
    chat_id: int,
    state: FSMContext,
    roles: list[str],
) -> None:
    """Renderiza (ou actualiza) o selector de perfis usando refresh_menu()."""
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text=_label(r), callback_data=f"role:{r.lower()}")]
            for r in roles
        ]
    )

    data          = await state.get_data()
    prev_msg_id   = data.get("menu_msg_id")      # id do selector anterior (se existir)

    # Usa helper genérico: editar ↦ apagar ↦ enviar novo + timeout
    msg = await refresh_menu(
        bot       = bot,
        state     = state,
        chat_id   = chat_id,
        message_id= prev_msg_id,
        text      = "🎭 *Escolha o perfil:*",
        keyboard  = kbd,
    )

    # Guarda papéis disponíveis e estado de espera
    await state.set_state(MenuStates.WAIT_ROLE_CHOICE)
    await state.update_data(roles=[r.lower() for r in roles])

# ─────────────────── callback «role:…» ────────────────────
@router.callback_query(
    F.data.startswith("role:"),
    state=MenuStates.WAIT_ROLE_CHOICE,
)
async def choose_role(cb: types.CallbackQuery, state: FSMContext) -> None:
    role   = cb.data.split(":", 1)[1].lower()
    data   = await state.get_data()
    roles  = data.get("roles", [])

    if role not in roles:
        await cb.answer("Perfil inválido.", show_alert=True)
        return

    # Pop-up + remoção do selector via helper
    await close_menu_with_alert(cb, f"✅ Perfil {_label(role)} seleccionado!")

    # Actualiza FSM e abre o menu do papel escolhido
    await state.update_data(active_role=role)
    await show_menu(cb.bot, cb.from_user.id, state, [role], requested=role)
