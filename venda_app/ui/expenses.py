"""
Tela de gastos.

Permite lançar gastos em categorias pré-definidas e listar gastos
registrados. Esta implementação suporta apenas funcionalidade básica.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

from ..db.repositories import ExpenseRepository
from ..utils.validators import is_non_empty, is_non_negative_float


class ExpensesFrame(ctk.CTkFrame):
    CATEGORIES = ["COMPRA_ESTOQUE", "MARKETING", "FIXO", "INVESTIMENTO", "OUTROS"]

    def __init__(self, master, conn):
        super().__init__(master)
        self.conn = conn
        self.create_widgets()
        self.load_expenses()

    def create_widgets(self):
        form_frame = ctk.CTkFrame(self)
        form_frame.pack(fill="x", padx=10, pady=10)

        # Data
        ctk.CTkLabel(form_frame, text="Data (YYYY-MM-DD):").grid(row=0, column=0, sticky="w")
        self.date_entry = ctk.CTkEntry(form_frame)
        self.date_entry.grid(row=0, column=1, padx=5, pady=5)
        self.date_entry.insert(0, date.today().isoformat())

        # Categoria
        ctk.CTkLabel(form_frame, text="Categoria:").grid(row=0, column=2, sticky="w")
        self.category_var = tk.StringVar(value=self.CATEGORIES[0])
        self.category_menu = ctk.CTkOptionMenu(form_frame, variable=self.category_var, values=self.CATEGORIES)
        self.category_menu.grid(row=0, column=3, padx=5, pady=5)

        # Descrição
        ctk.CTkLabel(form_frame, text="Descrição:").grid(row=1, column=0, sticky="w")
        self.desc_entry = ctk.CTkEntry(form_frame, width=250)
        self.desc_entry.grid(row=1, column=1, columnspan=3, padx=5, pady=5, sticky="ew")

        # Valor
        ctk.CTkLabel(form_frame, text="Valor:").grid(row=2, column=0, sticky="w")
        self.amount_entry = ctk.CTkEntry(form_frame)
        self.amount_entry.grid(row=2, column=1, padx=5, pady=5)

        # Forma pagamento
        ctk.CTkLabel(form_frame, text="Forma pgto:").grid(row=2, column=2, sticky="w")
        self.payment_entry = ctk.CTkEntry(form_frame)
        self.payment_entry.grid(row=2, column=3, padx=5, pady=5)

        # Observação
        ctk.CTkLabel(form_frame, text="Observações:").grid(row=3, column=0, sticky="w")
        self.notes_entry = ctk.CTkEntry(form_frame, width=250)
        self.notes_entry.grid(row=3, column=1, columnspan=3, padx=5, pady=5, sticky="ew")

        # Botões
        action_frame = ctk.CTkFrame(self)
        action_frame.pack(fill="x", padx=10)
        save_btn = ctk.CTkButton(action_frame, text="Lançar Gasto", command=self.save_expense)
        save_btn.pack(side="left", padx=5, pady=5)
        clear_btn = ctk.CTkButton(action_frame, text="Limpar", command=self.clear_form)
        clear_btn.pack(side="left", padx=5, pady=5)

        # Lista de gastos
        self.tree = ttk.Treeview(
            self,
            columns=("date", "category", "description", "amount", "payment", "notes"),
            show="headings",
        )
        for col, text in [
            ("date", "Data"),
            ("category", "Categoria"),
            ("description", "Descrição"),
            ("amount", "Valor"),
            ("payment", "Forma"),
            ("notes", "Observações"),
        ]:
            self.tree.heading(col, text=text)
            self.tree.column(col, minwidth=80, width=120, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

    def save_expense(self):
        exp_date = self.date_entry.get().strip()
        category = self.category_var.get()
        description = self.desc_entry.get().strip()
        amount = self.amount_entry.get().strip()
        payment = self.payment_entry.get().strip()
        notes = self.notes_entry.get().strip()
        # Valida
        if not is_non_empty(description):
            messagebox.showwarning("Descrição", "Informe a descrição do gasto.")
            return
        if not is_non_negative_float(amount):
            messagebox.showwarning("Valor", "Valor deve ser um número não negativo.")
            return
        expense_data = {
            "exp_date": exp_date,
            "category": category,
            "description": description,
            "amount": float(amount),
            "payment_method": payment or None,
            "notes": notes or None,
        }
        ExpenseRepository.add_expense(self.conn, expense_data)
        messagebox.showinfo("Gastos", "Gasto lançado com sucesso!")
        self.clear_form()
        self.load_expenses()

    def clear_form(self):
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, date.today().isoformat())
        self.desc_entry.delete(0, tk.END)
        self.amount_entry.delete(0, tk.END)
        self.payment_entry.delete(0, tk.END)
        self.notes_entry.delete(0, tk.END)

    def load_expenses(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        cur = self.conn.cursor()
        cur.execute(
            """
            SELECT exp_date, category, description, amount, payment_method, notes
            FROM expenses
            ORDER BY exp_date DESC, id DESC
            LIMIT 100
            """
        )
        for exp_date, category, desc, amount, payment, notes in cur.fetchall():
            self.tree.insert(
                "",
                "end",
                values=(exp_date, category, desc, f"{amount:.2f}", payment or "", notes or ""),
            )