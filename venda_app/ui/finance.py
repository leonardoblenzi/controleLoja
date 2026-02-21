"""
Tela financeira: gastos x lucros.

Permite escolher um intervalo de datas e visualizar um resumo
financeiro, incluindo receita, custo, lucro, gastos e resultado final.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
from datetime import date, timedelta

from ..services.reports_service import get_financial_summary


class FinanceFrame(ctk.CTkFrame):
    def __init__(self, master, conn):
        super().__init__(master)
        self.conn = conn
        self.create_widgets()

    def create_widgets(self):
        form_frame = ctk.CTkFrame(self)
        form_frame.pack(fill="x", padx=10, pady=10)

        # Data inicial
        ctk.CTkLabel(form_frame, text="De (YYYY-MM-DD):").grid(row=0, column=0, sticky="w")
        self.from_entry = ctk.CTkEntry(form_frame)
        self.from_entry.grid(row=0, column=1, padx=5, pady=5)
        first_day = date.today().replace(day=1)
        self.from_entry.insert(0, first_day.isoformat())

        # Data final
        ctk.CTkLabel(form_frame, text="Até (YYYY-MM-DD):").grid(row=0, column=2, sticky="w")
        self.to_entry = ctk.CTkEntry(form_frame)
        self.to_entry.grid(row=0, column=3, padx=5, pady=5)
        self.to_entry.insert(0, date.today().isoformat())

        # Botão calcular
        calc_btn = ctk.CTkButton(form_frame, text="Calcular", command=self.calculate)
        calc_btn.grid(row=0, column=4, padx=10, pady=5)

        # Exibição do resumo
        self.result_frame = ctk.CTkFrame(self)
        self.result_frame.pack(fill="both", expand=True, padx=10, pady=10)
        self.result_labels = {}
        for i, key in enumerate(["Receita líquida", "Custo", "Lucro", "Gastos", "Resultado"]):
            lbl = ctk.CTkLabel(self.result_frame, text=f"{key}: 0,00", font=("Helvetica", 14))
            lbl.pack(anchor="w", pady=5)
            self.result_labels[key] = lbl

    def calculate(self):
        date_from = self.from_entry.get().strip()
        date_to = self.to_entry.get().strip()
        try:
            summary = get_financial_summary(self.conn, date_from, date_to)
        except Exception as e:
            messagebox.showerror("Erro ao calcular", str(e))
            return
        mapping = {
            "Receita líquida": summary["revenue"],
            "Custo": summary["cost"],
            "Lucro": summary["profit"],
            "Gastos": summary["expenses"],
            "Resultado": summary["result"],
        }

        def brl(x: float) -> str:
            return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        for key, value in mapping.items():
            self.result_labels[key].configure(text=f"{key}: {brl(float(value))}")