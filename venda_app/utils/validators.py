"""
Funções de validação para inputs do usuário.

Estas funções podem ser utilizadas na interface gráfica para
verificar campos obrigatórios e tipos de dados antes de gravar no
banco de dados.
"""

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


__all__ = ["is_non_empty", "is_positive_integer", "is_non_negative_float"]