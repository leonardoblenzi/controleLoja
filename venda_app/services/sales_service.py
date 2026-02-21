"""venda_app.services.sales_service

Serviço para registrar vendas e seus itens.

Regra: itens e estoque são SEMPRE por variação (variant_id).
Mesmo produtos sem variação têm uma variação "Única".
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

import sqlite3

from ..db.repositories import SaleRepository, StockMoveRepository, VariantRepository


def create_sale(
    conn: sqlite3.Connection,
    sale_date: str,
    channel: str,
    status: str,
    order_ref: str,
    customer_name: str,
    notes: str,
    items: List[Dict[str, Any]],
    packaging_enabled: bool = False,
    packaging_volumes: int = 1,
    packaging_box_sku: str = "",
    packaging_env_sku: str = "",
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

    # Embalagem (opcional)
    box_variant_id: Optional[int] = None
    env_variant_id: Optional[int] = None
    volumes = max(1, int(packaging_volumes or 1))

    if packaging_enabled:
        if packaging_box_sku.strip():
            box = VariantRepository.get_variant_by_sku(conn, packaging_box_sku.strip())
            if not box:
                raise ValueError(f"Caixa (SKU variação) não encontrada: {packaging_box_sku}")
            box_variant_id = int(box["variant_id"])
        if packaging_env_sku.strip():
            env = VariantRepository.get_variant_by_sku(conn, packaging_env_sku.strip())
            if not env:
                raise ValueError(f"Envelope (SKU variação) não encontrado: {packaging_env_sku}")
            env_variant_id = int(env["variant_id"])

    sale_data = {
        "sale_date": sale_date,
        "channel": channel,
        "status": status or "A_ENVIAR",
        "order_ref": order_ref,
        "customer_name": customer_name,
        "notes": notes,
        "packaging_enabled": 1 if packaging_enabled else 0,
        "packaging_volumes": volumes,
        "packaging_box_variant_id": box_variant_id,
        "packaging_env_variant_id": env_variant_id,
        **totals,
    }

    sale_id = SaleRepository.insert_sale(conn, sale_data)

    for item_data, move_data in zip(sale_items_data, stock_moves_data):
        item_data["sale_id"] = sale_id
        move_data["ref_id"] = sale_id
        SaleRepository.insert_sale_item(conn, item_data)
        StockMoveRepository.insert_stock_move(conn, move_data)

    # Baixa de embalagem (se habilitado)
    if packaging_enabled:
        # caixa
        if box_variant_id is not None:
            StockMoveRepository.insert_stock_move(
                conn,
                {
                    "move_date": sale_date,
                    "variant_id": box_variant_id,
                    "move_type": "OUT",
                    "reason": "EMBALAGEM",
                    "qty": volumes,
                    "unit_cost": 0,
                    "ref_type": "SALE",
                    "ref_id": sale_id,
                    "notes": f"Caixa | {order_ref}".strip(),
                },
            )
        # envelope
        if env_variant_id is not None:
            StockMoveRepository.insert_stock_move(
                conn,
                {
                    "move_date": sale_date,
                    "variant_id": env_variant_id,
                    "move_type": "OUT",
                    "reason": "EMBALAGEM",
                    "qty": volumes,
                    "unit_cost": 0,
                    "ref_type": "SALE",
                    "ref_id": sale_id,
                    "notes": f"Envelope | {order_ref}".strip(),
                },
            )

    return sale_id


def cancel_sale(conn: sqlite3.Connection, sale_id: int) -> None:
    """Cancela uma venda e gera movimentos inversos de estoque.

    Regras:
    - Marca a venda como CANCELADO
    - NÃO apaga dados
    - Cria movimentos de reversão para todos os movimentos ref_type='SALE' e ref_id=sale_id
    """
    cur = conn.cursor()

    sale = cur.execute("SELECT id, status, sale_date, order_ref FROM sales WHERE id = ?", (sale_id,)).fetchone()
    if not sale:
        raise ValueError("Venda não encontrada")

    if sale["status"] == "CANCELADO":
        return

    moves = cur.execute(
        """
        SELECT move_date, variant_id, move_type, reason, qty, unit_cost
          FROM stock_moves
         WHERE ref_type = 'SALE' AND ref_id = ?
        """,
        (sale_id,),
    ).fetchall()

    # Cria reversão (IN <-> OUT). ADJ vira ADJ com qty negativo.
    for m in moves:
        move_type = m["move_type"]
        if move_type == "OUT":
            rev_type = "IN"
            rev_qty = m["qty"]
        elif move_type == "IN":
            rev_type = "OUT"
            rev_qty = m["qty"]
        else:
            rev_type = "ADJ"
            rev_qty = -int(m["qty"])

        StockMoveRepository.insert_stock_move(
            conn,
            {
                "move_date": m["move_date"],
                "variant_id": m["variant_id"],
                "move_type": rev_type,
                "reason": "CANCELAMENTO",
                "qty": int(rev_qty),
                "unit_cost": float(m["unit_cost"]),
                "ref_type": "SALE_CANCEL",
                "ref_id": sale_id,
                "notes": f"Reversão venda {sale_id} ({sale['order_ref'] or ''})".strip(),
            },
        )

    # Atualiza status
    conn.execute("UPDATE sales SET status = 'CANCELADO' WHERE id = ?", (sale_id,))
    conn.commit()


def update_sale_status(conn: sqlite3.Connection, sale_id: int, status: str) -> None:
    conn.execute("UPDATE sales SET status = ? WHERE id = ?", (status, sale_id))
    conn.commit()


__all__ = ["create_sale", "cancel_sale", "update_sale_status"]
