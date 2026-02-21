"""venda_app.db.repositories

Repositórios para acessar e manipular dados.

Este módulo contém classes que encapsulam operações de leitura e escrita no
banco de dados, separando persistência da UI e da lógica de negócios.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import sqlite3


# =========================
# MODELOS (dataclasses)
# =========================


@dataclass
class Category:
    id: Optional[int]
    name: str
    is_active: bool = True


@dataclass
class Product:
    id: Optional[int]
    sku: str
    name: str
    category_id: int
    variant_attribute_name: Optional[str] = None  # ex: "Cor" | "Modelo" (opcional)
    brand: Optional[str] = None
    cost_default: float = 0.0
    price_default: float = 0.0
    stock_min: int = 0
    is_active: bool = True


@dataclass
class ProductVariant:
    id: Optional[int]
    product_id: int
    variant_sku: str
    variant_value: str
    is_default: bool = False
    cost_override: Optional[float] = None
    price_override: Optional[float] = None
    is_active: bool = True


# =========================
# REPOSITÓRIO: CATEGORIAS
# =========================


class CategoryRepository:
    """CRUD de categorias."""

    @staticmethod
    def add_category(conn: sqlite3.Connection, name: str, is_active: bool = True) -> int:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO categories (name, is_active)
            VALUES (?, ?)
            """,
            (name.strip(), 1 if is_active else 0),
        )
        conn.commit()
        return cur.lastrowid

    @staticmethod
    def update_category(conn: sqlite3.Connection, category_id: int, name: str, is_active: bool) -> None:
        conn.execute(
            """
            UPDATE categories
               SET name = ?,
                   is_active = ?,
                   updated_at = datetime('now')
             WHERE id = ?
            """,
            (name.strip(), 1 if is_active else 0, category_id),
        )
        conn.commit()

    @staticmethod
    def delete_category(conn: sqlite3.Connection, category_id: int) -> None:
        conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
        conn.commit()

    @staticmethod
    def list_categories(conn: sqlite3.Connection, only_active: bool = False) -> List[Category]:
        cur = conn.cursor()
        if only_active:
            cur.execute(
                """
                SELECT id, name, is_active
                  FROM categories
                 WHERE is_active = 1
                 ORDER BY name
                """
            )
        else:
            cur.execute(
                """
                SELECT id, name, is_active
                  FROM categories
                 ORDER BY name
                """
            )
        rows = cur.fetchall()
        return [
            Category(id=r["id"], name=r["name"], is_active=bool(r["is_active"]))
            for r in rows
        ]


# =========================
# REPOSITÓRIO: PRODUTOS
# =========================


class ProductRepository:
    """CRUD de produtos."""

    @staticmethod
    def add_product(conn: sqlite3.Connection, product: Product) -> int:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO products (
                sku, name, category_id, variant_attribute_name,
                brand, cost_default, price_default, stock_min, is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                product.sku.strip(),
                product.name.strip(),
                int(product.category_id),
                (product.variant_attribute_name.strip() if product.variant_attribute_name else None),
                (product.brand.strip() if product.brand else None),
                float(product.cost_default),
                float(product.price_default),
                int(product.stock_min),
                1 if product.is_active else 0,
            ),
        )
        conn.commit()
        return cur.lastrowid

    @staticmethod
    def update_product(conn: sqlite3.Connection, product: Product) -> None:
        if product.id is None:
            raise ValueError("Produto deve ter ID para ser atualizado")
        conn.execute(
            """
            UPDATE products
               SET sku = ?,
                   name = ?,
                   category_id = ?,
                   variant_attribute_name = ?,
                   brand = ?,
                   cost_default = ?,
                   price_default = ?,
                   stock_min = ?,
                   is_active = ?,
                   updated_at = datetime('now')
             WHERE id = ?
            """,
            (
                product.sku.strip(),
                product.name.strip(),
                int(product.category_id),
                (product.variant_attribute_name.strip() if product.variant_attribute_name else None),
                (product.brand.strip() if product.brand else None),
                float(product.cost_default),
                float(product.price_default),
                int(product.stock_min),
                1 if product.is_active else 0,
                int(product.id),
            ),
        )
        conn.commit()

    @staticmethod
    def delete_product(conn: sqlite3.Connection, product_id: int) -> None:
        conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()

    @staticmethod
    def get_all_products_rows(conn: sqlite3.Connection) -> List[sqlite3.Row]:
        """Retorna produtos com nome da categoria (para UI)."""
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                p.id, p.sku, p.name, p.category_id, c.name AS category_name,
                p.variant_attribute_name,
                p.brand, p.cost_default, p.price_default, p.stock_min, p.is_active
              FROM products p
              JOIN categories c ON c.id = p.category_id
             ORDER BY p.name
            """
        )
        return cur.fetchall()

    @staticmethod
    def get_product_by_id(conn: sqlite3.Connection, product_id: int) -> Optional[Product]:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, sku, name, category_id, variant_attribute_name, brand,
                   cost_default, price_default, stock_min, is_active
              FROM products
             WHERE id = ?
            """,
            (product_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        return Product(
            id=row["id"],
            sku=row["sku"],
            name=row["name"],
            category_id=row["category_id"],
            variant_attribute_name=row["variant_attribute_name"],
            brand=row["brand"],
            cost_default=row["cost_default"],
            price_default=row["price_default"],
            stock_min=row["stock_min"],
            is_active=bool(row["is_active"]),
        )

    @staticmethod
    def get_product_by_sku(conn: sqlite3.Connection, sku: str) -> Optional[Product]:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, sku, name, category_id, variant_attribute_name, brand,
                   cost_default, price_default, stock_min, is_active
              FROM products
             WHERE sku = ?
            """,
            (sku.strip(),),
        )
        row = cur.fetchone()
        if not row:
            return None
        return Product(
            id=row["id"],
            sku=row["sku"],
            name=row["name"],
            category_id=row["category_id"],
            variant_attribute_name=row["variant_attribute_name"],
            brand=row["brand"],
            cost_default=row["cost_default"],
            price_default=row["price_default"],
            stock_min=row["stock_min"],
            is_active=bool(row["is_active"]),
        )


# =========================
# REPOSITÓRIO: VARIAÇÕES
# =========================


class VariantRepository:
    """CRUD de variações."""

    @staticmethod
    def add_variant(conn: sqlite3.Connection, v: ProductVariant) -> int:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO product_variants (
                product_id, variant_sku, variant_value, is_default,
                cost_override, price_override, is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(v.product_id),
                v.variant_sku.strip(),
                v.variant_value.strip(),
                1 if v.is_default else 0,
                v.cost_override,
                v.price_override,
                1 if v.is_active else 0,
            ),
        )
        conn.commit()
        return cur.lastrowid

    @staticmethod
    def update_variant(conn: sqlite3.Connection, v: ProductVariant) -> None:
        if v.id is None:
            raise ValueError("Variação deve ter ID para ser atualizada")
        conn.execute(
            """
            UPDATE product_variants
               SET variant_sku = ?,
                   variant_value = ?,
                   is_default = ?,
                   cost_override = ?,
                   price_override = ?,
                   is_active = ?,
                   updated_at = datetime('now')
             WHERE id = ?
            """,
            (
                v.variant_sku.strip(),
                v.variant_value.strip(),
                1 if v.is_default else 0,
                v.cost_override,
                v.price_override,
                1 if v.is_active else 0,
                int(v.id),
            ),
        )
        conn.commit()

    @staticmethod
    def list_variants_by_product(conn: sqlite3.Connection, product_id: int, only_active: bool = False) -> List[ProductVariant]:
        cur = conn.cursor()
        if only_active:
            cur.execute(
                """
                SELECT id, product_id, variant_sku, variant_value, is_default,
                       cost_override, price_override, is_active
                  FROM product_variants
                 WHERE product_id = ? AND is_active = 1
                 ORDER BY is_default DESC, variant_value
                """,
                (product_id,),
            )
        else:
            cur.execute(
                """
                SELECT id, product_id, variant_sku, variant_value, is_default,
                       cost_override, price_override, is_active
                  FROM product_variants
                 WHERE product_id = ?
                 ORDER BY is_default DESC, variant_value
                """,
                (product_id,),
            )
        rows = cur.fetchall()
        return [
            ProductVariant(
                id=r["id"],
                product_id=r["product_id"],
                variant_sku=r["variant_sku"],
                variant_value=r["variant_value"],
                is_default=bool(r["is_default"]),
                cost_override=r["cost_override"],
                price_override=r["price_override"],
                is_active=bool(r["is_active"]),
            )
            for r in rows
        ]

    @staticmethod
    def get_variant_by_sku(conn: sqlite3.Connection, variant_sku: str) -> Optional[sqlite3.Row]:
        """Retorna uma Row com infos do variant + produto (para custo/preço)."""
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                v.id AS variant_id,
                v.variant_sku,
                v.variant_value,
                v.is_default,
                v.cost_override,
                v.price_override,
                v.is_active,
                p.id AS product_id,
                p.sku AS product_sku,
                p.name AS product_name,
                p.cost_default,
                p.price_default,
                p.stock_min,
                p.variant_attribute_name
              FROM product_variants v
              JOIN products p ON p.id = v.product_id
             WHERE v.variant_sku = ?
            """,
            (variant_sku.strip(),),
        )
        return cur.fetchone()


# =========================
# REPOSITÓRIO: VENDAS
# =========================


class SaleRepository:
    @staticmethod
    def insert_sale(conn: sqlite3.Connection, sale_data: Dict[str, Any]) -> int:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO sales (
                sale_date, channel, order_ref, customer_name, notes,
                total_gross, total_fees, total_discount, total_net,
                total_cost, total_profit
            )
            VALUES (
                :sale_date, :channel, :order_ref, :customer_name, :notes,
                :total_gross, :total_fees, :total_discount, :total_net,
                :total_cost, :total_profit
            )
            """,
            sale_data,
        )
        conn.commit()
        return cur.lastrowid

    @staticmethod
    def insert_sale_item(conn: sqlite3.Connection, item_data: Dict[str, Any]) -> int:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO sale_items (
                sale_id, variant_id, qty, unit_price, unit_cost,
                fees, discount, net, profit
            )
            VALUES (
                :sale_id, :variant_id, :qty, :unit_price, :unit_cost,
                :fees, :discount, :net, :profit
            )
            """,
            item_data,
        )
        conn.commit()
        return cur.lastrowid


# =========================
# REPOSITÓRIO: ESTOQUE
# =========================


class StockMoveRepository:
    @staticmethod
    def insert_stock_move(conn: sqlite3.Connection, move_data: Dict[str, Any]) -> int:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO stock_moves (
                move_date, variant_id, move_type, reason,
                qty, unit_cost, ref_type, ref_id, notes
            )
            VALUES (
                :move_date, :variant_id, :move_type, :reason,
                :qty, :unit_cost, :ref_type, :ref_id, :notes
            )
            """,
            move_data,
        )
        conn.commit()
        return cur.lastrowid


# =========================
# REPOSITÓRIO: GASTOS
# =========================


class ExpenseRepository:
    @staticmethod
    def add_expense(conn: sqlite3.Connection, expense_data: Dict[str, Any]) -> int:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO expenses (exp_date, category, description, amount, payment_method, notes)
            VALUES (:exp_date, :category, :description, :amount, :payment_method, :notes)
            """,
            expense_data,
        )
        conn.commit()
        return cur.lastrowid


class VariantRepository:
    @staticmethod
    def search_variants(conn: sqlite3.Connection, q: str, limit: int = 12):
        """
        Retorna sugestões de variantes por:
        - prefixo/trecho de SKU
        - nome do produto
        - valor da variação (ex: Preto, Rosa)
        """
        q = (q or "").strip()
        if not q:
            return []

        like = f"%{q}%"

        cur = conn.cursor()
        cur.execute(
            """
            SELECT
              v.id AS variant_id,
              v.variant_sku,
              p.name AS product_name,
              COALESCE(p.variant_attribute_name, 'Variação') AS attr_name,
              v.variant_value
            FROM product_variants v
            JOIN products p ON p.id = v.product_id
            WHERE
              v.variant_sku LIKE ?
              OR p.name LIKE ?
              OR v.variant_value LIKE ?
            ORDER BY
              CASE WHEN v.variant_sku LIKE ? THEN 0 ELSE 1 END,
              v.variant_sku
            LIMIT ?
            """,
            (like, like, like, f"{q}%", limit),
        )
        return cur.fetchall()

    @staticmethod
    def get_variant_by_sku(conn: sqlite3.Connection, sku: str):
        """
        Busca UMA variante pelo SKU exato.
        Retorna sqlite3.Row com (variant_id, variant_sku, product_name, attr_name, variant_value)
        ou None.
        """
        sku = (sku or "").strip()
        if not sku:
            return None

        cur = conn.cursor()
        cur.execute(
            """
            SELECT
              v.id AS variant_id,
              v.variant_sku,
              p.name AS product_name,
              COALESCE(p.variant_attribute_name, 'Variação') AS attr_name,
              v.variant_value
            FROM product_variants v
            JOIN products p ON p.id = v.product_id
            WHERE v.variant_sku = ?
            """,
            (sku,),
        )
        return cur.fetchone()

    @staticmethod
    def get_variant_id_by_sku(conn: sqlite3.Connection, sku: str):
        """
        Versão enxuta pra validação:
        retorna somente o id da variante (int) ou None.
        """
        sku = (sku or "").strip()
        if not sku:
            return None

        cur = conn.cursor()
        cur.execute(
            "SELECT id FROM product_variants WHERE variant_sku = ?",
            (sku,),
        )
        row = cur.fetchone()
        return int(row["id"]) if row else None

__all__ = [
    "Category",
    "Product",
    "ProductVariant",
    "CategoryRepository",
    "ProductRepository",
    "VariantRepository",
    "SaleRepository",
    "StockMoveRepository",
    "ExpenseRepository",
]
