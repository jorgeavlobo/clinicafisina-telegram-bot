# bot/handlers/administrator_handlers.py
"""
Administrator menu handlers.
- Ensures only the active menu responds (via global middleware).
- 60 s timeout for menu inactivity.
- "Voltar" (Back) button works correctly.
"""
from __future__ import annotations

from aiogram import Router, F, exceptions
from aiogram.filters import StateFilter
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from bot.filters.role_filter import RoleFilter
from bot.states.admin_menu_states import AdminMenuStates, AddUserStates
from bot.menus.common import back_button, start_menu_timeout
from bot.menus.administrator_menu import build_menu as _main_menu_kbd
from bot.menus.administrator_menu import build_user_type_kbd
from bot.database.connection import get_pool
from bot.database import queries as q
import re
import datetime

router = Router(name="administrator")
router.callback_query.filter(RoleFilter("administrator"))
router.message.filter(RoleFilter("administrator"))

# ───────────────────────────── builders ──────────────────────────────
def _agenda_kbd() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📆 Geral", callback_data="agenda:geral")],
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

# ───────────────────────── helpers ──────────────────────────────────
async def _replace_menu(cb: CallbackQuery, state: FSMContext, text: str, kbd: InlineKeyboardMarkup) -> None:
    """
    Edit the current menu message to update its content, or send a new message if editing fails.
    Updates the FSM state data with the new menu message ID and restarts the inactivity timeout.
    """
    try:
        await cb.message.edit_text(text, reply_markup=kbd, parse_mode="Markdown")
        msg = cb.message
    except exceptions.TelegramBadRequest:
        await cb.message.delete()
        msg = await cb.message.answer(text, reply_markup=kbd, parse_mode="Markdown")
        await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)
    # Start/reset the 60-second inactivity timeout for this menu
    start_menu_timeout(cb.bot, msg, state)

async def _show_main_menu(cb: CallbackQuery, state: FSMContext) -> None:
    """Return to the main Administrator menu."""
    await state.set_state(AdminMenuStates.MAIN)
    await _replace_menu(cb, state, "💻 *Menu:*", _main_menu_kbd())

# ─────────────────────────── MAIN nav ───────────────────────────────
@router.callback_query(StateFilter(AdminMenuStates.MAIN), F.data.in_(["admin:agenda", "admin:users"]))
async def admin_main_nav(cb: CallbackQuery, state: FSMContext):
    # Navigate from the main menu to the "Agenda" or "Utilizadores" submenu
    await cb.answer()
    if cb.data == "admin:agenda":
        await state.set_state(AdminMenuStates.AGENDA)
        await _replace_menu(cb, state, "📅 *Agenda* — seleccione:", _agenda_kbd())
    else:
        await state.set_state(AdminMenuStates.USERS)
        await _replace_menu(cb, state, "👥 *Utilizadores* — seleccione:", _users_kbd())

# ──────────────────────── Agenda (placeholders) ─────────────────────
@router.callback_query(StateFilter(AdminMenuStates.AGENDA), F.data.in_(["agenda:geral", "agenda:fisios"]))
async def agenda_placeholders(cb: CallbackQuery, state: FSMContext):
    # Placeholder for Agenda options (not implemented yet)
    await cb.answer("🚧 Placeholder – em desenvolvimento", show_alert=True)
    await cb.message.delete()
    await state.update_data(menu_msg_id=None, menu_chat_id=None)

@router.callback_query(StateFilter(AdminMenuStates.AGENDA), F.data == "back")
async def agenda_back(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await _show_main_menu(cb, state)

# ──────────────────────── Utilizadores (User management) ─────────────────────
@router.callback_query(StateFilter(AdminMenuStates.USERS), F.data == "users:search")
async def users_search_placeholder(cb: CallbackQuery, state: FSMContext):
    # Placeholder for "Procurar" (search user) - not implemented in Phase 1
    await cb.answer("🚧 Funcionalidade de procura em desenvolvimento", show_alert=True)
    await cb.message.delete()
    await state.update_data(menu_msg_id=None, menu_chat_id=None)

@router.callback_query(StateFilter(AdminMenuStates.USERS), F.data == "users:add")
async def start_add_user(cb: CallbackQuery, state: FSMContext):
    """
    Handler for selecting "Adicionar" in the admin Users menu.
    Initiates the add user flow by asking for user type.
    """
    await cb.answer()
    try:
        await cb.message.delete()
    except exceptions.TelegramBadRequest:
        pass
    await state.update_data(menu_msg_id=None, menu_chat_id=None)
    # Enter the add user FSM flow
    await state.set_state(AdminMenuStates.USERS_ADD)
    await state.set_state(AddUserStates.CHOOSING_ROLE)
    msg = await cb.message.answer("👤 *Adicionar Utilizador*\nPor favor, selecione o *tipo* de utilizador:",
                                  reply_markup=build_user_type_kbd(), parse_mode="Markdown")
    # Initialize lists to track messages for deletion (privacy)
    await state.update_data(menu_msg_id=msg.message_id, menu_chat_id=msg.chat.id)
    start_menu_timeout(cb.bot, msg, state)

@router.callback_query(StateFilter(AddUserStates.CHOOSING_ROLE), F.data.startswith("role:"))
async def choose_user_type(cb: CallbackQuery, state: FSMContext):
    """
    Handles selection of user type (role).
    Saves the chosen role and asks for the first name.
    """
    role_name = cb.data.split(":", 1)[1]  # e.g. 'patient', 'caregiver', etc.
    await state.update_data(chosen_role=role_name)
    await cb.answer()
    try:
        await cb.message.delete()
    except exceptions.TelegramBadRequest:
        pass
    await state.set_state(AddUserStates.FIRST_NAME)
    prompt_msg = await cb.message.answer("👉 *Primeiro(s) nome(s)* do utilizador:",
                                        reply_markup=ReplyKeyboardMarkup(
                                            keyboard=[[KeyboardButton("◀ Regressar à Opção Anterior"),
                                                       KeyboardButton("❌ Cancelar Processo de Adição")]],
                                            resize_keyboard=True, one_time_keyboard=True),
                                        parse_mode="Markdown")
    data = await state.get_data()
    bot_msgs: list = data.get("bot_msgs", [])
    bot_msgs.append(prompt_msg.message_id)
    await state.update_data(bot_msgs=bot_msgs)

@router.message(StateFilter(AddUserStates.FIRST_NAME))
async def get_first_name(message: Message, state: FSMContext):
    """
    Receives the first name(s) and asks for last name.
    """
    text = message.text.strip()
    if text.lower() == "cancelar processo de adição":
        return await cancel_add_user(message, state)
    if text.lower().startswith("regressar"):
        # Back from first name -> return to role selection
        try:
            await message.delete()
        except exceptions.TelegramBadRequest:
            pass
        data = await state.get_data()
        data.pop("chosen_role", None)
        await state.update_data(data)
        await state.set_state(AddUserStates.CHOOSING_ROLE)
        msg = await message.answer("Por favor, selecione o *tipo* de utilizador:",
                                   reply_markup=build_user_type_kbd(), parse_mode="Markdown")
        bot_msgs: list = data.get("bot_msgs", [])
        bot_msgs.append(msg.message_id)
        await state.update_data(bot_msgs=bot_msgs)
        return
    if not text:
        await message.answer("❗ *Nome inválido.* Por favor, indique o primeiro nome.", parse_mode="Markdown")
        return  # stay in FIRST_NAME
    await state.update_data(first_name=text)
    await state.set_state(AddUserStates.LAST_NAME)
    prompt_msg = await message.answer("👉 *Último(s) nome(s)* do utilizador:",
                                      reply_markup=ReplyKeyboardMarkup(
                                          keyboard=[[KeyboardButton("◀ Regressar à Opção Anterior"),
                                                     KeyboardButton("❌ Cancelar Processo de Adição")]],
                                          resize_keyboard=True, one_time_keyboard=True),
                                      parse_mode="Markdown")
    data = await state.get_data()
    user_msgs: list = data.get("user_msgs", [])
    user_msgs.append(message.message_id)
    bot_msgs: list = data.get("bot_msgs", [])
    bot_msgs.append(prompt_msg.message_id)
    await state.update_data(bot_msgs=bot_msgs, user_msgs=user_msgs)

@router.message(StateFilter(AddUserStates.LAST_NAME))
async def get_last_name(message: Message, state: FSMContext):
    """
    Receives the last name(s) and asks for date of birth.
    """
    text = message.text.strip()
    if text.lower() == "cancelar processo de adição":
        return await cancel_add_user(message, state)
    if text.lower().startswith("regressar"):
        # Back from last name -> go to first name
        try:
            await message.delete()
        except exceptions.TelegramBadRequest:
            pass
        data = await state.get_data()
        data.pop("first_name", None)
        await state.update_data(data)
        await state.set_state(AddUserStates.FIRST_NAME)
        prompt_msg = await message.answer("👉 *Primeiro(s) nome(s)* do utilizador:",
                                          reply_markup=ReplyKeyboardMarkup(
                                              keyboard=[[KeyboardButton("◀ Regressar à Opção Anterior"),
                                                         KeyboardButton("❌ Cancelar Processo de Adição")]],
                                              resize_keyboard=True, one_time_keyboard=True),
                                          parse_mode="Markdown")
        bot_msgs: list = data.get("bot_msgs", [])
        bot_msgs.append(prompt_msg.message_id)
        await state.update_data(bot_msgs=bot_msgs)
        return
    if not text:
        await message.answer("❗ *Nome inválido.* Por favor, indique o último nome.", parse_mode="Markdown")
        return
    await state.update_data(last_name=text)
    await state.set_state(AddUserStates.BIRTHDATE)
    prompt_msg = await message.answer("👉 *Data de Nascimento* (dd-MM-yyyy):",
                                      reply_markup=ReplyKeyboardMarkup(
                                          keyboard=[[KeyboardButton("◀ Regressar à Opção Anterior"),
                                                     KeyboardButton("❌ Cancelar Processo de Adição")]],
                                          resize_keyboard=True, one_time_keyboard=True),
                                      parse_mode="Markdown")
    data = await state.get_data()
    user_msgs: list = data.get("user_msgs", [])
    user_msgs.append(message.message_id)
    bot_msgs: list = data.get("bot_msgs", [])
    bot_msgs.append(prompt_msg.message_id)
    await state.update_data(bot_msgs=bot_msgs, user_msgs=user_msgs)

@router.message(StateFilter(AddUserStates.BIRTHDATE))
async def get_birthdate(message: Message, state: FSMContext):
    """
    Receives date of birth and asks for phone number (validates format).
    """
    text = message.text.strip()
    if text.lower() == "cancelar processo de adição":
        return await cancel_add_user(message, state)
    if text.lower().startswith("regressar"):
        # Back from birthdate -> go to last name
        try:
            await message.delete()
        except exceptions.TelegramBadRequest:
            pass
        data = await state.get_data()
        data.pop("last_name", None)
        await state.update_data(data)
        await state.set_state(AddUserStates.LAST_NAME)
        prompt_msg = await message.answer("👉 *Último(s) nome(s)* do utilizador:",
                                          reply_markup=ReplyKeyboardMarkup(
                                              keyboard=[[KeyboardButton("◀ Regressar à Opção Anterior"),
                                                         KeyboardButton("❌ Cancelar Processo de Adição")]],
                                              resize_keyboard=True, one_time_keyboard=True),
                                          parse_mode="Markdown")
        bot_msgs: list = data.get("bot_msgs", [])
        bot_msgs.append(prompt_msg.message_id)
        await state.update_data(bot_msgs=bot_msgs)
        return
    dob_str = text.replace("/", "-")
    try:
        day, month, year = map(int, dob_str.split("-"))
        dob = datetime.date(year, month, day)
    except Exception:
        await message.answer("❗ *Data inválida.* Use o formato dd-MM-aaaa.", parse_mode="Markdown")
        return
    if dob.year < 1900 or dob > datetime.date.today():
        await message.answer("❗ *Data de nascimento fora do intervalo válido (1900 até hoje).*", parse_mode="Markdown")
        return
    await state.update_data(birth_date=dob.strftime("%Y-%m-%d"))
    await state.set_state(AddUserStates.PHONE)
    prompt_msg = await message.answer("👉 *Número de telemóvel* (inclua indicativo do país, ex: +351):",
                                      reply_markup=ReplyKeyboardMarkup(
                                          keyboard=[[KeyboardButton("◀ Regressar à Opção Anterior"),
                                                     KeyboardButton("❌ Cancelar Processo de Adição")]],
                                          resize_keyboard=True, one_time_keyboard=True),
                                      parse_mode="Markdown")
    data = await state.get_data()
    user_msgs: list = data.get("user_msgs", [])
    user_msgs.append(message.message_id)
    bot_msgs: list = data.get("bot_msgs", [])
    bot_msgs.append(prompt_msg.message_id)
    await state.update_data(bot_msgs=bot_msgs, user_msgs=user_msgs)

@router.message(StateFilter(AddUserStates.PHONE))
async def get_phone(message: Message, state: FSMContext):
    """
    Receives phone number and asks for email (validates format for Portugal).
    """
    text = message.text.strip()
    if text.lower() == "cancelar processo de adição":
        return await cancel_add_user(message, state)
    if text.lower().startswith("regressar"):
        # Back from phone -> go to birthdate
        try:
            await message.delete()
        except exceptions.TelegramBadRequest:
            pass
        data = await state.get_data()
        data.pop("birth_date", None)
        await state.update_data(data)
        await state.set_state(AddUserStates.BIRTHDATE)
        prompt_msg = await message.answer("👉 *Data de Nascimento* (dd-MM-yyyy):",
                                          reply_markup=ReplyKeyboardMarkup(
                                              keyboard=[[KeyboardButton("◀ Regressar à Opção Anterior"),
                                                         KeyboardButton("❌ Cancelar Processo de Adição")]],
                                              resize_keyboard=True, one_time_keyboard=True),
                                          parse_mode="Markdown")
        bot_msgs: list = data.get("bot_msgs", [])
        bot_msgs.append(prompt_msg.message_id)
        await state.update_data(bot_msgs=bot_msgs)
        return
    raw_phone = re.sub(r"[^\d+]", "", text)
    if raw_phone.startswith("+"):
        raw_phone = raw_phone[1:]
    if raw_phone.startswith("00"):
        raw_phone = raw_phone[2:]
    if not raw_phone.isdigit() or not (7 <= len(raw_phone) <= 15) or raw_phone[0] == "0":
        await message.answer("❗ *Número de telemóvel inválido.* Indique um número válido (incluindo indicativo).", parse_mode="Markdown")
        return
    await state.update_data(phone_number=raw_phone)
    await state.set_state(AddUserStates.EMAIL)
    prompt_msg = await message.answer("👉 *Endereço de e-mail* do utilizador:",
                                      reply_markup=ReplyKeyboardMarkup(
                                          keyboard=[[KeyboardButton("◀ Regressar à Opção Anterior"),
                                                     KeyboardButton("❌ Cancelar Processo de Adição")]],
                                          resize_keyboard=True, one_time_keyboard=True),
                                      parse_mode="Markdown")
    data = await state.get_data()
    user_msgs: list = data.get("user_msgs", [])
    user_msgs.append(message.message_id)
    bot_msgs: list = data.get("bot_msgs", [])
    bot_msgs.append(prompt_msg.message_id)
    await state.update_data(bot_msgs=bot_msgs, user_msgs=user_msgs)

@router.message(StateFilter(AddUserStates.EMAIL))
async def get_email(message: Message, state: FSMContext):
    """
    Receives email and asks for address.
    """
    text = message.text.strip()
    if text.lower() == "cancelar processo de adição":
        return await cancel_add_user(message, state)
    if text.lower().startswith("regressar"):
        # Back from email -> go to phone
        try:
            await message.delete()
        except exceptions.TelegramBadRequest:
            pass
        data = await state.get_data()
        data.pop("phone_number", None)
        await state.update_data(data)
        await state.set_state(AddUserStates.PHONE)
        prompt_msg = await message.answer("👉 *Número de telemóvel* (inclua indicativo do país, ex: +351):",
                                          reply_markup=ReplyKeyboardMarkup(
                                              keyboard=[[KeyboardButton("◀ Regressar à Opção Anterior"),
                                                         KeyboardButton("❌ Cancelar Processo de Adição")]],
                                              resize_keyboard=True, one_time_keyboard=True),
                                          parse_mode="Markdown")
        bot_msgs: list = data.get("bot_msgs", [])
        bot_msgs.append(prompt_msg.message_id)
        await state.update_data(bot_msgs=bot_msgs)
        return
    email = text
    pattern = re.compile(r'^[^@]+@[^@]+\.[a-zA-Z]{2,}$')
    if not pattern.match(email):
        await message.answer("❗ *Endereço de e-mail inválido.* Por favor, tente novamente.", parse_mode="Markdown")
        return
    await state.update_data(email=email)
    await state.set_state(AddUserStates.ADDRESS)
    prompt_msg = await message.answer(
        "👉 *Morada* do utilizador (opcional – pode separar por vírgulas: País, Código Postal, Cidade, Rua, Número):",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton("◀ Regressar à Opção Anterior"),
                       KeyboardButton("❌ Cancelar Processo de Adição")]],
            resize_keyboard=True, one_time_keyboard=True),
        parse_mode="Markdown")
    data = await state.get_data()
    user_msgs: list = data.get("user_msgs", [])
    user_msgs.append(message.message_id)
    bot_msgs: list = data.get("bot_msgs", [])
    bot_msgs.append(prompt_msg.message_id)
    await state.update_data(bot_msgs=bot_msgs, user_msgs=user_msgs)

@router.message(StateFilter(AddUserStates.ADDRESS))
async def get_address(message: Message, state: FSMContext):
    """
    Receives address (optional) and asks for NIF (optional).
    """
    text = message.text.strip()
    if text.lower() == "cancelar processo de adição":
        return await cancel_add_user(message, state)
    if text.lower().startswith("regressar"):
        # Back from address -> go to email
        try:
            await message.delete()
        except exceptions.TelegramBadRequest:
            pass
        data = await state.get_data()
        data.pop("email", None)
        await state.update_data(data)
        await state.set_state(AddUserStates.EMAIL)
        prompt_msg = await message.answer("👉 *Endereço de e-mail* do utilizador:",
                                          reply_markup=ReplyKeyboardMarkup(
                                              keyboard=[[KeyboardButton("◀ Regressar à Opção Anterior"),
                                                         KeyboardButton("❌ Cancelar Processo de Adição")]],
                                              resize_keyboard=True, one_time_keyboard=True),
                                          parse_mode="Markdown")
        bot_msgs: list = data.get("bot_msgs", [])
        bot_msgs.append(prompt_msg.message_id)
        await state.update_data(bot_msgs=bot_msgs)
        return
    addr_input = text
    if addr_input == "" or addr_input.lower() == "saltar":
        await state.update_data(address=None)
    else:
        parts = [p.strip() for p in addr_input.split(",") if p.strip()]
        address_data = {}
        if len(parts) == 5:
            address_data["country"] = parts[0]
            address_data["postal_code"] = parts[1]
            address_data["city"] = parts[2]
            address_data["street"] = parts[3]
            address_data["street_number"] = parts[4]
        else:
            address_data["street"] = addr_input
        await state.update_data(address=address_data)
    await state.set_state(AddUserStates.NIF)
    prompt_msg = await message.answer("👉 *NIF* do utilizador (opcional, 9 dígitos; pode incluir 'PT'):",
                                      reply_markup=ReplyKeyboardMarkup(
                                          keyboard=[[KeyboardButton("◀ Regressar à Opção Anterior"),
                                                     KeyboardButton("❌ Cancelar Processo de Adição")]],
                                          resize_keyboard=True, one_time_keyboard=True),
                                      parse_mode="Markdown")
    data = await state.get_data()
    user_msgs: list = data.get("user_msgs", [])
    user_msgs.append(message.message_id)
    bot_msgs: list = data.get("bot_msgs", [])
    bot_msgs.append(prompt_msg.message_id)
    await state.update_data(bot_msgs=bot_msgs, user_msgs=user_msgs)

@router.message(StateFilter(AddUserStates.NIF))
async def get_nif(message: Message, state: FSMContext):
    """
    Receives NIF (optional) and then shows the summary for confirmation.
    """
    text = message.text.strip()
    if text.lower() == "cancelar processo de adição":
        return await cancel_add_user(message, state)
    if text.lower().startswith("regressar"):
        # Back from NIF -> go to address
        try:
            await message.delete()
        except exceptions.TelegramBadRequest:
            pass
        data = await state.get_data()
        data.pop("address", None)
        await state.update_data(data)
        await state.set_state(AddUserStates.ADDRESS)
        prompt_msg = await message.answer(
            "👉 *Morada* do utilizador (opcional – pode separar por vírgulas: País, Código Postal, Cidade, Rua, Número):",
            reply_markup=ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton("◀ Regressar à Opção Anterior"),
                           KeyboardButton("❌ Cancelar Processo de Adição")]],
                resize_keyboard=True, one_time_keyboard=True),
            parse_mode="Markdown")
        bot_msgs: list = data.get("bot_msgs", [])
        bot_msgs.append(prompt_msg.message_id)
        await state.update_data(bot_msgs=bot_msgs)
        return
    nif_input = text
    nif_value = None
    if nif_input and nif_input.lower() != "saltar":
        if nif_input.upper().startswith("PT"):
            nif_input = nif_input[2:]
        nif_input = nif_input.replace(" ", "")
        if nif_input.isdigit():
            if len(nif_input) == 9:
                digits = list(map(int, nif_input))
                checksum = sum(d * (9 - idx) for idx, d in enumerate(digits[:8])) % 11
                checkdigit = 0 if checksum == 0 or checksum == 1 else 11 - checksum
                if checkdigit != digits[8]:
                    await message.answer("❗ *NIF inválido.* Por favor, verifique o número.", parse_mode="Markdown")
                    return
                nif_value = "PT" + nif_input
            else:
                await message.answer("❗ *NIF inválido.* O NIF deve ter 9 dígitos.", parse_mode="Markdown")
                return
        else:
            await message.answer("❗ *NIF inválido.* Indique apenas os dígitos (e prefixo 'PT' se aplicável).", parse_mode="Markdown")
            return
    await state.update_data(nif=nif_value)
    data = await state.get_data()
    # Compose summary of all collected data
    role = data.get("chosen_role")
    role_display = {"patient": "Cliente", "caregiver": "Cuidador", "physiotherapist": "Fisioterapeuta",
                    "accountant": "Contabilista", "administrator": "Administrador"}.get(role, role)
    fname = data.get("first_name", "")
    lname = data.get("last_name", "")
    birth = data.get("birth_date", "")
    phone = data.get("phone_number", "")
    email = data.get("email", "")
    addr_data = data.get("address", None)
    if addr_data is None:
        addr_str = "_(não fornecida)_"
    elif isinstance(addr_data, dict):
        country = addr_data.get("country"); postal = addr_data.get("postal_code")
        city = addr_data.get("city"); street = addr_data.get("street"); number = addr_data.get("street_number")
        parts = [p for p in [street, number, postal, city, country] if p]
        addr_str = ", ".join(parts) if parts else "_(não fornecida)_"
    else:
        addr_str = str(addr_data)
    nif_text = data.get("nif", None)
    nif_str = nif_text if nif_text else "_(não fornecido)_"
    summary_text = (
        f"*Confirme os dados introduzidos:*\n"
        f"• Tipo: {role_display}\n"
        f"• Nome: {fname}\n"
        f"• Apelido: {lname}\n"
        f"• Nascimento: {birth if birth else '_(não fornecida)_'}\n"
        f"• Telemóvel: {phone}\n"
        f"• Email: {email}\n"
        f"• Morada: {addr_str}\n"
        f"• NIF: {nif_str}"
    )
    # Remove reply keyboard (we will show inline buttons for confirmation)
    remove_kb_msg = await message.answer(".", reply_markup=ReplyKeyboardRemove())
    try:
        await remove_kb_msg.delete()
    except exceptions.TelegramBadRequest:
        pass
    summary_msg = await message.answer(summary_text, reply_markup=InlineKeyboardMarkup(
                                            inline_keyboard=[
                                                [InlineKeyboardButton(text="✅ Confirmar", callback_data="usersadd:confirm")],
                                                [InlineKeyboardButton(text="✏️ Editar", callback_data="usersadd:edit")],
                                                [InlineKeyboardButton(text="❌ Cancelar", callback_data="usersadd:cancel")]
                                            ]),
                                        parse_mode="Markdown")
    user_msgs: list = data.get("user_msgs", [])
    user_msgs.append(message.message_id)
    bot_msgs: list = data.get("bot_msgs", [])
    bot_msgs.append(summary_msg.message_id)
    await state.update_data(bot_msgs=bot_msgs, user_msgs=user_msgs, summary_msg_id=summary_msg.message_id)
    await state.set_state(AddUserStates.CONFIRM)

@router.callback_query(StateFilter(AddUserStates.CONFIRM), F.data == "usersadd:confirm")
async def confirm_new_user(cb: CallbackQuery, state: FSMContext):
    """
    Final confirmation: inserts the new user into the database and ends the flow.
    """
    await cb.answer()
    data = await state.get_data()
    pool = await get_pool()
    # Insert user and related info into DB
    user_id = await q.create_user(pool, data["first_name"], data["last_name"], data.get("nif"))
    await q.add_user_role(pool, user_id, data["chosen_role"])
    if data.get("phone_number"):
        await q.add_phone(pool, user_id, data["phone_number"], is_primary=True)
    if data.get("email"):
        await q.add_email(pool, user_id, data["email"], is_primary=True)
    if data.get("address"):
        addr = data["address"]
        if isinstance(addr, dict):
            await q.add_address(pool, user_id,
                                country=addr.get("country"),
                                city=addr.get("city"),
                                postal_code=addr.get("postal_code"),
                                street=addr.get("street"),
                                street_number=addr.get("street_number"),
                                is_primary=True)
        else:
            await q.add_address(pool, user_id, street=str(addr), is_primary=True)
    # Notify success
    try:
        await cb.message.edit_text("✅ *Utilizador adicionado com sucesso!*", parse_mode="Markdown")
    except exceptions.TelegramBadRequest:
        await cb.message.answer("✅ *Utilizador adicionado com sucesso!*", parse_mode="Markdown")
    # Clean up all collected messages from the chat for privacy
    await cleanup_flow_messages(state, cb.message.chat.id)
    await state.clear()

@router.callback_query(StateFilter(AddUserStates.CONFIRM), F.data == "usersadd:cancel")
async def cancel_from_summary(cb: CallbackQuery, state: FSMContext):
    """
    Cancel the addition at confirmation stage.
    """
    await cb.answer()
    try:
        await cb.message.edit_text("❌ *Operação cancelada.*", parse_mode="Markdown")
    except exceptions.TelegramBadRequest:
        await cb.message.answer("❌ *Operação cancelada.*", parse_mode="Markdown")
    await cleanup_flow_messages(state, cb.message.chat.id)
    await state.clear()

@router.callback_query(StateFilter(AddUserStates.CONFIRM), F.data == "usersadd:edit")
async def edit_fields_request(cb: CallbackQuery, state: FSMContext):
    """
    Handle 'Editar' action: show list of fields to edit.
    """
    await cb.answer()
    fields_kbd = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Tipo de Utilizador", callback_data="edit:role")],
        [InlineKeyboardButton("Primeiro Nome", callback_data="edit:first_name")],
        [InlineKeyboardButton("Último Nome", callback_data="edit:last_name")],
        [InlineKeyboardButton("Data Nascimento", callback_data="edit:birth_date")],
        [InlineKeyboardButton("Telemóvel", callback_data="edit:phone")],
        [InlineKeyboardButton("Email", callback_data="edit:email")],
        [InlineKeyboardButton("Morada", callback_data="edit:address")],
        [InlineKeyboardButton("NIF", callback_data="edit:nif")],
        [InlineKeyboardButton("⬅️ Voltar", callback_data="edit:back")],
    ])
    try:
        await cb.message.edit_text("✏️ *Editar campo:*", reply_markup=fields_kbd, parse_mode="Markdown")
    except exceptions.TelegramBadRequest:
        await cb.message.answer("✏️ *Editar campo:*", reply_markup=fields_kbd, parse_mode="Markdown")
    await state.set_state(AddUserStates.EDIT_FIELD)

@router.callback_query(StateFilter(AddUserStates.EDIT_FIELD), F.data.startswith("edit:"))
async def choose_field_to_edit(cb: CallbackQuery, state: FSMContext):
    """
    Handle selection of a specific field to edit.
    """
    await cb.answer()
    field = cb.data.split(":", 1)[1]
    if field == "back":
        # Return to summary view without changes
        data = await state.get_data()
        summary_msg_id = data.get("summary_msg_id")
        # Recompose summary text from current data
        role = data.get("chosen_role")
        role_display = {"patient": "Cliente", "caregiver": "Cuidador", "physiotherapist": "Fisioterapeuta",
                        "accountant": "Contabilista", "administrator": "Administrador"}.get(role, role)
        fname = data.get("first_name", "")
        lname = data.get("last_name", "")
        birth = data.get("birth_date", "")
        phone = data.get("phone_number", "")
        email = data.get("email", "")
        addr_data = data.get("address", None)
        if addr_data is None:
            addr_str = "_(não fornecida)_"
        elif isinstance(addr_data, dict):
            country = addr_data.get("country"); postal = addr_data.get("postal_code")
            city = addr_data.get("city"); street = addr_data.get("street"); number = addr_data.get("street_number")
            parts = [p for p in [street, number, postal, city, country] if p]
            addr_str = ", ".join(parts) if parts else "_(não fornecida)_"
        else:
            addr_str = str(addr_data)
        nif_text = data.get("nif", None)
        nif_str = nif_text if nif_text else "_(não fornecido)_"
        summary_text = (
            f"*Confirme os dados introduzidos:*\n"
            f"• Tipo: {role_display}\n"
            f"• Nome: {fname}\n"
            f"• Apelido: {lname}\n"
            f"• Nascimento: {birth if birth else '_(não fornecida)_'}\n"
            f"• Telemóvel: {phone}\n"
            f"• Email: {email}\n"
            f"• Morada: {addr_str}\n"
            f"• NIF: {nif_str}"
        )
        try:
            await cb.message.edit_text(summary_text, reply_markup=InlineKeyboardMarkup(
                                            inline_keyboard=[
                                                [InlineKeyboardButton(text="✅ Confirmar", callback_data="usersadd:confirm")],
                                                [InlineKeyboardButton(text="✏️ Editar", callback_data="usersadd:edit")],
                                                [InlineKeyboardButton(text="❌ Cancelar", callback_data="usersadd:cancel")]
                                            ]),
                                        parse_mode="Markdown")
        except exceptions.TelegramBadRequest:
            await cb.message.answer(summary_text, reply_markup=InlineKeyboardMarkup(
                                            inline_keyboard=[
                                                [InlineKeyboardButton(text="✅ Confirmar", callback_data="usersadd:confirm")],
                                                [InlineKeyboardButton(text="✏️ Editar", callback_data="usersadd:edit")],
                                                [InlineKeyboardButton(text="❌ Cancelar", callback_data="usersadd:cancel")]
                                            ]),
                                        parse_mode="Markdown")
        await state.set_state(AddUserStates.CONFIRM)
        return
    # Proceed to edit the specified field
    try:
        await cb.message.delete()
    except exceptions.TelegramBadRequest:
        pass
    await state.update_data(edit_field=field)
    if field == "role":
        await state.set_state(AddUserStates.CHOOSING_ROLE)
        msg = await cb.message.answer("👤 Selecione o *novo tipo* de utilizador:", 
                                      reply_markup=build_user_type_kbd(), parse_mode="Markdown")
        data = await state.get_data()
        bot_msgs: list = data.get("bot_msgs", [])
        bot_msgs.append(msg.message_id)
        await state.update_data(bot_msgs=bot_msgs)
    else:
        field_state_map = {
            "first_name": (AddUserStates.FIRST_NAME, "👉 *Primeiro(s) nome(s)* (novo):"),
            "last_name": (AddUserStates.LAST_NAME, "👉 *Último(s) nome(s)* (novo):"),
            "birth_date": (AddUserStates.BIRTHDATE, "👉 *Data de Nascimento* (dd-MM-yyyy):"),
            "phone": (AddUserStates.PHONE, "👉 *Número de telemóvel* (novo):"),
            "email": (AddUserStates.EMAIL, "👉 *Endereço de e-mail* (novo):"),
            "address": (AddUserStates.ADDRESS, "👉 *Morada* do utilizador (nova, formato: País, Código Postal, Cidade, Rua, Número):"),
            "nif": (AddUserStates.NIF, "👉 *NIF* do utilizador (novo):"),
        }
        if field in field_state_map:
            target_state, prompt_text = field_state_map[field]
            await state.set_state(target_state)
            prompt_msg = await cb.message.answer(prompt_text,
                                                 reply_markup=ReplyKeyboardMarkup(
                                                     keyboard=[[KeyboardButton("◀ Regressar à Opção Anterior"),
                                                                KeyboardButton("❌ Cancelar Processo de Adição")]],
                                                     resize_keyboard=True, one_time_keyboard=True),
                                                 parse_mode="Markdown")
            data = await state.get_data()
            bot_msgs: list = data.get("bot_msgs", [])
            bot_msgs.append(prompt_msg.message_id)
            await state.update_data(bot_msgs=bot_msgs)

@router.callback_query(StateFilter(AddUserStates.CHOOSING_ROLE), F.data == "users:add_back")
async def back_to_user_menu(cb: CallbackQuery, state: FSMContext):
    """
    Handler to return from the role selection back to the 'Utilizadores' submenu.
    """
    await cb.answer()
    await state.set_state(AdminMenuStates.USERS)
    await _replace_menu(cb, state, "👥 *Utilizadores* — seleccione:", _users_kbd())

@router.message(StateFilter(AddUserStates))
async def cancel_add_user(message: Message, state: FSMContext):
    """
    Cancel the addition process (triggered when user presses Cancel at any step).
    """
    try:
        await message.answer("❌ *Operação cancelada.*", parse_mode="Markdown")
    except exceptions.TelegramBadRequest:
        pass
    await cleanup_flow_messages(state, message.chat.id, message.bot)
    await state.clear()


async def cleanup_flow_messages(state: FSMContext, chat_id: int, bot: Bot):
    """
    Deletes all tracked messages from the add user flow to protect privacy.
    """
    data = await state.get_data()
    for msg_id in data.get("bot_msgs", []):
        try:
            await bot.delete_message(chat_id, msg_id)
        except exceptions.TelegramBadRequest:
            continue
    for msg_id in data.get("user_msgs", []):
        try:
            await bot.delete_message(chat_id, msg_id)
        except exceptions.TelegramBadRequest:
            continue
