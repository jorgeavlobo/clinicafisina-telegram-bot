# bot/middlewares/active_menu_middleware.py
from aiogram import CancelHandler
from aiogram.dispatcher.middlewares.base import BaseMiddleware
from aiogram import exceptions
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext

class ActiveMenuMiddleware(BaseMiddleware):
    """
    Middleware to ensure that only active menus (inline keyboards) can be interacted with.
    It blocks any callback query from an inactive or expired menu, providing a warning to the user.

    This middleware checks the stored active menu message ID in the user's FSM state (state data)
    and compares it with the incoming callback query's message. If they don't match,
    the callback is considered invalid (the menu is no longer active).

    When an invalid interaction is detected:
    - A pop-up warning "⚠️ Este menu já não está activo." is shown to the user.
    - The old menu message is removed from the chat (ignored if it no longer exists or cannot be deleted).

    This design is modular and easily expandable. By centralizing the active menu validation here,
    all current and future menus are automatically protected without needing to repeat checks in every handler.
    """
    async def __call__(self, handler, event, data):
        # Only process if the update is a CallbackQuery (interaction with an inline menu)
        cb: CallbackQuery
        if isinstance(event, CallbackQuery):
            cb = event
        elif hasattr(event, "callback_query") and event.callback_query:
            # If event is an Update containing a CallbackQuery (outer middleware scenario)
            cb = event.callback_query
        else:
            # Not a callback query event, continue to the next handler without interruption
            return await handler(event, data)

        # Retrieve FSM context (state) and stored data for this user/chat
        state: FSMContext = data.get("state")
        state_data = await state.get_data() if state else {}
        active_msg_id = state_data.get("menu_msg_id")
        active_chat_id = state_data.get("menu_chat_id")

        # Check if the callback query's message matches the active menu message
        if not active_msg_id or not active_chat_id or \
           cb.message.message_id != active_msg_id or cb.message.chat.id != active_chat_id:
            # This callback is from an inactive/old menu
            try:
                # Attempt to delete the old menu message from the chat
                await cb.message.delete()
            except exceptions.TelegramBadRequest:
                # If the message is too old or already removed, ignore the error
                pass
            # Inform the user that this menu is no longer active
            await cb.answer("⚠️ Este menu já não está activo.", show_alert=True)
            # Stop further processing of this callback query
            raise CancelHandler()

        # If the menu is active, proceed with the normal handler chain
        return await handler(event, data)
