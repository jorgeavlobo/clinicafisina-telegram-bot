# bot/utils/fsm_helpers.py
from aiogram.fsm.context import FSMContext

__all__ = ["clear_keep_role"]

async def clear_keep_role(state: FSMContext) -> None:
    """
    Limpa toda a FSM mas mantém «active_role».
    Remove também chaves temporárias (_menu_timeout_task, menu_msg_id…).
    """
    data = await state.get_data()
    role = data.get("active_role")          # pode ser None
    await state.clear()

    # repõe só o que interessa
    if role:
        await state.update_data(active_role=role)
