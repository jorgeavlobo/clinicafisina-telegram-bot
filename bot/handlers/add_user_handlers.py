# bot/handlers/add_user_handlers.py
"""
Fluxo “Adicionar Utilizador” – versão consolidada e corrigida
• Indicativo genérico normalizado (+44 / 44 / 0044, …)
• Data de nascimento opcional (“saltar”/“skip”)
• Gravação real via queries.add_user()
• Limpa mensagens do formulário por privacidade
• Compatível com ActiveMenuMiddleware
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from aiogram import Router, F, types, exceptions
from aiogram.fsm.context import FSMContext

from bot.states.add_user_flow      import AddUserFlow
from bot.menus.common              import cancel_back_kbd
from bot.menus.administrator_menu  import build_user_type_kbd
from bot.utils.validators          import (
    normalize_phone_cc, valid_date, valid_email, valid_pt_phone,
)
from bot.database                  import queries as Q

router = Router(name="add_user")

PROMPTS = {
    AddUserFlow.FIRST_NAME:   "Primeiro(s) nome(s):",
    AddUserFlow.LAST_NAME:    "Apelido(s):",
    AddUserFlow.DATE_OF_BIRTH:"Data de nascimento (dd-MM-aaaa ou dd/MM/aaaa) — escreva «saltar» se desconhece:",
    AddUserFlow.PHONE_COUNTRY:"Indicativo do país (ex.: +351, 351 ou 00351):",
    AddUserFlow.PHONE_NUMBER: "Número de telemóvel *sem* indicativo:",
    AddUserFlow.EMAIL:        "Endereço de e-mail:",
}

# ───────────────────── helpers de suporte ──────────────────────
async def _cache(state: FSMContext, mid: int) -> None:
    data = await state.get_data()
    data.setdefault("flow_msgs", []).append(mid)
    await state.update_data(flow_msgs=data["flow_msgs"])

async def _purge(bot: types.Bot, state: FSMContext) -> None:
    data = await state.get_data()
    for mid in data.get("flow_msgs", []):
        try:
            await bot.delete_message(data["menu_chat_id"], mid)
        except exceptions.TelegramBadRequest:
            pass
    await state.update_data(flow_msgs=[])

async def _ask(
    msg: types.Message,
    prompt: str,
    state: FSMContext,
    *,
    kbd: bool = True,
) -> None:
    m = await msg.answer(
        prompt,
        reply_markup=cancel_back_kbd() if kbd else types.ReplyKeyboardRemove(),
    )
    await _cache(state, m.message_id)

async def _cancel_flow(msg: types.Message, state: FSMContext):
    await _purge(msg.bot, state)
    await msg.answer("❌ Processo cancelado.", reply_markup=types.ReplyKeyboardRemove())
    await state.clear()

async def _handle_back_cancel(
    msg: types.Message,
    state: FSMContext,
    prev: Optional[AddUserFlow],
) -> bool:
    """
    Trata «❌ Cancelar…» e «↩️ Regressar…».
    Devolve True se já lidou com a mensagem.
    """
    await _cache(state, msg.message_id)
    txt = msg.text.lower().strip()

    if txt.startswith("❌"):
        await _cancel_flow(msg, state)
        return True

    if txt.startswith("↩️"):
        if prev is None:  # voltar ao menu de tipos
            await state.set_state(AddUserFlow.CHOOSING_ROLE)
            await msg.answer("⁠", reply_markup=types.ReplyKeyboardRemove())  # zero-width char
            menu = await msg.answer(
                "👤 *Adicionar utilizador* — escolha o tipo:",
                parse_mode="Markdown",
                reply_markup=build_user_type_kbd(),
            )
            await state.update_data(menu_msg_id=menu.message_id, menu_chat_id=menu.chat.id)
            await _cache(state, menu.message_id)
            return True

        await state.set_state(prev)
        await _ask(msg, PROMPTS[prev], state)
        return True

    return False

# ─────────────────────── passos FSM ───────────────────────
@router.message(AddUserFlow.FIRST_NAME)
async def first_name(msg: types.Message, state: FSMContext):
    if await _handle_back_cancel(msg, state, None):
        return
    await state.update_data(first_name=msg.text.strip())
    await _ask(msg, PROMPTS[AddUserFlow.LAST_NAME], state)
    await state.set_state(AddUserFlow.LAST_NAME)

@router.message(AddUserFlow.LAST_NAME)
async def last_name(msg: types.Message, state: FSMContext):
    if await _handle_back_cancel(msg, state, AddUserFlow.FIRST_NAME):
        return
    await state.update_data(last_name=msg.text.strip())
    await _ask(msg, PROMPTS[AddUserFlow.DATE_OF_BIRTH], state)
    await state.set_state(AddUserFlow.DATE_OF_BIRTH)

@router.message(AddUserFlow.DATE_OF_BIRTH)
async def dob(msg: types.Message, state: FSMContext):
    if await _handle_back_cancel(msg, state, AddUserFlow.LAST_NAME):
        return

    txt = msg.text.strip()
    if txt.lower() in {"saltar", "skip"}:
        await state.update_data(date_of_birth=None)
    else:
        try:
            dob = valid_date(txt)
        except ValueError as e:
            return await msg.reply(f"⚠️ {e}")
        await state.update_data(date_of_birth=str(dob))

    await _ask(msg, PROMPTS[AddUserFlow.PHONE_COUNTRY], state)
    await state.set_state(AddUserFlow.PHONE_COUNTRY)

@router.message(AddUserFlow.PHONE_COUNTRY)
async def phone_cc(msg: types.Message, state: FSMContext):
    if await _handle_back_cancel(msg, state, AddUserFlow.DATE_OF_BIRTH):
        return
    try:
        disp, cc = normalize_phone_cc(msg.text)
    except ValueError as e:
        return await msg.reply(f"⚠️ {e}")
    await state.update_data(phone_cc_display=disp, phone_cc=cc)
    await _ask(msg, PROMPTS[AddUserFlow.PHONE_NUMBER], state)
    await state.set_state(AddUserFlow.PHONE_NUMBER)

@router.message(AddUserFlow.PHONE_NUMBER)
async def phone(msg: types.Message, state: FSMContext):
    if await _handle_back_cancel(msg, state, AddUserFlow.PHONE_COUNTRY):
        return
    data = await state.get_data()
    try:
        if data["phone_cc"] == "351":
            valid_pt_phone(msg.text.strip())
        elif not msg.text.isdigit():
            raise ValueError("Apenas dígitos.")
    except ValueError as e:
        return await msg.reply(f"⚠️ {e}")
    await state.update_data(phone=msg.text.strip())
    await _ask(msg, PROMPTS[AddUserFlow.EMAIL], state)
    await state.set_state(AddUserFlow.EMAIL)

@router.message(AddUserFlow.EMAIL)
async def email(msg: types.Message, state: FSMContext):
    if await _handle_back_cancel(msg, state, AddUserFlow.PHONE_NUMBER):
        return
    try:
        email = valid_email(msg.text)
    except ValueError as e:
        return await msg.reply(f"⚠️ {e}")
    await state.update_data(email=email)
    await _summary(msg, state)

# ───────────── resumo & callbacks ─────────────
async def _summary(msg: types.Message, state: FSMContext):
    d = await state.get_data()
    dob_txt = d["date_of_birth"] or "—"
    txt = (
        "*Confirme os dados:*\n"
        f"• Tipo: {d['role']}\n"
        f"• Nome: {d['first_name']} {d['last_name']}\n"
        f"• Data Nasc.: {dob_txt}\n"
        f"• Tel.: {d['phone_cc_display']}{d['phone']}\n"
        f"• Email: {d['email']}"
    )
    kb = types.InlineKeyboardMarkup(
        inline_keyboard=[[
            types.InlineKeyboardButton("✅ Confirmar", callback_data="add_ok"),
            types.InlineKeyboardButton("✏️ Editar",    callback_data="add_edit"),
            types.InlineKeyboardButton("❌ Cancelar",  callback_data="add_cancel"),
        ]]
    )
    m = await msg.answer(txt, reply_markup=kb, parse_mode="Markdown")
    await state.update_data(menu_msg_id=m.message_id, menu_chat_id=m.chat.id)
    await _cache(state, m.message_id)
    await state.set_state(AddUserFlow.CONFIRM_DATA)

@router.callback_query(AddUserFlow.CONFIRM_DATA, F.data == "add_cancel")
async def cb_cancel(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer("Cancelado")
    await _finish(cb, state, "❌ Operação cancelada.")

@router.callback_query(AddUserFlow.CONFIRM_DATA, F.data == "add_ok")
async def cb_ok(cb: types.CallbackQuery, state: FSMContext):
    d = await state.get_data()
    pool = cb.bot["pg_pool"]  # injecção no main
    await Q.add_user(
        pool,
        role=d["role"],
        first_name=d["first_name"],
        last_name=d["last_name"],
        date_of_birth=(date.fromisoformat(d["date_of_birth"]) if d["date_of_birth"] else None),
        phone_cc=d["phone_cc"],
        phone=d["phone"],
        email=d["email"],
        created_by=str(cb.from_user.id),
    )
    await cb.answer()
    await _finish(cb, state, "✅ Utilizador adicionado com sucesso!")

@router.callback_query(AddUserFlow.CONFIRM_DATA, F.data == "add_edit")
async def cb_edit(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer("🚧 Edição ainda não implementada", show_alert=True)

# ───────────── função final ─────────────
async def _finish(cb: types.CallbackQuery, state: FSMContext, text: str):
    await _purge(cb.bot, state)
    try:
        await cb.message.edit_text(text, parse_mode="Markdown")
    except exceptions.TelegramBadRequest:
        pass
    await state.clear()
