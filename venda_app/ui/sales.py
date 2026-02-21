"""
Tela de lançamento de vendas.

Esta tela permite registrar vendas com múltiplos itens. Os itens são
acumulados em uma lista e, ao salvar, a venda é registrada junto com
os itens e as movimentações de estoque. Esta é uma implementação
simplificada que suporta adição de um item por vez em uma tabela
temporária.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from ..db.repositories import VariantRepository
from ..services.sales_service import create_sale
from ..utils.validators import is_non_empty, is_positive_integer, is_non_negative_float
from ..db.repositories import VariantRepository
from .autocomplete import AutocompleteEntry

class SalesFrame(ctk.CTkFrame):
    CHANNEL_OPTIONS = ["Shopee", "ML", "Presencial", "Outros"]

    def __init__(self, master, conn):
        super().__init__(master)
        self.conn = conn
        self.items = []  # Itens temporários para a venda
        self.create_widgets()

    def create_widgets(self):
        # Dados gerais da venda
        form_frame = ctk.CTkFrame(self)
        form_frame.pack(fill="x", padx=10, pady=10)

        # Data da venda (padrão: hoje)
        ctk.CTkLabel(form_frame, text="Data (YYYY-MM-DD):").grid(row=0, column=0, sticky="w")
        self.date_entry = ctk.CTkEntry(form_frame)
        self.date_entry.grid(row=0, column=1, padx=5, pady=5)
        self.date_entry.insert(0, date.today().isoformat())

        # Canal
        ctk.CTkLabel(form_frame, text="Canal:").grid(row=0, column=2, sticky="w")
        self.channel_var = tk.StringVar(value=self.CHANNEL_OPTIONS[0])
        self.channel_menu = ctk.CTkOptionMenu(form_frame, variable=self.channel_var, values=self.CHANNEL_OPTIONS)
        self.channel_menu.grid(row=0, column=3, padx=5, pady=5)

        # Referência do pedido
        ctk.CTkLabel(form_frame, text="Pedido/Ref.:").grid(row=1, column=0, sticky="w")
        self.ref_entry = ctk.CTkEntry(form_frame)
        self.ref_entry.grid(row=1, column=1, padx=5, pady=5)

        # Cliente
        ctk.CTkLabel(form_frame, text="Cliente:").grid(row=1, column=2, sticky="w")
        self.customer_entry = ctk.CTkEntry(form_frame)
        self.customer_entry.grid(row=1, column=3, padx=5, pady=5)

        # Notas
        ctk.CTkLabel(form_frame, text="Observações:").grid(row=2, column=0, sticky="nw")
        self.notes_text = tk.Text(form_frame, height=3, width=40)
        self.notes_text.grid(row=2, column=1, columnspan=3, padx=5, pady=5, sticky="ew")

        # Seção para adicionar itens
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
        self.item_price_entry = ctk.CTkEntry(item_frame, width=80)
        self.item_price_entry.grid(row=0, column=5, padx=5, pady=5)
        ctk.CTkLabel(item_frame, text="Taxa:").grid(row=0, column=6, sticky="w")
        self.item_fee_entry = ctk.CTkEntry(item_frame, width=80)
        self.item_fee_entry.grid(row=0, column=7, padx=5, pady=5)
        ctk.CTkLabel(item_frame, text="Desconto:").grid(row=0, column=8, sticky="w")
        self.item_discount_entry = ctk.CTkEntry(item_frame, width=80)
        self.item_discount_entry.grid(row=0, column=9, padx=5, pady=5)
        self.add_item_button = ctk.CTkButton(item_frame, text="Adicionar Item", command=self.add_item)
        self.add_item_button.grid(row=0, column=10, padx=10, pady=5)

        # Tabela de itens adicionados
        self.item_tree = ttk.Treeview(
            self,
            columns=("sku", "qty", "price", "fees", "discount"),
            show="headings",
        )
        for col, text in [
            ("sku", "SKU"),
            ("qty", "Qtd"),
            ("price", "Preço"),
            ("fees", "Taxa"),
            ("discount", "Desc."),
        ]:
            self.item_tree.heading(col, text=text)
            self.item_tree.column(col, minwidth=50, width=80, anchor="center")
        self.item_tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.item_tree.bind("<ButtonRelease-1>", self.on_item_select)

        # Botões de ação
        action_frame = ctk.CTkFrame(self)
        action_frame.pack(fill="x", padx=10)
        self.save_button = ctk.CTkButton(action_frame, text="Salvar Venda", command=self.save_sale)
        self.save_button.pack(side="left", padx=5, pady=5)
        self.remove_item_button = ctk.CTkButton(action_frame, text="Remover Item", command=self.remove_selected_item)
        self.remove_item_button.pack(side="left", padx=5, pady=5)
        self.clear_button = ctk.CTkButton(action_frame, text="Limpar", command=self.clear_form)
        self.clear_button.pack(side="left", padx=5, pady=5)

    def add_item(self):
        """Adiciona item à lista temporária e à tabela."""
        sku = self.item_sku_entry.get().strip()
        qty = self.item_qty_entry.get().strip()
        price = self.item_price_entry.get().strip()
        fee = self.item_fee_entry.get().strip() or "0"
        discount = self.item_discount_entry.get().strip() or "0"
        # Validações
        if not is_non_empty(sku):
            messagebox.showwarning("SKU", "Informe o SKU do produto.")
            return
        if not is_positive_integer(qty):
            messagebox.showwarning("Quantidade", "Quantidade deve ser um inteiro positivo.")
            return
        if not is_non_negative_float(price) or not is_non_negative_float(fee) or not is_non_negative_float(discount):
            messagebox.showwarning("Valores", "Preço, taxa e desconto devem ser números válidos (>= 0).")
            return

        # Verifica se o SKU de VARIAÇÃO existe no banco
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
        # Adiciona ao Treeview
        self.item_tree.insert(
            "",
            "end",
            values=(sku, qty, f"{float(price):.2f}", f"{float(fee):.2f}", f"{float(discount):.2f}"),
        )
        # Limpa campos de item
        self.item_sku_entry.delete(0, tk.END)
        self.item_qty_entry.delete(0, tk.END)
        self.item_price_entry.delete(0, tk.END)
        self.item_fee_entry.delete(0, tk.END)
        self.item_discount_entry.delete(0, tk.END)

    def on_item_select(self, event):
        """Seleção de item na tabela (placeholder)."""
        pass

    def remove_selected_item(self):
        """Remove item selecionado da tabela e da lista temporária."""
        selection = self.item_tree.selection()
        if not selection:
            return
        idx = self.item_tree.index(selection[0])
        self.item_tree.delete(selection[0])
        if 0 <= idx < len(self.items):
            del self.items[idx]

    def save_sale(self):
        """Registra a venda e limpa o formulário."""
        sale_date = self.date_entry.get().strip()
        channel = self.channel_var.get()
        ref = self.ref_entry.get().strip()
        customer = self.customer_entry.get().strip()
        notes = self.notes_text.get("1.0", tk.END).strip()

        if not self.items:
            messagebox.showwarning("Itens", "Adicione ao menos um item à venda.")
            return
        try:
            sale_id = create_sale(
                self.conn,
                sale_date=sale_date,
                channel=channel,
                order_ref=ref,
                customer_name=customer,
                notes=notes,
                items=self.items,
            )
        except Exception as e:
            messagebox.showerror("Erro ao salvar venda", str(e))
            return
        messagebox.showinfo("Venda", f"Venda registrada com sucesso (ID {sale_id})")
        self.clear_form()

    def clear_form(self):
        """Limpa todos os campos e a lista de itens."""
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, date.today().isoformat())
        self.ref_entry.delete(0, tk.END)
        self.customer_entry.delete(0, tk.END)
        self.notes_text.delete("1.0", tk.END)
        # Limpa itens
        for row in self.item_tree.get_children():
            self.item_tree.delete(row)
        self.items.clear()