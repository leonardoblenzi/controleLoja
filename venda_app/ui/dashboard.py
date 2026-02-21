"""
Tela inicial e container de navegação.

Este módulo define a classe `MainApp` que cria a janela principal
utilizando CustomTkinter. Ela inclui um menu lateral de navegação
permitindo alternar entre diferentes telas (dashboard, produtos,
vendas, estoque etc.). Para simplicidade, algumas telas são
placeholders.
"""

import customtkinter as ctk
from datetime import date

from ..services.inventory_service import get_product_stock_levels

from ..db.database import init_db, get_connection
from .products import ProductsFrame
from .sales import SalesFrame
from .stock import StockFrame
from .moves import MovesFrame
from .finance import FinanceFrame
from .expenses import ExpensesFrame


class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Controle de Vendas e Estoque")
        self.geometry("1024x640")
        self.minsize(900, 600)

        # Inicializa o banco de dados
        init_db()
        self.conn = get_connection()

        # Configure grid: coluna 0 para menu, coluna 1 para conteúdo
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Menu lateral
        self.menu_frame = ctk.CTkFrame(self, corner_radius=0)
        self.menu_frame.grid(row=0, column=0, sticky="ns")

        # Botões do menu
        btn_specs = [
            ("Dashboard", self.show_dashboard),
            ("Produtos", self.show_products),
            ("Vendas", self.show_sales),
            ("Estoque", self.show_stock),
            ("Movimentações", self.show_moves),
            ("Financeiro", self.show_finance),
            ("Gastos", self.show_expenses),
        ]
        for i, (text, callback) in enumerate(btn_specs):
            btn = ctk.CTkButton(
                self.menu_frame,
                text=text,
                command=callback,
                corner_radius=0,
                fg_color="transparent",
                hover=True,
            )
            btn.grid(row=i, column=0, sticky="ew", padx=10, pady=5)

        # Frame de conteúdo (alterado por navegação)
        self.content_frame = ctk.CTkFrame(self, corner_radius=0)
        self.content_frame.grid(row=0, column=1, sticky="nsew")
        self.content_frame.grid_rowconfigure(0, weight=1)
        self.content_frame.grid_columnconfigure(0, weight=1)

        # Frames das telas (cache)
        self.frames = {}

        # Exibe tela inicial
        self.show_dashboard()

    def clear_content(self):
        """Esconde (não destrói) as telas do frame de conteúdo."""
        for widget in self.content_frame.winfo_children():
            try:
                widget.grid_remove()
            except Exception:
                # fallback caso algum widget use pack
                try:
                    widget.pack_forget()
                except Exception:
                    pass

    def _show_frame(self, key: str, factory):
        """
        Helper: esconde todas as telas e mostra uma específica.
        - key: nome no dict self.frames
        - factory: função/lambda que cria o frame quando não existir
        """
        self.clear_content()

        # Se não existe ou foi destruído, recria
        if key not in self.frames or not self.frames[key].winfo_exists():
            self.frames[key] = factory()
            self.frames[key].grid(row=0, column=0, sticky="nsew")
        else:
            # só mostra de novo
            self.frames[key].grid()

    # Métodos de exibição para cada tela
    def show_dashboard(self):
        def factory():
            frame = DashboardFrame(self.content_frame, self.conn)
            return frame

        self._show_frame("dashboard", factory)

        # se o frame já existia, apenas atualiza KPIs
        try:
            f = self.frames.get("dashboard")
            if hasattr(f, "refresh"):
                f.refresh()
        except Exception:
            pass

    def show_products(self):
        self._show_frame("products", lambda: ProductsFrame(self.content_frame, self.conn))

    def show_sales(self):
        self._show_frame("sales", lambda: SalesFrame(self.content_frame, self.conn))

    def show_stock(self):
        self._show_frame("stock", lambda: StockFrame(self.content_frame, self.conn))

    def show_moves(self):
        self._show_frame("moves", lambda: MovesFrame(self.content_frame, self.conn))

    def show_finance(self):
        self._show_frame("finance", lambda: FinanceFrame(self.content_frame, self.conn))

    def show_expenses(self):
        self._show_frame("expenses", lambda: ExpensesFrame(self.content_frame, self.conn))


def run_app() -> None:
    """Função de conveniência para iniciar a aplicação."""
    app = MainApp()
    app.mainloop()


if __name__ == "__main__":
    run_app()


class DashboardFrame(ctk.CTkFrame):
    """Dashboard com KPIs e visual mais vivo."""

    def __init__(self, master, conn):
        super().__init__(master)
        self.conn = conn

        header = ctk.CTkFrame(self)
        header.pack(fill="x", padx=14, pady=(14, 10))

        ctk.CTkLabel(
            header,
            text="📊 Dashboard",
            font=("Helvetica", 20, "bold"),
        ).pack(side="left", padx=10, pady=10)

        ctk.CTkButton(header, text="🔄 Atualizar", width=140, command=self.refresh).pack(side="right", padx=10, pady=10)

        self.cards = ctk.CTkFrame(self)
        self.cards.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.cards.grid_columnconfigure((0, 1), weight=1)
        self.cards.grid_rowconfigure((0, 1), weight=0)

        self.kpi_widgets = {}
        self._make_card(0, 0, "💰 Receita líquida (mês)", "0,00", "#1f6aa5")
        self._make_card(0, 1, "🧾 Gastos (mês)", "0,00", "#6a1fa5")
        self._make_card(1, 0, "📈 Lucro (mês)", "0,00", "#1f8a5a")
        self._make_card(1, 1, "⚠️ Abaixo do mínimo", "0", "#a56a1f")

        self.refresh()

    def _make_card(self, r: int, c: int, title: str, value: str, accent: str):
        card = ctk.CTkFrame(self.cards)
        card.grid(row=r, column=c, sticky="nsew", padx=8, pady=8)

        bar = ctk.CTkFrame(card, fg_color=accent, corner_radius=10)
        bar.pack(fill="x", padx=10, pady=(10, 6))
        ctk.CTkLabel(bar, text=title, font=("Helvetica", 13, "bold")).pack(anchor="w", padx=10, pady=6)

        val_lbl = ctk.CTkLabel(card, text=value, font=("Helvetica", 26, "bold"))
        val_lbl.pack(anchor="w", padx=18, pady=(6, 14))

        self.kpi_widgets[title] = val_lbl

    def refresh(self):
        today = date.today()
        month_start = today.replace(day=1).isoformat()
        today_str = today.isoformat()
        cur = self.conn.cursor()

        # Receita líquida e lucro
        cur.execute(
            """
            SELECT
                COALESCE(SUM(total_net), 0) AS revenue,
                COALESCE(SUM(total_profit), 0) AS profit
            FROM sales
            WHERE sale_date BETWEEN ? AND ?
            """,
            (month_start, today_str),
        )
        row = cur.fetchone()
        revenue = float(row["revenue"]) if row else 0.0
        profit = float(row["profit"]) if row else 0.0

        # Gastos
        cur.execute(
            """
            SELECT COALESCE(SUM(amount), 0) AS expenses
            FROM expenses
            WHERE exp_date BETWEEN ? AND ?
            """,
            (month_start, today_str),
        )
        exp = cur.fetchone()
        expenses = float(exp["expenses"]) if exp else 0.0

        # Compras via movimentações (IN + COMPRA) entram como gasto
        cur.execute(
            """
            SELECT COALESCE(SUM(qty * unit_cost), 0) AS purchases
              FROM stock_moves
             WHERE move_type = 'IN'
               AND UPPER(reason) = 'COMPRA'
               AND move_date BETWEEN ? AND ?
            """,
            (month_start, today_str),
        )
        prow = cur.fetchone()
        purchases = float(prow["purchases"]) if prow else 0.0
        expenses_total = expenses + purchases

        # Produtos abaixo do mínimo (estoque total por produto)
        stock_by_product = get_product_stock_levels(self.conn)
        cur.execute("SELECT id, stock_min FROM products WHERE is_active = 1")
        low = 0
        for r in cur.fetchall():
            pid = int(r["id"])
            min_stock = int(r["stock_min"])
            if int(stock_by_product.get(pid, 0)) < min_stock:
                low += 1

        def brl(x: float) -> str:
            return f"{x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        self.kpi_widgets["💰 Receita líquida (mês)"].configure(text=brl(revenue))
        self.kpi_widgets["🧾 Gastos (mês)"].configure(text=brl(expenses_total))
        self.kpi_widgets["📈 Lucro (mês)"].configure(text=brl(profit))
        self.kpi_widgets["⚠️ Abaixo do mínimo"].configure(text=str(low))