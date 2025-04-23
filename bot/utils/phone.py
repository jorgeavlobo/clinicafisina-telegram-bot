# bot/utils/phone.py
import re

E164_DIGITS = re.compile(r"^\+?([1-9]\d{6,14})$")

def cleanse(raw: str) -> str:
    """
    Converte número E.164 para dígitos-apenas.
    Aceita com ou sem '+'. Lança ValueError se inválido.
    """
    m = E164_DIGITS.match(raw.strip())
    if not m:
        raise ValueError(f"Invalid phone number: {raw!r}")
    return m.group(1)          # só dígitos
