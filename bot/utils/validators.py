# bot/utils/validators.py
"""
Validações e normalizações usadas em todo o projecto.

Cada função levanta ValueError com mensagem legível quando o input é inválido.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import datetime, date
from typing import Tuple

# ─────────────────────────── datas ────────────────────────────
_DATE_RE = re.compile(r"^(?P<d>\d{2})[-/](?P<m>\d{2})[-/](?P<y>\d{4})$")


def valid_date(value: str) -> date:
    """
    Aceita 'dd-MM-aaaa' ou 'dd/MM/aaaa'.
    Garante ano ≥ 1900 e não no futuro.
    """
    m = _DATE_RE.fullmatch(value.strip())
    if not m:
        raise ValueError("Formato inválido (use dd-MM-aaaa).")
    d, mth, y = map(int, (m["d"], m["m"], m["y"]))
    try:
        dt = datetime(year=y, month=mth, day=d).date()
    except ValueError:
        raise ValueError("Data impossível.")
    if not (1900 <= dt.year <= datetime.now().year):
        raise ValueError("Ano fora do intervalo 1900-hoje.")
    return dt


# ─────────────────────────── e-mail ────────────────────────────
_EMAIL_RE = re.compile(r"^[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,}$")


def _strip_invisible(s: str) -> str:
    """Remove chars categoria Cf (format) e espaços invisíveis."""
    return "".join(ch for ch in s if unicodedata.category(ch)[0] != "C")

def valid_email(value: str) -> str:
    value = _strip_invisible(value).strip()
    if not _EMAIL_RE.fullmatch(value):
        raise ValueError("Endereço de e-mail inválido.")
    return value.lower()


# ───────────────────── telemóvel Portugal ─────────────────────
def valid_pt_phone(num: str) -> str:
    """
    Valida número de telemóvel português (9 dígitos começando por 9).
    Devolve o número tal como veio (apenas dígitos).
    """
    if not num.isdigit() or len(num) != 9 or not num.startswith("9"):
        raise ValueError("Telemóvel PT deve ter 9 dígitos e começar por 9.")
    return num


# ─────────────────────── NIF Portugal ────────────────────────
def valid_pt_nif(nif: str) -> str:
    """
    Valida NIF português usando algoritmo de controlo.
    """
    if not (nif.isdigit() and len(nif) == 9):
        raise ValueError("NIF PT deve ter 9 dígitos.")
    digs = list(map(int, nif))
    chk = sum(d * (9 - i) for i, d in enumerate(digs[:-1])) % 11
    chk = 0 if chk in (0, 1) else 11 - chk
    if chk != digs[-1]:
        raise ValueError("NIF PT inválido.")
    return nif


# ──────────────── indicativo de país genérico ────────────────
_CC_RE = re.compile(r"^(?:\+|00)?(\d{1,4})$")


def normalize_phone_cc(raw: str) -> Tuple[str, str]:
    """
    Normaliza o indicativo do país.

    Exemplos aceites  →  devolve («display», «digits»)
        '+351'  → ('+351', '351')
        '351'   → ('+351', '351')
        '00351' → ('+351', '351')
        '+44'   → ('+44',  '44')

    Levanta ValueError se contiver algo além de dígitos, '+' ou '00'.
    """
    raw = raw.strip()
    m = _CC_RE.fullmatch(raw)
    if not m:
        raise ValueError("Indicativo deve conter apenas dígitos, '+', ou '00'.")
    digits = m.group(1).lstrip("0") or "0"
    return f"+{digits}", digits
