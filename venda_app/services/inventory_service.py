"""venda_app.services.inventory_service

Serviços para cálculos de estoque.

Regra do projeto:
  - Estoque é SEMPRE controlado por variação (product_variants).
  - Mesmo produtos sem variação têm uma variação "Única".
"""

from __future__ import annotations

from typing import Dict, List

import sqlite3


def get_variant_stock_levels(conn: sqlite3.Connection) -> Dict[int, int]:
    """Retorna um mapa variant_id -> estoque atual."""
    query = """
        SELECT v.id AS variant_id,
               COALESCE(SUM(
                   CASE
                       WHEN sm.move_type = 'IN'  THEN sm.qty
                       WHEN sm.move_type = 'OUT' THEN -sm.qty
                       WHEN sm.move_type = 'ADJ' THEN sm.qty
                       ELSE 0
                   END
               ), 0) AS stock
          FROM product_variants v
     LEFT JOIN stock_moves sm ON sm.variant_id = v.id
      GROUP BY v.id
    """
    cur = conn.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    return {int(r["variant_id"]): int(r["stock"]) for r in rows}


def get_product_stock_levels(conn: sqlite3.Connection) -> Dict[int, int]:
    """Retorna um mapa product_id -> estoque total (soma das variações ativas)."""
    query = """
        SELECT p.id AS product_id,
               COALESCE(SUM(
                   CASE
                       WHEN sm.move_type = 'IN'  THEN sm.qty
                       WHEN sm.move_type = 'OUT' THEN -sm.qty
                       WHEN sm.move_type = 'ADJ' THEN sm.qty
                       ELSE 0
                   END
               ), 0) AS stock
          FROM products p
          JOIN product_variants v ON v.product_id = p.id AND v.is_active = 1
     LEFT JOIN stock_moves sm ON sm.variant_id = v.id
      GROUP BY p.id
    """
    cur = conn.cursor()
    cur.execute(query)
    rows = cur.fetchall()
    return {int(r["product_id"]): int(r["stock"]) for r in rows}


def get_stock_table_rows(conn: sqlite3.Connection) -> List[sqlite3.Row]:
    """Retorna linhas completas para tela de estoque (por variação)."""
    query = """
        SELECT
            c.name AS category_name,
            p.id AS product_id,
            p.sku AS product_sku,
            p.name AS product_name,
            p.stock_min,
            p.is_active AS product_active,
            p.variant_attribute_name,

            v.id AS variant_id,
            v.variant_sku,
            v.variant_value,
            v.is_default,
            v.is_active AS variant_active,

            COALESCE(SUM(
                CASE
                    WHEN sm.move_type = 'IN'  THEN sm.qty
                    WHEN sm.move_type = 'OUT' THEN -sm.qty
                    WHEN sm.move_type = 'ADJ' THEN sm.qty
                    ELSE 0
                END
            ), 0) AS stock

        FROM products p
        JOIN categories c ON c.id = p.category_id
        JOIN product_variants v ON v.product_id = p.id
        LEFT JOIN stock_moves sm ON sm.variant_id = v.id
        GROUP BY v.id
        ORDER BY p.name, v.is_default DESC, v.variant_value
    """
    cur = conn.cursor()
    cur.execute(query)
    return cur.fetchall()


__all__ = [
    "get_variant_stock_levels",
    "get_product_stock_levels",
    "get_stock_table_rows",
]
