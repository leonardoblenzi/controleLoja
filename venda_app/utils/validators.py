"""
Funções de validação para inputs do usuário.

Estas funções podem ser utilizadas na interface gráfica para
verificar campos obrigatórios e tipos de dados antes de gravar no
banco de dados.
"""

from __future__ import annotations

from datetime import datetime

def is_non_empty(text: str) -> bool:
    """Verifica se uma string não é vazia nem composta apenas por espaços."""
    return bool(text and text.strip())


def is_positive_integer(value: str) -> bool:
    """Verifica se o valor fornecido representa um inteiro positivo."""
    try:
        return int(value) > 0
    except (ValueError, TypeError):
        return False


def is_non_negative_float(value: str) -> bool:
    """Verifica se o valor fornecido representa um número de ponto flutuante >= 0."""
    try:
        return float(value) >= 0
    except (ValueError, TypeError):
        return False


def parse_flexible_date(text: str) -> str:
    """Converte várias formas de data para ISO (YYYY-MM-DD).

    Aceita, por exemplo:
    - YYYY-MM-DD
    - DD/MM/YYYY
    - DD-MM-YYYY
    - YYYY/MM/DD
    - DD.MM.YYYY
    """
    s = (text or "").strip()
    if not s:
        raise ValueError("Data vazia")

    s = s.replace("\\\\", "/")

    fmts = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%d.%m.%Y",
    ]

    for fmt in fmts:
        try:
            dt = datetime.strptime(s, fmt)
            return dt.date().isoformat()
        except ValueError:
            continue

    raise ValueError("Formato de data inválido. Use 21/05/2000, 21-05-2000 ou 2000-05-21.")


def format_iso_to_br(iso_date: str) -> str:
    """Converte YYYY-MM-DD para DD/MM/YYYY para exibição."""
    s = (iso_date or "").strip()
    if not s:
        return ""
    try:
        dt = datetime.strptime(s, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except ValueError:
        return s


__all__ = [
    "is_non_empty",
    "is_positive_integer",
    "is_non_negative_float",
    "parse_flexible_date",
    "format_iso_to_br",
]