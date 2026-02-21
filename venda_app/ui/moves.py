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

from ..db.repositories import StockMoveRepository, VariantRepository, ProductRepository
from ..utils.validators import (
    is_non_empty,
    is_positive_integer,
    is_non_negative_float,
    parse_flexible_date,
    format_iso_to_br,
)

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
        self.editing_move_id: int | None = None
        self.create_widgets()
        self.load_moves()

    def create_widgets(self):
        # Formulário
        form_frame = ctk.CTkFrame(self)
        form_frame.pack(fill="x", padx=10, pady=10)

        # Data
        ctk.CTkLabel(form_frame, text="Data:").grid(row=0, column=0, sticky="w")
        self.date_entry = ctk.CTkEntry(form_frame)
        self.date_entry.grid(row=0, column=1, padx=5, pady=5)
        self.date_entry.insert(0, format_iso_to_br(date.today().isoformat()))

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

        # Custo total (unitário será calculado = total / qtd)
        ctk.CTkLabel(form_frame, text="Custo total:").grid(row=1, column=4, sticky="w")
        self.total_cost_entry = ctk.CTkEntry(form_frame)
        self.total_cost_entry.grid(row=1, column=5, padx=5, pady=5)

        # Notas
        ctk.CTkLabel(form_frame, text="Observações:").grid(row=2, column=0, sticky="w")
        self.notes_entry = ctk.CTkEntry(form_frame, width=300)
        self.notes_entry.grid(row=2, column=1, columnspan=5, padx=5, pady=5, sticky="ew")

        # Botões de ação
        actions = ctk.CTkFrame(form_frame, fg_color="transparent")
        actions.grid(row=3, column=0, columnspan=6, pady=8)

        self.add_button = ctk.CTkButton(actions, text="Registrar", command=self.add_or_update_move, width=140)
        self.add_button.pack(side="left", padx=6)

        self.cancel_edit_btn = ctk.CTkButton(
            actions,
            text="Cancelar edição",
            command=self.cancel_edit,
            width=160,
            fg_color="#3a3a3a",
            hover_color="#4a4a4a",
        )
        self.cancel_edit_btn.pack(side="left", padx=6)

        self.delete_btn = ctk.CTkButton(
            actions,
            text="Remover selecionado",
            command=self.delete_selected_move,
            width=180,
            fg_color="#7a2e2e",
            hover_color="#8a3a3a",
        )
        self.delete_btn.pack(side="left", padx=6)

        # Treeview de movimentos
        self.tree = ttk.Treeview(
            self,
            columns=("date", "type", "reason", "sku", "qty", "cost", "total"),
            show="headings",
        )
        for col, text in [
            ("date", "Data"),
            ("type", "Tipo"),
            ("reason", "Motivo"),
            ("sku", "SKU"),
            ("qty", "Qtd"),
            ("cost", "Custo"),
            ("total", "Total"),
        ]:
            self.tree.heading(col, text=text)
            self.tree.column(col, minwidth=80, width=100, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Duplo clique para editar
        self.tree.bind("<Double-1>", self.on_tree_double_click)

    def on_type_change(self, selected_type):
        """Atualiza lista de motivos quando o tipo muda."""
        reasons = self.REASONS.get(selected_type, ["AJUSTE"])
        self.reason_menu.configure(values=reasons)
        self.reason_var.set(reasons[0])

    def _compute_unit_cost(self, qty: int, total_cost: float) -> float:
        if qty <= 0:
            return 0.0
        return float(total_cost) / float(qty)

    def add_or_update_move(self):
        """Valida e adiciona/atualiza um movimento."""
        # Aceita vários formatos e grava no banco em ISO
        try:
            move_date = parse_flexible_date(self.date_entry.get().strip())
        except Exception as e:
            messagebox.showwarning("Data", str(e))
            return
        move_type = self.type_var.get()
        reason = self.reason_var.get()
        sku = self.sku_entry.get().strip()
        qty = self.qty_entry.get().strip()
        total_cost = self.total_cost_entry.get().strip() or "0"
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
        if not is_non_negative_float(total_cost):
            messagebox.showwarning("Custo", "Custo total deve ser um número não negativo.")
            return

        qty_i = int(qty)
        unit_cost = self._compute_unit_cost(qty_i, float(total_cost))
        # Insere movimento
        variant_id = int(vrow["variant_id"])
        move_data = {
            "move_date": move_date,
            "variant_id": variant_id,
            "move_type": move_type,
            "reason": reason,
            "qty": qty_i,
            "unit_cost": float(unit_cost),
            "ref_type": "MANUAL",
            "ref_id": None,
            "notes": notes,
        }

        if self.editing_move_id is None:
            StockMoveRepository.insert_stock_move(self.conn, move_data)
            messagebox.showinfo("Movimentação", "Movimento registrado com sucesso!")
        else:
            StockMoveRepository.update_stock_move(self.conn, int(self.editing_move_id), move_data)
            messagebox.showinfo("Movimentação", "Movimento atualizado com sucesso!")

        # Atualiza custo do produto/variação quando for COMPRA (entrada)
        if move_type == "IN" and str(reason).strip().upper() == "COMPRA":
            try:
                ProductRepository.apply_purchase_cost_from_variant(self.conn, variant_id, float(unit_cost))
            except Exception:
                # não bloqueia o fluxo da movimentação
                pass

        self.clear_form()
        self.load_moves()

    def clear_form(self):
        self.editing_move_id = None
        self.add_button.configure(text="Registrar")
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, format_iso_to_br(date.today().isoformat()))
        self.sku_entry.delete(0, tk.END)
        self.qty_entry.delete(0, tk.END)
        self.total_cost_entry.delete(0, tk.END)
        self.notes_entry.delete(0, tk.END)

    def cancel_edit(self):
        self.clear_form()

    def _get_selected_move_id(self) -> int | None:
        sel = self.tree.selection()
        if not sel:
            return None
        iid = sel[0]
        try:
            return int(iid)
        except Exception:
            return None

    def on_tree_double_click(self, _evt=None):
        move_id = self._get_selected_move_id()
        if move_id is None:
            return
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT sm.id, sm.move_date, sm.move_type, sm.reason, sm.qty, sm.unit_cost, sm.notes,
                   v.variant_sku
              FROM stock_moves sm
              JOIN product_variants v ON v.id = sm.variant_id
             WHERE sm.id = ?
            """,
            (move_id,),
        )
        row = cur.fetchone()
        if not row:
            return

        self.editing_move_id = int(row["id"])
        self.add_button.configure(text="Salvar alterações")

        # Preenche formulário
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, format_iso_to_br(row["move_date"]))

        self.type_var.set(row["move_type"])
        self.on_type_change(row["move_type"])
        self.reason_var.set(row["reason"])

        self.sku_entry.delete(0, tk.END)
        self.sku_entry.insert(0, row["variant_sku"])

        self.qty_entry.delete(0, tk.END)
        self.qty_entry.insert(0, str(row["qty"]))

        total = float(row["qty"]) * float(row["unit_cost"])
        self.total_cost_entry.delete(0, tk.END)
        self.total_cost_entry.insert(0, f"{total:.2f}")

        self.notes_entry.delete(0, tk.END)
        self.notes_entry.insert(0, row["notes"] or "")

    def delete_selected_move(self):
        move_id = self._get_selected_move_id()
        if move_id is None:
            messagebox.showwarning("Remover", "Selecione uma movimentação na lista.")
            return
        if not messagebox.askyesno("Confirmar", "Deseja remover a movimentação selecionada?"):
            return
        try:
            # Captura variant_id antes de remover
            cur = self.conn.cursor()
            cur.execute("SELECT variant_id FROM stock_moves WHERE id = ?", (int(move_id),))
            r = cur.fetchone()
            variant_id = int(r[0]) if r else None

            StockMoveRepository.delete_stock_move(self.conn, int(move_id))

            # Recalcula custo com base na última compra registrada (se houver)
            if variant_id is not None:
                try:
                    ProductRepository.recompute_purchase_costs(self.conn, variant_id)
                except Exception:
                    pass
        except Exception as e:
            messagebox.showerror("Erro", str(e))
            return
        self.clear_form()
        self.load_moves()

    def load_moves(self):
        """Carrega os últimos movimentos para a Treeview (sem filtro)."""
        for row in self.tree.get_children():
            self.tree.delete(row)
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT sm.id, sm.move_date, sm.move_type, sm.reason,
                   v.variant_sku, sm.qty, sm.unit_cost
              FROM stock_moves sm
              JOIN product_variants v ON v.id = sm.variant_id
             ORDER BY sm.move_date DESC, sm.id DESC
             LIMIT 100
            """
        )
        for move_id, move_date, move_type, reason, sku, qty, unit_cost in cur.fetchall():
            total = float(qty) * float(unit_cost)
            self.tree.insert(
                "",
                "end",
                iid=str(move_id),
                values=(format_iso_to_br(move_date), move_type, reason, sku, qty, f"{float(unit_cost):.2f}", f"{total:.2f}"),
            )