# bot/utils/fsm_helpers.py
"""
Helpers para lidar com FSM sem perder o `active_role`
que o RoleCheckMiddleware precisa para autorizar o utilizador.
"""

from aiogram.fsm.context import FSMContext


async def clear_keep_role(state: FSMContext) -> None:
    """
    Limpa TODO o estado mas, se existir, volta a gravar «active_role».
    Usa-a sempre em vez de `state.clear()` depois de o perfil
    já estar escolhido.
    """
    data = await state.get_data()
    active = data.get("active_role")
    await state.clear()
    if active:
        await state.update_data(active_role=active)
