# bot/handlers/add_user_handlers.py
"""
Fluxo “Adicionar Utilizador”.

Este router é importado em handlers/__init__.py.
Lógica:
1. Iniciado em administrator_handlers depois de CHOOSE_TYPE.
2. Cada passo valida input, permite «Regressar» (volta ao passo anterior)
   ou «Cancelar» (termina o processo e limpa teclado).
3. No final mostra resumo + inline buttons Confirmar / Editar / Cancelar.
"""

from __future__ import annotations

from aiogram import Router, F, types
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.states.add_user_flow   import AddUserFlow
from bot.menus.common           import cancel_back_kbd
from bot.utils                  import validators as V

router = Router(name="add_user")


# ─────────────────────── helpers ───────────────────────
async def _ask(message: types.Message, text: str, *, kbd=True):
    await message.answer(
        text,
        reply_markup=cancel_back_kbd() if kbd else None,
    )

async def _prev_step(state: FSMContext, prev: AddUserFlow):
    await state.set_state(prev)

# ─────────────────── entry: FIRST_NAME ───────────────────
@router.message(StateFilter(AddUserFlow.FIRST_NAME))
async def first_name_step(msg: types.Message, state: FSMContext):
    txt = msg.text.strip()
    if txt.lower().startswith("❌"):
        await _cancel_add(msg, state)
        return
    if txt.lower().startswith("↩️"):
        # não há passo anterior – mantemos estado
        return
    await state.update_data(first_name=txt)
    await _ask(msg, "Apelido(s):")
    await state.set_state(AddUserFlow.LAST_NAME)

# ─────────────────── LAST_NAME ───────────────────
@router.message(StateFilter(AddUserFlow.LAST_NAME))
async def last_name_step(msg: types.Message, state: FSMContext):
    if await _handle_back_cancel(msg, state, AddUserFlow.FIRST_NAME):
        return
    await state.update_data(last_name=msg.text.strip())
    await _ask(msg, "Data de nascimento (dd-MM-aaaa):")
    await state.set_state(AddUserFlow.DATE_OF_BIRTH)

# ─────────────────── DATE_OF_BIRTH ───────────────────
@router.message(StateFilter(AddUserFlow.DATE_OF_BIRTH))
async def dob_step(msg: types.Message, state: FSMContext):
    if await _handle_back_cancel(msg, state, AddUserFlow.LAST_NAME):
        return
    try:
        dob = V.valid_date(msg.text)
    except ValueError as e:
        await msg.reply(f"⚠️ {e}")
        return
    await state.update_data(date_of_birth=str(dob))
    # País do telefone
    await _ask(msg, "Indicativo do país para o telemóvel?\n(Escreva 351 para Portugal ou prefixo internacional)")
    await state.set_state(AddUserFlow.PHONE_COUNTRY)

# ─────────────────── PHONE_COUNTRY ───────────────────
@router.message(StateFilter(AddUserFlow.PHONE_COUNTRY))
async def phone_country_step(msg: types.Message, state: FSMContext):
    if await _handle_back_cancel(msg, state, AddUserFlow.DATE_OF_BIRTH):
        return
    cc = msg.text.replace("+", "").lstrip("0").strip()
    await state.update_data(phone_cc=cc)
    await _ask(msg, "Número de telemóvel (sem indicativo):")
    await state.set_state(AddUserFlow.PHONE_NUMBER)

# ─────────────────── PHONE_NUMBER ───────────────────
@router.message(StateFilter(AddUserFlow.PHONE_NUMBER))
async def phone_number_step(msg: types.Message, state: FSMContext):
    if await _handle_back_cancel(msg, state, AddUserFlow.PHONE_COUNTRY):
        return
    data = await state.get_data()
    cc = data["phone_cc"]
    num = msg.text.strip()
    try:
        if cc == "351":
            V.valid_pt_phone(num)
        else:
            if not num.isdigit():
                raise ValueError("Apenas dígitos.")
    except ValueError as e:
        await msg.reply(f"⚠️ {e}")
        return
    await state.update_data(phone=num)
    await _ask(msg, "Endereço de e-mail:")
    await state.set_state(AddUserFlow.EMAIL)

# ─────────────────── EMAIL ───────────────────
@router.message(StateFilter(AddUserFlow.EMAIL))
async def email_step(msg: types.Message, state: FSMContext):
    if await _handle_back_cancel(msg, state, AddUserFlow.PHONE_NUMBER):
        return
    try:
        email = V.valid_email(msg.text)
    except ValueError as e:
        await msg.reply(f"⚠️ {e}")
        return
    await state.update_data(email=email)
    # Aqui seguiríamos com WANT_ADDRESS etc.
    await _summarise(msg, state)

# ─────────────────── helpers comuns ───────────────────
async def _handle_back_cancel(
    msg: types.Message,
    state: FSMContext,
    prev_state: AddUserFlow,
) -> bool:
    """Trata “Regressar”/“Cancelar”. Devolve True se interceptou."""
    txt = msg.text.lower().strip()
    if txt.startswith("❌"):
        await _cancel_add(msg, state)
        return True
    if txt.startswith("↩️"):
        await _prev_step(state, prev_state)
        await msg.answer("Passo anterior.", reply_markup=cancel_back_kbd())
        return True
    return False

async def _cancel_add(msg: types.Message, state: FSMContext):
    await msg.answer("❌ Adição de utilizador cancelada.",
                     reply_markup=types.ReplyKeyboardRemove())
    await state.clear()

async def _summarise(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    summary = (
        "*Confirme os dados:*\n"
        f"• Tipo: {data.get('role')}\n"
        f"• Nome: {data.get('first_name')} {data.get('last_name')}\n"
        f"• Data Nasc.: {data.get('date_of_birth')}\n"
        f"• Tel.: +{data.get('phone_cc')}{data.get('phone')}\n"
        f"• Email: {data.get('email')}"
    )
    kbd = types.InlineKeyboardMarkup(
        inline_keyboard=[
            [types.InlineKeyboardButton(text="✅ Confirmar", callback_data="adduser:confirm")],
            [types.InlineKeyboardButton(text="✏️ Editar",    callback_data="adduser:edit")],
            [types.InlineKeyboardButton(text="❌ Cancelar",  callback_data="adduser:cancel")],
        ]
    )
    await msg.answer(summary, parse_mode="Markdown", reply_markup=kbd,
                     reply_markup_remove=True)
    await state.set_state(AddUserFlow.CONFIRM_DATA)
