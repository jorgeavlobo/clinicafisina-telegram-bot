# bot/handlers/add_user_handlers.py
"""
Fluxo completo “Adicionar Utilizador”.

Correções desta versão
──────────────────────
1. **Regressar à opção anterior** a partir do primeiro passo volta a mostrar o
   teclado inline de escolha de *User Role* e remove de imediato o teclado
   "custom reply".
2. O teclado "custom reply" desaparece sempre que saímos do formulário para
   o menu de tipos.
3. Quando regressamos e o teclado inline aparece, o par `(menu_msg_id,
   menu_chat_id)` é actualizado — o `ActiveMenuMiddleware` já não bloqueia
   cliques nos botões.
4. Mensagem "Passo anterior" substituída pelo prompt correcto.
"""

from __future__ import annotations

from aiogram import Router, F, types, exceptions
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext

from bot.states.add_user_flow   import AddUserFlow
from bot.menus.common           import cancel_back_kbd
from bot.menus.administrator_menu import build_user_type_kbd
from bot.utils                  import validators as V

router = Router(name="add_user")

# ─────────────────── PROMPTS por estado ───────────────────
PROMPTS: dict[AddUserFlow, str] = {
    AddUserFlow.FIRST_NAME: "Primeiro(s) nome(s):",
    AddUserFlow.LAST_NAME: "Apelido(s):",
    AddUserFlow.DATE_OF_BIRTH: "Data de nascimento (dd-MM-aaaa):",
    AddUserFlow.PHONE_COUNTRY: "Indicativo do país para o telemóvel?\n(Escreva 351 para Portugal ou prefixo internacional)",
    AddUserFlow.PHONE_NUMBER: "Número de telemóvel (sem indicativo):",
    AddUserFlow.EMAIL: "Endereço de e-mail:",
}

# ─────────────────────── helpers ───────────────────────
async def _ask(message: types.Message, text: str, *, kbd: bool = True):
    """Envia pergunta com (ou sem) teclado de navegação."""
    await message.answer(
        text,
        reply_markup=cancel_back_kbd() if kbd else None,
    )

async def _prev_step(state: FSMContext, prev: AddUserFlow):
    await state.set_state(prev)

async def _handle_back_cancel(
    msg: types.Message,
    state: FSMContext,
    prev_state: AddUserFlow | None,
) -> bool:
    """Trata Regressar/Cancelar. Devolve True se interceptou."""
    txt = msg.text.lower().strip()

    # ───────── Cancelar em qualquer passo ─────────
    if txt.startswith("❌"):
        await _cancel_add(msg, state)
        return True

    # ───────── Regressar à opção anterior ─────────
    if txt.startswith("↩️"):
        if prev_state is None:
            # Estamos no primeiro passo – voltar ao menu de tipos
            await state.set_state(AddUserFlow.CHOOSING_ROLE)
            # 1) remover o teclado reply
            await msg.answer(" ", reply_markup=types.ReplyKeyboardRemove())
            # 2) mostrar novamente o teclado inline com tipos
            role_msg = await msg.answer(
                "👤 *Adicionar utilizador* — escolha o tipo:",
                parse_mode="Markdown",
                reply_markup=build_user_type_kbd(),
            )
            # 3) registar menu activo para o middleware
            await state.update_data(menu_msg_id=role_msg.message_id,
                                    menu_chat_id=role_msg.chat.id)
            return True
        # Passo normal: voltar ao anterior
        await _prev_step(state, prev_state)
        await _ask(msg, PROMPTS[prev_state])
        return True
    return False

async def _cancel_add(msg: types.Message, state: FSMContext):
    """Aborta todo o fluxo."""
    await msg.answer(
        "❌ Adição de utilizador cancelada.",
        reply_markup=types.ReplyKeyboardRemove(),
    )
    await state.clear()

# ───────────────────────── FIRST_NAME ─────────────────────────
@router.message(StateFilter(AddUserFlow.FIRST_NAME))
async def first_name_step(msg: types.Message, state: FSMContext):
    if await _handle_back_cancel(msg, state, None):
        return
    await state.update_data(first_name=msg.text.strip())
    await _ask(msg, PROMPTS[AddUserFlow.LAST_NAME])
    await state.set_state(AddUserFlow.LAST_NAME)

# ───────────────────────── LAST_NAME ─────────────────────────
@router.message(StateFilter(AddUserFlow.LAST_NAME))
async def last_name_step(msg: types.Message, state: FSMContext):
    if await _handle_back_cancel(msg, state, AddUserFlow.FIRST_NAME):
        return
    await state.update_data(last_name=msg.text.strip())
    await _ask(msg, PROMPTS[AddUserFlow.DATE_OF_BIRTH])
    await state.set_state(AddUserFlow.DATE_OF_BIRTH)

# ─────────────────────── DATE_OF_BIRTH ───────────────────────
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
    await _ask(msg, PROMPTS[AddUserFlow.PHONE_COUNTRY])
    await state.set_state(AddUserFlow.PHONE_COUNTRY)

# ─────────────────────── PHONE_COUNTRY ───────────────────────
@router.message(StateFilter(AddUserFlow.PHONE_COUNTRY))
async def phone_country_step(msg: types.Message, state: FSMContext):
    if await _handle_back_cancel(msg, state, AddUserFlow.DATE_OF_BIRTH):
        return
    cc = msg.text.replace("+", "").lstrip("0").strip()
    await state.update_data(phone_cc=cc)
    await _ask(msg, PROMPTS[AddUserFlow.PHONE_NUMBER])
    await state.set_state(AddUserFlow.PHONE_NUMBER)

# ─────────────────────── PHONE_NUMBER ───────────────────────
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
    await _ask(msg, PROMPTS[AddUserFlow.EMAIL])
    await state.set_state(AddUserFlow.EMAIL)

# ───────────────────────── EMAIL ─────────────────────────
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
    await _summarise(msg, state)

# ─────────────────── SUMÁRIO & CONFIRMAÇÃO ───────────────────
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
    sent = await msg.answer(summary, parse_mode="Markdown", reply_markup=kbd,
                            reply_markup_remove=True)
    await state.update_data(menu_msg_id=sent.message_id, menu_chat_id=sent.chat.id)
    await state.set_state(AddUserFlow.CONFIRM_DATA)

# ────────────────── CALLBACKS Confirmar / Editar / Cancelar ──────────────────
@router.callback_query(AddUserFlow.CONFIRM_DATA, F.data == "adduser:cancel")
async def confirm_cancel(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer("Operação cancelada.", show_alert=True)
    await _close_summary(cb, state, "❌ Processo cancelado.")

@router.callback_query(AddUserFlow.CONFIRM_DATA, F.data == "adduser:confirm")
async def confirm_save(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer("💾 A guardar…", show_alert=False)
    # TODO: inserir na BD
    await _close_summary(cb, state, "✅ Utilizador adicionado com sucesso!")

@router.callback_query(AddUserFlow.CONFIRM_DATA, F.data == "adduser:edit")
async def confirm_edit(cb: types.CallbackQuery, state: FSMContext):
    await cb.answer()
    await cb.message.edit_reply_markup(reply_markup=None)
    await cb.message.answer("🚧 Edição ainda não implementada.")

async def _close_summary(cb: types.CallbackQuery, state
