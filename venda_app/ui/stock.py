"""venda_app.ui.stock

Tela de estoque (por variação).

Mostra cada variação com seu estoque atual e sinaliza quando o estoque TOTAL
do produto (soma das variações ativas) está abaixo do mínimo.
"""

from __future__ import annotations

import customtkinter as ctk
from tkinter import ttk

from ..services.inventory_service import get_product_stock_levels, get_stock_table_rows


class StockFrame(ctk.CTkFrame):
    def __init__(self, master, conn):
        super().__init__(master)
        self.conn = conn
        self.create_widgets()
        self.load_stock()

    def create_widgets(self):
        top = ctk.CTkFrame(self)
        top.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(top, text="Atualizar", command=self.load_stock, width=140).pack(side="left", padx=6)

        self.tree = ttk.Treeview(
            self,
            columns=("product_sku", "product", "attr", "variant_value", "variant_sku", "stock", "min", "status"),
            show="headings",
        )
        cols = [
            ("product_sku", "SKU Produto", 120),
            ("product", "Produto", 220),
            ("attr", "Atributo", 90),
            ("variant_value", "Variação", 140),
            ("variant_sku", "SKU Variação", 140),
            ("stock", "Estoque", 90),
            ("min", "Mínimo", 80),
            ("status", "Status", 90),
        ]
        for key, label, width in cols:
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, anchor="center")

        self.tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def load_stock(self):
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        product_stock = get_product_stock_levels(self.conn)
        rows = get_stock_table_rows(self.conn)

        for r in rows:
            pid = int(r["product_id"])
            total = int(product_stock.get(pid, 0))
            min_stock = int(r["stock_min"])
            status = "OK" if total >= min_stock else "BAIXO"

            attr = r["variant_attribute_name"] or "-"
            self.tree.insert(
                "",
                "end",
                values=(
                    r["product_sku"],
                    r["product_name"],
                    attr,
                    r["variant_value"],
                    r["variant_sku"],
                    int(r["stock"]),
                    min_stock,
                    status,
                ),
            )
