# bot/utils/validators.py
"""
Funções utilitárias de validação.
Todas levantam ValueError com mensagem legível em caso de input inválido.
"""

import re
from datetime import datetime
from typing import Tuple


# ───────────── data (dd-MM-yyyy ou dd/MM/yyyy) ─────────────
DATE_RE = re.compile(r"^(?P<d>\d{2})[-/](?P<m>\d{2})[-/](?P<y>\d{4})$")


def valid_date(date_str: str) -> datetime.date:
    m = DATE_RE.match(date_str.strip())
    if not m:
        raise ValueError("Formato inválido (usa dd-MM-aaaa).")
    d, m_, y = map(int, (m["d"], m["m"], m["y"]))
    try:
        dt = datetime(year=y, month=m_, day=d).date()
    except ValueError:
        raise ValueError("Data impossível.")
    if dt.year < 1900 or dt > datetime.now().date():
        raise ValueError("Ano fora do intervalo 1900-hoje.")
    return dt


# ───────────── e-mail ─────────────
EMAIL_RE = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w{2,}$")


def valid_email(email: str) -> str:
    if not EMAIL_RE.match(email.strip()):
        raise ValueError("Endereço de e-mail inválido.")
    return email.strip()


# ───────────── telemóvel Portugal ─────────────
def valid_pt_phone(num: str) -> str:
    if not num.isdigit() or len(num) != 9 or not num.startswith("9"):
        raise ValueError("Telemóvel PT deve ter 9 dígitos e começar por 9.")
    return num


# ───────────── NIF Portugal ─────────────
def valid_pt_nif(nif: str) -> str:
    if not (nif.isdigit() and len(nif) == 9):
        raise ValueError("NIF PT deve ter 9 dígitos.")
    digits = list(map(int, nif))
    check = sum(d * (9 - i) for i, d in enumerate(digits[:-1])) % 11
    check = 0 if check in (0, 1) else 11 - check
    if check != digits[-1]:
        raise ValueError("NIF PT inválido.")
    return nif
