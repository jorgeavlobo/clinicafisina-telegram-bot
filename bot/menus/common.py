# bot/menus/common.py
"""
Helpers comuns para todos os menus inline.
Neste momento só existe `back_button`, mas aqui também poderás
colocar outros utilitários partilhados (por ex. botão “Fechar”).
"""

from aiogram.types import InlineKeyboardButton

__all__ = ["back_button"]

def back_button() -> InlineKeyboardButton:
    """
    🔙 Botão 'Voltar' — devolve sempre a mesma callback-data ('back').
    Usa-se em sub-menus para regressar ao menu anterior.
    """
    return InlineKeyboardButton(text="🔙 Voltar", callback_data="back")
