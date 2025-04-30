# bot/utils/fsm_helpers.py
from aiogram.fsm.context import FSMContext

async def clear_keep_role(state: FSMContext) -> None:
    """
    Limpa o FSM mas preserva «active_role», para que o
    RoleCheckMiddleware continue a reconhecer o perfil escolhido.
    """
    data = await state.get_data()
    active = data.get("active_role")
    await state.clear()
    if active:
        await state.update_data(active_role=active)
