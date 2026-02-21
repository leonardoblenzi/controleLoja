"""
Tela de movimentações de estoque.

Permite registrar entradas, saídas e ajustes de estoque manualmente e
listar as últimas movimentações. Esta implementação cobre apenas o
básico, sem filtros avançados.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from ..db.repositories import StockMoveRepository, VariantRepository
from ..utils.validators import is_non_empty, is_positive_integer, is_non_negative_float

from ..db.repositories import VariantRepository
from .autocomplete import AutocompleteEntry

class MovesFrame(ctk.CTkFrame):
    MOVE_TYPES = ["IN", "OUT", "ADJ"]
    REASONS = {
        "IN": ["COMPRA", "DEVOLUCAO"],
        "OUT": ["PERDA", "CONSUMO"],
        "ADJ": ["AJUSTE"],
    }

    def __init__(self, master, conn):
        super().__init__(master)
        self.conn = conn
        self.create_widgets()
        self.load_moves()

    def create_widgets(self):
        # Formulário
        form_frame = ctk.CTkFrame(self)
        form_frame.pack(fill="x", padx=10, pady=10)

        # Data
        ctk.CTkLabel(form_frame, text="Data (YYYY-MM-DD):").grid(row=0, column=0, sticky="w")
        self.date_entry = ctk.CTkEntry(form_frame)
        self.date_entry.grid(row=0, column=1, padx=5, pady=5)
        self.date_entry.insert(0, date.today().isoformat())

        # Tipo
        ctk.CTkLabel(form_frame, text="Tipo:").grid(row=0, column=2, sticky="w")
        self.type_var = tk.StringVar(value=self.MOVE_TYPES[0])
        self.type_menu = ctk.CTkOptionMenu(form_frame, variable=self.type_var, values=self.MOVE_TYPES, command=self.on_type_change)
        self.type_menu.grid(row=0, column=3, padx=5, pady=5)

        # Motivo
        ctk.CTkLabel(form_frame, text="Motivo:").grid(row=0, column=4, sticky="w")
        self.reason_var = tk.StringVar(value=self.REASONS[self.MOVE_TYPES[0]][0])
        self.reason_menu = ctk.CTkOptionMenu(form_frame, variable=self.reason_var, values=self.REASONS[self.MOVE_TYPES[0]])
        self.reason_menu.grid(row=0, column=5, padx=5, pady=5)

        # SKU (variação)
        ctk.CTkLabel(form_frame, text="SKU (variação):").grid(row=1, column=0, sticky="w")
        self.sku_entry = AutocompleteEntry(
            form_frame,
            provider=lambda q: VariantRepository.search_variants(self.conn, q),
        )
        self.sku_entry.grid(row=1, column=1, padx=5, pady=5)

        # Quantidade
        ctk.CTkLabel(form_frame, text="Qtd:").grid(row=1, column=2, sticky="w")
        self.qty_entry = ctk.CTkEntry(form_frame)
        self.qty_entry.grid(row=1, column=3, padx=5, pady=5)

        # Custo unitário
        ctk.CTkLabel(form_frame, text="Custo unitário:").grid(row=1, column=4, sticky="w")
        self.cost_entry = ctk.CTkEntry(form_frame)
        self.cost_entry.grid(row=1, column=5, padx=5, pady=5)

        # Notas
        ctk.CTkLabel(form_frame, text="Observações:").grid(row=2, column=0, sticky="w")
        self.notes_entry = ctk.CTkEntry(form_frame, width=300)
        self.notes_entry.grid(row=2, column=1, columnspan=5, padx=5, pady=5, sticky="ew")

        # Botão registrar
        self.add_button = ctk.CTkButton(form_frame, text="Registrar", command=self.add_move)
        self.add_button.grid(row=3, column=0, columnspan=6, pady=5)

        # Treeview de movimentos
        self.tree = ttk.Treeview(
            self,
            columns=("date", "type", "reason", "sku", "qty", "cost"),
            show="headings",
        )
        for col, text in [
            ("date", "Data"),
            ("type", "Tipo"),
            ("reason", "Motivo"),
            ("sku", "SKU"),
            ("qty", "Qtd"),
            ("cost", "Custo"),
        ]:
            self.tree.heading(col, text=text)
            self.tree.column(col, minwidth=80, width=100, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

    def on_type_change(self, selected_type):
        """Atualiza lista de motivos quando o tipo muda."""
        reasons = self.REASONS.get(selected_type, ["AJUSTE"])
        self.reason_menu.configure(values=reasons)
        self.reason_var.set(reasons[0])

    def add_move(self):
        """Valida e adiciona um movimento."""
        move_date = self.date_entry.get().strip()
        move_type = self.type_var.get()
        reason = self.reason_var.get()
        sku = self.sku_entry.get().strip()
        qty = self.qty_entry.get().strip()
        cost = self.cost_entry.get().strip() or "0"
        notes = self.notes_entry.get().strip()
        # Valida
        if not is_non_empty(sku):
            messagebox.showwarning("SKU", "Informe o SKU da variação.")
            return
        vrow = VariantRepository.get_variant_by_sku(self.conn, sku)
        if vrow is None:
            messagebox.showwarning("Variação", f"Variação/SKU '{sku}' não encontrado.")
            return
        if not is_positive_integer(qty):
            messagebox.showwarning("Quantidade", "Quantidade deve ser um inteiro positivo.")
            return
        if not is_non_negative_float(cost):
            messagebox.showwarning("Custo", "Custo deve ser um número não negativo.")
            return
        # Insere movimento
        variant_id = int(vrow["variant_id"])
        move_data = {
            "move_date": move_date,
            "variant_id": variant_id,
            "move_type": move_type,
            "reason": reason,
            "qty": int(qty),
            "unit_cost": float(cost),
            "ref_type": "MANUAL",
            "ref_id": None,
            "notes": notes,
        }
        StockMoveRepository.insert_stock_move(self.conn, move_data)
        messagebox.showinfo("Movimentação", "Movimento registrado com sucesso!")
        self.clear_form()
        self.load_moves()

    def clear_form(self):
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, date.today().isoformat())
        self.sku_entry.delete(0, tk.END)
        self.qty_entry.delete(0, tk.END)
        self.cost_entry.delete(0, tk.END)
        self.notes_entry.delete(0, tk.END)

    def load_moves(self):
        """Carrega os últimos movimentos para a Treeview (sem filtro)."""
        for row in self.tree.get_children():
            self.tree.delete(row)
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT sm.move_date, sm.move_type, sm.reason,
                   v.variant_sku, sm.qty, sm.unit_cost
              FROM stock_moves sm
              JOIN product_variants v ON v.id = sm.variant_id
             ORDER BY sm.move_date DESC, sm.id DESC
             LIMIT 100
            """
        )
        for move_date, move_type, reason, sku, qty, cost in cur.fetchall():
            self.tree.insert(
                "",
                "end",
                values=(move_date, move_type, reason, sku, qty, f"{cost:.2f}"),
            )