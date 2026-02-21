"""venda_app.ui.sales

Tela de Vendas.

Funcionalidades:
- Lançar venda com itens (por SKU de variação) com autocomplete
- Definir status do pedido (A_ENVIAR, ENVIADO, CONCLUIDO, CANCELADO)
- (Opcional) baixar embalagem ao salvar (caixa/envelope) + volumes
- Lista de vendas recentes com ações: marcar ENVIADO/CONCLUIDO e CANCELAR (reverte estoque)
"""

from __future__ import annotations

from datetime import date

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox

from ..db.repositories import VariantRepository, SaleRepository
from ..services.sales_service import create_sale, cancel_sale, update_sale_status
from ..utils.validators import is_non_empty, is_positive_integer, is_non_negative_float
from .autocomplete import AutocompleteEntry


class SalesFrame(ctk.CTkFrame):
    CHANNEL_OPTIONS = ["Shopee", "ML", "Presencial", "Outros"]
    STATUS_OPTIONS = ["A_ENVIAR", "ENVIADO", "CONCLUIDO", "CANCELADO"]

    def __init__(self, master, conn):
        super().__init__(master)
        self.conn = conn
        self.items: list[dict] = []
        self._selected_sale_id: int | None = None
        self.create_widgets()
        self.refresh_sales_list()

    def create_widgets(self):
        # ======================
        # FORM: dados gerais
        # ======================
        form_frame = ctk.CTkFrame(self)
        form_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(form_frame, text="Data (YYYY-MM-DD):").grid(row=0, column=0, sticky="w")
        self.date_entry = ctk.CTkEntry(form_frame)
        self.date_entry.grid(row=0, column=1, padx=5, pady=5)
        self.date_entry.insert(0, date.today().isoformat())

        ctk.CTkLabel(form_frame, text="Canal:").grid(row=0, column=2, sticky="w")
        self.channel_var = tk.StringVar(value=self.CHANNEL_OPTIONS[0])
        self.channel_menu = ctk.CTkOptionMenu(form_frame, variable=self.channel_var, values=self.CHANNEL_OPTIONS)
        self.channel_menu.grid(row=0, column=3, padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Status:").grid(row=0, column=4, sticky="w")
        self.status_var = tk.StringVar(value="A_ENVIAR")
        self.status_menu = ctk.CTkOptionMenu(form_frame, variable=self.status_var, values=self.STATUS_OPTIONS)
        self.status_menu.grid(row=0, column=5, padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Pedido/Ref.:").grid(row=1, column=0, sticky="w")
        self.ref_entry = ctk.CTkEntry(form_frame)
        self.ref_entry.grid(row=1, column=1, padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Cliente:").grid(row=1, column=2, sticky="w")
        self.customer_entry = ctk.CTkEntry(form_frame)
        self.customer_entry.grid(row=1, column=3, padx=5, pady=5)

        ctk.CTkLabel(form_frame, text="Observações:").grid(row=2, column=0, sticky="nw")
        self.notes_text = tk.Text(form_frame, height=3, width=40)
        self.notes_text.grid(row=2, column=1, columnspan=5, padx=5, pady=5, sticky="ew")

        for col in range(6):
            form_frame.grid_columnconfigure(col, weight=1)

        # ======================
        # EMBALAGEM
        # ======================
        pack_frame = ctk.CTkFrame(self)
        pack_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(pack_frame, text="Embalagem do pedido", font=("Helvetica", 14)).grid(
            row=0, column=0, columnspan=6, sticky="w", padx=8, pady=(8, 4)
        )

        self.pack_enable_var = tk.IntVar(value=1)
        ctk.CTkCheckBox(pack_frame, text="Baixar embalagem", variable=self.pack_enable_var).grid(
            row=1, column=0, sticky="w", padx=8, pady=6
        )

        ctk.CTkLabel(pack_frame, text="Volumes:").grid(row=1, column=1, sticky="e", padx=(10, 4))
        self.pack_volumes_entry = ctk.CTkEntry(pack_frame, width=70)
        self.pack_volumes_entry.grid(row=1, column=2, sticky="w", padx=4, pady=6)
        self.pack_volumes_entry.insert(0, "1")

        ctk.CTkLabel(pack_frame, text="Caixa (SKU variação):").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        self.pack_box_entry = AutocompleteEntry(
            pack_frame,
            provider=lambda q: VariantRepository.search_variants(self.conn, q, category_name="MATERIAIS"),
        )
        self.pack_box_entry.grid(row=2, column=1, columnspan=2, sticky="ew", padx=8, pady=6)

        ctk.CTkLabel(pack_frame, text="Envelope (SKU variação):").grid(row=2, column=3, sticky="w", padx=8, pady=6)
        self.pack_env_entry = AutocompleteEntry(
            pack_frame,
            provider=lambda q: VariantRepository.search_variants(self.conn, q, category_name="MATERIAIS"),
        )
        self.pack_env_entry.grid(row=2, column=4, columnspan=2, sticky="ew", padx=8, pady=6)

        for c in range(6):
            pack_frame.grid_columnconfigure(c, weight=1)
        pack_frame.grid_columnconfigure(2, weight=0)

        # ======================
        # ITENS
        # ======================
        item_frame = ctk.CTkFrame(self)
        item_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(item_frame, text="SKU (variação):").grid(row=0, column=0, sticky="w")
        self.item_sku_entry = AutocompleteEntry(
            item_frame,
            provider=lambda q: VariantRepository.search_variants(self.conn, q),
        )
        self.item_sku_entry.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(item_frame, text="Qtd:").grid(row=0, column=2, sticky="w")
        self.item_qty_entry = ctk.CTkEntry(item_frame, width=60)
        self.item_qty_entry.grid(row=0, column=3, padx=5, pady=5)

        ctk.CTkLabel(item_frame, text="Preço unitário:").grid(row=0, column=4, sticky="w")
        self.item_price_entry = ctk.CTkEntry(item_frame, width=90)
        self.item_price_entry.grid(row=0, column=5, padx=5, pady=5)

        ctk.CTkLabel(item_frame, text="Taxa:").grid(row=0, column=6, sticky="w")
        self.item_fee_entry = ctk.CTkEntry(item_frame, width=80)
        self.item_fee_entry.grid(row=0, column=7, padx=5, pady=5)

        ctk.CTkLabel(item_frame, text="Desconto:").grid(row=0, column=8, sticky="w")
        self.item_discount_entry = ctk.CTkEntry(item_frame, width=80)
        self.item_discount_entry.grid(row=0, column=9, padx=5, pady=5)

        self.add_item_button = ctk.CTkButton(item_frame, text="Adicionar", command=self.add_item)
        self.add_item_button.grid(row=0, column=10, padx=10, pady=5)

        # Tabela de itens
        self.item_tree = ttk.Treeview(self, columns=("sku", "qty", "price", "fees", "discount"), show="headings")
        for col, text in [
            ("sku", "SKU"),
            ("qty", "Qtd"),
            ("price", "Preço"),
            ("fees", "Taxa"),
            ("discount", "Desc."),
        ]:
            self.item_tree.heading(col, text=text)
            self.item_tree.column(col, minwidth=60, width=110, anchor="center")
        self.item_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # ações itens
        action_frame = ctk.CTkFrame(self)
        action_frame.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(action_frame, text="Salvar Venda", command=self.save_sale).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(action_frame, text="Remover Item", command=self.remove_selected_item).pack(side="left", padx=5, pady=5)
        ctk.CTkButton(action_frame, text="Limpar", command=self.clear_form).pack(side="left", padx=5, pady=5)

        # ======================
        # LISTA DE VENDAS
        # ======================
        list_frame = ctk.CTkFrame(self)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        header = ctk.CTkFrame(list_frame)
        header.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(header, text="Vendas recentes", font=("Helvetica", 14)).pack(side="left")
        ctk.CTkButton(header, text="Atualizar", command=self.refresh_sales_list).pack(side="right")

        self.sales_tree = ttk.Treeview(
            list_frame,
            columns=("id", "date", "channel", "status", "ref", "net", "profit"),
            show="headings",
            height=8,
        )
        for col, text, w in [
            ("id", "ID", 60),
            ("date", "Data", 110),
            ("channel", "Canal", 120),
            ("status", "Status", 120),
            ("ref", "Pedido", 160),
            ("net", "Líquido", 110),
            ("profit", "Lucro", 110),
        ]:
            self.sales_tree.heading(col, text=text)
            self.sales_tree.column(col, width=w, anchor="center")
        self.sales_tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.sales_tree.bind("<ButtonRelease-1>", self.on_select_sale)

        status_actions = ctk.CTkFrame(list_frame)
        status_actions.pack(fill="x", padx=8, pady=(0, 8))
        ctk.CTkButton(status_actions, text="Marcar Enviado", command=lambda: self.set_selected_status("ENVIADO")).pack(side="left", padx=5)
        ctk.CTkButton(status_actions, text="Marcar Concluído", command=lambda: self.set_selected_status("CONCLUIDO")).pack(side="left", padx=5)
        ctk.CTkButton(status_actions, text="Cancelar (reverter)", command=self.cancel_selected_sale).pack(side="left", padx=5)

    # ======================
    # Itens
    # ======================

    def add_item(self):
        sku = self.item_sku_entry.get().strip()
        qty = self.item_qty_entry.get().strip()
        price = self.item_price_entry.get().strip()
        fee = self.item_fee_entry.get().strip() or "0"
        discount = self.item_discount_entry.get().strip() or "0"

        if not is_non_empty(sku):
            messagebox.showwarning("SKU", "Informe o SKU da variação.")
            return
        if not is_positive_integer(qty):
            messagebox.showwarning("Quantidade", "Quantidade deve ser um inteiro positivo.")
            return
        if not is_non_negative_float(price) or not is_non_negative_float(fee) or not is_non_negative_float(discount):
            messagebox.showwarning("Valores", "Preço, taxa e desconto devem ser números válidos (>= 0).")
            return

        if VariantRepository.get_variant_by_sku(self.conn, sku) is None:
            messagebox.showwarning("SKU", f"Variação/SKU '{sku}' não encontrado.")
            return

        item = {
            "sku": sku,
            "qty": int(qty),
            "unit_price": float(price),
            "fees": float(fee),
            "discount": float(discount),
        }
        self.items.append(item)
        self.item_tree.insert("", "end", values=(sku, qty, f"{float(price):.2f}", f"{float(fee):.2f}", f"{float(discount):.2f}"))

        # limpa campos item
        self.item_sku_entry.delete(0, tk.END)
        self.item_qty_entry.delete(0, tk.END)
        self.item_price_entry.delete(0, tk.END)
        self.item_fee_entry.delete(0, tk.END)
        self.item_discount_entry.delete(0, tk.END)

    def remove_selected_item(self):
        sel = self.item_tree.selection()
        if not sel:
            return
        idx = self.item_tree.index(sel[0])
        self.item_tree.delete(sel[0])
        if 0 <= idx < len(self.items):
            del self.items[idx]

    # ======================
    # Venda
    # ======================

    def save_sale(self):
        sale_date = self.date_entry.get().strip()
        channel = self.channel_var.get()
        status = self.status_var.get() or "A_ENVIAR"
        ref = self.ref_entry.get().strip()
        customer = self.customer_entry.get().strip()
        notes = self.notes_text.get("1.0", tk.END).strip()

        if not self.items:
            messagebox.showwarning("Itens", "Adicione ao menos um item à venda.")
            return

        pack_enabled = bool(self.pack_enable_var.get())
        volumes_txt = (self.pack_volumes_entry.get() or "1").strip()
        if not is_positive_integer(volumes_txt):
            messagebox.showwarning("Volumes", "Volumes deve ser um inteiro positivo.")
            return
        volumes = int(volumes_txt)
        box_sku = self.pack_box_entry.get().strip()
        env_sku = self.pack_env_entry.get().strip()

        # Se baixar embalagem, exige ao menos 1 dos dois (você pode tornar ambos obrigatórios)
        if pack_enabled and not (box_sku or env_sku):
            messagebox.showwarning("Embalagem", "Informe pelo menos a Caixa ou o Envelope (ou desmarque 'Baixar embalagem').")
            return

        try:
            sale_id = create_sale(
                self.conn,
                sale_date=sale_date,
                channel=channel,
                status=status,
                order_ref=ref,
                customer_name=customer,
                notes=notes,
                items=self.items,
                packaging_enabled=pack_enabled,
                packaging_volumes=volumes,
                packaging_box_sku=box_sku,
                packaging_env_sku=env_sku,
            )
        except Exception as e:
            messagebox.showerror("Erro ao salvar", str(e))
            return

        messagebox.showinfo("Venda", f"Venda registrada com sucesso (ID {sale_id})")
        self.clear_form()
        self.refresh_sales_list()

    def clear_form(self):
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, date.today().isoformat())
        self.status_var.set("A_ENVIAR")
        self.ref_entry.delete(0, tk.END)
        self.customer_entry.delete(0, tk.END)
        self.notes_text.delete("1.0", tk.END)

        self.pack_enable_var.set(1)
        self.pack_volumes_entry.delete(0, tk.END)
        self.pack_volumes_entry.insert(0, "1")
        self.pack_box_entry.delete(0, tk.END)
        self.pack_env_entry.delete(0, tk.END)

        for row in self.item_tree.get_children():
            self.item_tree.delete(row)
        self.items.clear()

    # ======================
    # Lista de vendas
    # ======================

    def refresh_sales_list(self):
        for r in self.sales_tree.get_children():
            self.sales_tree.delete(r)
        rows = SaleRepository.list_recent_sales(self.conn, limit=50)
        for r in rows:
            self.sales_tree.insert(
                "",
                "end",
                iid=str(r["id"]),
                values=(
                    r["id"],
                    r["sale_date"],
                    r["channel"],
                    r["status"],
                    r["order_ref"] or "",
                    f"{float(r['total_net']):.2f}",
                    f"{float(r['total_profit']):.2f}",
                ),
            )

    def on_select_sale(self, event=None):
        sel = self.sales_tree.selection()
        if not sel:
            self._selected_sale_id = None
            return
        self._selected_sale_id = int(sel[0])

    def set_selected_status(self, status: str):
        if not self._selected_sale_id:
            messagebox.showwarning("Venda", "Selecione uma venda na lista.")
            return
        try:
            update_sale_status(self.conn, self._selected_sale_id, status)
        except Exception as e:
            messagebox.showerror("Erro", str(e))
            return
        self.refresh_sales_list()

    def cancel_selected_sale(self):
        if not self._selected_sale_id:
            messagebox.showwarning("Venda", "Selecione uma venda na lista.")
            return
        if not messagebox.askyesno("Confirmar", "Cancelar esta venda e reverter estoque?"):
            return
        try:
            cancel_sale(self.conn, self._selected_sale_id)
        except Exception as e:
            messagebox.showerror("Erro", str(e))
            return
        self.refresh_sales_list()


__all__ = ["SalesFrame"]
