"""venda_app.services.sales_service

Serviço para registrar vendas e seus itens.

Regra: itens e estoque são SEMPRE por variação (variant_id).
Mesmo produtos sem variação têm uma variação "Única".
"""

from __future__ import annotations

from typing import Any, Dict, List

import sqlite3

from ..db.repositories import SaleRepository, StockMoveRepository, VariantRepository


def create_sale(
    conn: sqlite3.Connection,
    sale_date: str,
    channel: str,
    order_ref: str,
    customer_name: str,
    notes: str,
    items: List[Dict[str, Any]],
) -> int:
    """Registra uma nova venda.

    Args:
        items: lista com chaves:
            - sku (variant_sku)
            - qty
            - unit_price
            - fees
            - discount

    Returns:
        sale_id
    """

    totals = {
        "total_gross": 0.0,
        "total_fees": 0.0,
        "total_discount": 0.0,
        "total_net": 0.0,
        "total_cost": 0.0,
        "total_profit": 0.0,
    }

    sale_items_data: List[Dict[str, Any]] = []
    stock_moves_data: List[Dict[str, Any]] = []

    for item in items:
        variant_sku = str(item.get("sku", "")).strip()
        qty = int(item.get("qty", 0))
        unit_price = float(item.get("unit_price", 0))
        fees = float(item.get("fees", 0))
        discount = float(item.get("discount", 0))

        if not variant_sku:
            raise ValueError("SKU do item não informado")
        if qty <= 0:
            raise ValueError("Quantidade deve ser maior que zero")

        vrow = VariantRepository.get_variant_by_sku(conn, variant_sku)
        if not vrow:
            raise ValueError(f"Variação/SKU não encontrado: {variant_sku}")
        if not bool(vrow["is_active"]):
            raise ValueError(f"Variação inativa: {variant_sku}")

        variant_id = int(vrow["variant_id"])

        # custo unitário: override > custo padrão do produto
        unit_cost = float(vrow["cost_override"]) if vrow["cost_override"] is not None else float(vrow["cost_default"])

        gross = qty * unit_price
        net = gross - fees - discount
        cost = qty * unit_cost
        profit = net - cost

        totals["total_gross"] += gross
        totals["total_fees"] += fees
        totals["total_discount"] += discount
        totals["total_net"] += net
        totals["total_cost"] += cost
        totals["total_profit"] += profit

        sale_items_data.append(
            {
                "sale_id": None,
                "variant_id": variant_id,
                "qty": qty,
                "unit_price": unit_price,
                "unit_cost": unit_cost,
                "fees": fees,
                "discount": discount,
                "net": net,
                "profit": profit,
            }
        )

        stock_moves_data.append(
            {
                "move_date": sale_date,
                "variant_id": variant_id,
                "move_type": "OUT",
                "reason": "VENDA",
                "qty": qty,
                "unit_cost": unit_cost,
                "ref_type": "SALE",
                "ref_id": None,
                "notes": order_ref or "",
            }
        )

    sale_data = {
        "sale_date": sale_date,
        "channel": channel,
        "order_ref": order_ref,
        "customer_name": customer_name,
        "notes": notes,
        **totals,
    }

    sale_id = SaleRepository.insert_sale(conn, sale_data)

    for item_data, move_data in zip(sale_items_data, stock_moves_data):
        item_data["sale_id"] = sale_id
        move_data["ref_id"] = sale_id
        SaleRepository.insert_sale_item(conn, item_data)
        StockMoveRepository.insert_stock_move(conn, move_data)

    return sale_id


__all__ = ["create_sale"]
