# bot/handlers/debug_fsm_handlers.py
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
import json

router = Router(name="debug-fsm")

@router.message(Command("dumpfsm"))
async def dump_fsm(msg: Message, state: FSMContext):
    data  = await state.get_data()
    cur   = await state.get_state()
    txt   = (
        f"*FSM state*: `{cur}`\n"
        f"*FSM data*:\n```json\n{json.dumps(data, indent=2, ensure_ascii=False)}```"
    )
    await msg.answer(txt, parse_mode="Markdown")
