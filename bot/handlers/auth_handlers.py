# bot/handlers/auth_handlers.py
@router.message(CommandStart())
async def start(message: Message, state: FSMContext):
    pool = await get_pool()
    user = await q.get_user_by_telegram_id(pool, message.from_user.id)

    if user:
        roles = await q.get_user_roles(pool, user["user_id"])

        # ─── limpa o FSM **mas preserva** o id da última mensagem-menu ───
        data = await state.get_data()
        last_menu_id  = data.get("menu_msg_id")
        last_menu_chat = data.get("menu_chat_id")
        await state.clear()
        if last_menu_id and last_menu_chat:
            await state.update_data(
                menu_msg_id=last_menu_id,
                menu_chat_id=last_menu_chat,
            )

        # envia (e o próprio show_menu já vai apagar o antigo, se existir)
        await show_menu(
            bot     = message.bot,
            chat_id = message.chat.id,
            state   = state,
            roles   = roles,
        )
    else:
        await flow.start_onboarding(message, state)
