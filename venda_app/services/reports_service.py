"""
Serviços de relatórios e DRE.

Este módulo contém funções de alto nível para gerar relatórios
financeiros, como a Demonstração de Resultados (DRE) simples por
período. As implementações são esboços e podem ser expandidas.
"""

from typing import Dict
import sqlite3


def get_financial_summary(conn: sqlite3.Connection, date_from: str, date_to: str) -> Dict[str, float]:
    """Calcula um resumo financeiro entre duas datas (inclusivas).

    O resumo inclui receita líquida, custo das vendas, lucro bruto,
    total de gastos e resultado final (lucro líquido).

    Args:
        conn (sqlite3.Connection): Conexão com o banco de dados.
        date_from (str): Data inicial no formato YYYY-MM-DD.
        date_to (str): Data final no formato YYYY-MM-DD.

    Returns:
        Dict[str, float]: Um dicionário com chaves `revenue`, `cost`,
            `profit`, `expenses` e `result`.
    """
    cur = conn.cursor()
    # Soma os valores de venda no intervalo
    cur.execute(
        """
        SELECT
            COALESCE(SUM(total_net), 0) AS revenue,
            COALESCE(SUM(total_cost), 0) AS cost,
            COALESCE(SUM(total_profit), 0) AS profit
        FROM sales
        WHERE sale_date BETWEEN ? AND ?
        """,
        (date_from, date_to),
    )
    revenue, cost, profit = cur.fetchone()

    # Soma os gastos no intervalo (tabela expenses)
    # Compra de estoque NÃO entra aqui (é contabilizada via Movimentações).
    cur.execute(
        """
        SELECT COALESCE(SUM(amount), 0) AS expenses
        FROM expenses
        WHERE exp_date BETWEEN ? AND ?
          AND UPPER(category) <> 'COMPRA_ESTOQUE'
        """,
        (date_from, date_to),
    )
    expenses = cur.fetchone()[0]

    # Compras registradas via movimentações (IN + COMPRA) contam como gasto
    cur.execute(
        """
        SELECT COALESCE(SUM(qty * unit_cost), 0) AS purchases
          FROM stock_moves
         WHERE move_type = 'IN'
           AND UPPER(reason) = 'COMPRA'
           AND move_date BETWEEN ? AND ?
        """,
        (date_from, date_to),
    )
    purchases = cur.fetchone()[0]

    expenses_total = float(expenses) + float(purchases)

    result = float(profit) - expenses_total
    return {
        "revenue": revenue,
        "cost": cost,
        "profit": profit,
        "expenses": expenses_total,
        "result": result,
    }


__all__ = ["get_financial_summary"]