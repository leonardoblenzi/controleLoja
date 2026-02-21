"""venda_app.ui.products

Tela de Produtos + Categorias (dentro da mesma aba).

Regras:
 - Categoria é obrigatória.
 - Estoque/Venda sempre por variação (variant_id).
 - Produto SEM variação real ainda terá 1 variação "Única".
 - SKU das variações pode ser gerado automaticamente (editável).
"""

from __future__ import annotations

import re
import unicodedata

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox

from ..db.repositories import (
    CategoryRepository,
    Product,
    ProductRepository,
    ProductVariant,
    VariantRepository,
    StockMoveRepository,
)
from ..utils.validators import is_non_empty, is_non_negative_float, is_positive_integer


def _slug(text: str) -> str:
    """Converte texto em um sufixo seguro para SKU."""
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^A-Za-z0-9]+", "-", text).strip("-")
    return text.upper() or "VAR"


class ProductsFrame(ctk.CTkFrame):
    def __init__(self, master, conn):
        super().__init__(master)
        self.conn = conn

        # seleção
        self.selected_product_id: int | None = None
        self.selected_category_id: int | None = None

        # categorias para dropdown
        self.category_name_to_id: dict[str, int] = {}
        self.category_names: list[str] = []

        # variações em edição (somente UI)
        self.variant_rows: list[dict] = []  # {value, sku, stock_initial}

        self.create_widgets()
        self.switch_view("Produtos")

        self.load_categories()
        self.refresh_category_dropdown()
        self.load_products()

    # ---------------- UI base ----------------
    def create_widgets(self):
        top_nav = ctk.CTkFrame(self)
        top_nav.pack(fill="x", padx=10, pady=(10, 5))

        self.nav = ctk.CTkSegmentedButton(
            top_nav,
            values=["Produtos", "Categorias"],
            command=self.switch_view,
        )
        self.nav.pack(side="left", padx=5, pady=5)
        self.nav.set("Produtos")

        self.view_container = ctk.CTkFrame(self)
        self.view_container.pack(fill="both", expand=True, padx=10, pady=10)
        self.view_container.grid_rowconfigure(0, weight=1)
        self.view_container.grid_columnconfigure(0, weight=1)

        self.products_view = ctk.CTkFrame(self.view_container)
        self.categories_view = ctk.CTkFrame(self.view_container)
        self.products_view.grid(row=0, column=0, sticky="nsew")
        self.categories_view.grid(row=0, column=0, sticky="nsew")

        self._build_products_view()
        self._build_categories_view()

    def switch_view(self, value: str):
        if value == "Produtos":
            self.categories_view.grid_remove()
            self.products_view.grid()
        else:
            self.products_view.grid_remove()
            self.categories_view.grid()

    # ---------------- Produtos ----------------
    def _build_products_view(self):
        form = ctk.CTkFrame(self.products_view)
        form.pack(fill="x", padx=10, pady=(10, 8))

        # Linha 0
        ctk.CTkLabel(form, text="SKU:").grid(row=0, column=0, sticky="w")
        self.sku_entry = ctk.CTkEntry(form, width=220)
        self.sku_entry.grid(row=0, column=1, padx=6, pady=6, sticky="w")

        ctk.CTkLabel(form, text="Nome:").grid(row=0, column=2, sticky="w")
        self.name_entry = ctk.CTkEntry(form, width=320)
        self.name_entry.grid(row=0, column=3, padx=6, pady=6, sticky="w")

        # Linha 1
        ctk.CTkLabel(form, text="Categoria:").grid(row=1, column=0, sticky="w")
        self.category_var = tk.StringVar(value="")
        self.category_menu = ctk.CTkOptionMenu(form, variable=self.category_var, values=["(Cadastre uma categoria)"])
        # correção visual: tamanho fixo e alinhamento
        self.category_menu.configure(width=240, height=30)
        self.category_menu.grid(row=1, column=1, padx=6, pady=6, sticky="w")

        ctk.CTkLabel(form, text="Marca:").grid(row=1, column=2, sticky="w")
        self.brand_entry = ctk.CTkEntry(form, width=320)
        self.brand_entry.grid(row=1, column=3, padx=6, pady=6, sticky="w")

        # Linha 2
        ctk.CTkLabel(form, text="Custo:").grid(row=2, column=0, sticky="w")
        self.cost_entry = ctk.CTkEntry(form, width=220)
        self.cost_entry.grid(row=2, column=1, padx=6, pady=6, sticky="w")

        ctk.CTkLabel(form, text="Preço:").grid(row=2, column=2, sticky="w")
        self.price_entry = ctk.CTkEntry(form, width=220)
        self.price_entry.grid(row=2, column=3, padx=6, pady=6, sticky="w")

        # Linha 3
        ctk.CTkLabel(form, text="Estoque mín.:").grid(row=3, column=0, sticky="w")
        self.stock_min_entry = ctk.CTkEntry(form, width=220)
        self.stock_min_entry.grid(row=3, column=1, padx=6, pady=6, sticky="w")

        self.active_var = tk.IntVar(value=1)
        self.active_check = ctk.CTkCheckBox(form, text="Ativo", variable=self.active_var)
        self.active_check.grid(row=3, column=3, padx=6, pady=6, sticky="w")

        # Linha 4: variações
        self.has_variants_var = tk.IntVar(value=0)
        self.has_variants_check = ctk.CTkCheckBox(
            form,
            text="Este produto tem variações",
            variable=self.has_variants_var,
            command=self._toggle_variants_block,
        )
        self.has_variants_check.grid(row=4, column=0, columnspan=2, padx=6, pady=(6, 10), sticky="w")

        ctk.CTkLabel(form, text="Atributo:").grid(row=4, column=2, sticky="w")
        self.variant_attr_entry = ctk.CTkEntry(form, width=220)
        self.variant_attr_entry.grid(row=4, column=3, padx=6, pady=(6, 10), sticky="w")

        # Bloco variações (aparece quando checkbox ligado)
        self.variants_block = ctk.CTkFrame(self.products_view)
        self.variants_block.pack(fill="x", padx=10, pady=(0, 8))

        vtop = ctk.CTkFrame(self.variants_block)
        vtop.pack(fill="x", padx=10, pady=(10, 6))

        ctk.CTkLabel(vtop, text="Variações", font=("Helvetica", 14, "bold")).pack(side="left")

        self.btn_add_variant = ctk.CTkButton(
            vtop,
            text="+ Adicionar",
            command=self._add_variant_row,
            width=120,
        )
        self.btn_add_variant.pack(side="right", padx=6)

        self.btn_remove_variant = ctk.CTkButton(
            vtop,
            text="Remover",
            command=self._remove_selected_variant,
            width=120,
            fg_color="#8a2b2b",
            hover_color="#a83a3a",
        )
        self.btn_remove_variant.pack(side="right", padx=6)

        self.variants_tree = ttk.Treeview(
            self.variants_block,
            columns=("value", "sku", "stock"),
            show="headings",
            height=5,
        )
        self.variants_tree.heading("value", text="Valor (ex: Preto)")
        self.variants_tree.heading("sku", text="SKU da variação")
        self.variants_tree.heading("stock", text="Estoque inicial")
        self.variants_tree.column("value", width=220, anchor="w")
        self.variants_tree.column("sku", width=220, anchor="w")
        self.variants_tree.column("stock", width=120, anchor="center")
        self.variants_tree.pack(fill="x", padx=10, pady=(0, 10))

        # Botões
        btns = ctk.CTkFrame(self.products_view)
        btns.pack(fill="x", padx=10, pady=(0, 10))

        self.btn_save = ctk.CTkButton(btns, text="Salvar", command=self.save_product, width=140)
        self.btn_save.pack(side="left", padx=6, pady=6)

        self.btn_clear = ctk.CTkButton(
            btns,
            text="Limpar",
            command=self.clear_product_form,
            width=140,
            fg_color="#3a3a3a",
            hover_color="#4a4a4a",
        )
        self.btn_clear.pack(side="left", padx=6, pady=6)

        self.btn_refresh = ctk.CTkButton(
            btns,
            text="Atualizar categorias",
            command=self._refresh_categories_from_db,
            width=180,
        )
        self.btn_refresh.pack(side="right", padx=6, pady=6)

        # Lista produtos
        self.products_tree = ttk.Treeview(
            self.products_view,
            columns=("sku", "name", "category", "brand", "cost", "price", "stock_min", "active"),
            show="headings",
        )
        for col, text, w in [
            ("sku", "SKU", 140),
            ("name", "Nome", 220),
            ("category", "Categoria", 160),
            ("brand", "Marca", 140),
            ("cost", "Custo", 90),
            ("price", "Preço", 90),
            ("stock_min", "Est. mín.", 90),
            ("active", "Ativo", 70),
        ]:
            self.products_tree.heading(col, text=text)
            self.products_tree.column(col, width=w, anchor="center")
        self.products_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.products_tree.bind("<ButtonRelease-1>", self._on_select_product)

        self._toggle_variants_block()  # aplica estado inicial

    def _toggle_variants_block(self):
        show = bool(self.has_variants_var.get())
        if show:
            self.variant_attr_entry.configure(state="normal")
            self.variants_block.pack(fill="x", padx=10, pady=(0, 8))
        else:
            self.variant_attr_entry.delete(0, tk.END)
            self.variant_attr_entry.insert(0, "")
            self.variants_block.pack_forget()
            # limpa variações em edição
            self._clear_variants_editor()

    def _clear_variants_editor(self):
        for iid in self.variants_tree.get_children():
            self.variants_tree.delete(iid)
        self.variant_rows.clear()

    def _add_variant_row(self):
        if not self.has_variants_var.get():
            messagebox.showinfo("Variações", "Marque 'Este produto tem variações' primeiro.")
            return

        sku_base = self.sku_entry.get().strip()
        if not sku_base:
            messagebox.showwarning("SKU", "Informe o SKU do produto antes de adicionar variações.")
            return

        # abre um mini prompt simples
        win = ctk.CTkToplevel(self)
        win.title("Adicionar variação")
        win.geometry("460x220")
        win.transient(self.winfo_toplevel())
        win.grab_set()

        ctk.CTkLabel(win, text="Valor da variação (ex: Preto)").pack(anchor="w", padx=14, pady=(14, 4))
        val_entry = ctk.CTkEntry(win)
        val_entry.pack(fill="x", padx=14)

        ctk.CTkLabel(win, text="SKU da variação (opcional, será gerado)").pack(anchor="w", padx=14, pady=(10, 4))
        sku_entry = ctk.CTkEntry(win)
        sku_entry.pack(fill="x", padx=14)

        ctk.CTkLabel(win, text="Estoque inicial").pack(anchor="w", padx=14, pady=(10, 4))
        stock_entry = ctk.CTkEntry(win)
        stock_entry.insert(0, "0")
        stock_entry.pack(fill="x", padx=14)

        def on_add():
            value = val_entry.get().strip()
            if not value:
                messagebox.showwarning("Variação", "Informe o valor da variação.")
                return
            vsku = sku_entry.get().strip()
            if not vsku:
                vsku = f"{sku_base}-{_slug(value)}"
            stock_init = stock_entry.get().strip() or "0"
            if stock_init and not stock_init.isdigit():
                messagebox.showwarning("Estoque", "Estoque inicial deve ser um inteiro >= 0")
                return

            self.variant_rows.append({"value": value, "sku": vsku, "stock_initial": int(stock_init)})
            self.variants_tree.insert("", "end", values=(value, vsku, int(stock_init)))
            win.destroy()

        btns = ctk.CTkFrame(win)
        btns.pack(fill="x", padx=14, pady=14)
        ctk.CTkButton(btns, text="Adicionar", command=on_add).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="Cancelar", fg_color="#3a3a3a", hover_color="#4a4a4a", command=win.destroy).pack(side="left", padx=6)

    def _remove_selected_variant(self):
        sel = self.variants_tree.selection()
        if not sel:
            return
        idx = self.variants_tree.index(sel[0])
        self.variants_tree.delete(sel[0])
        if 0 <= idx < len(self.variant_rows):
            del self.variant_rows[idx]

    def _refresh_categories_from_db(self):
        self.load_categories()
        self.refresh_category_dropdown()
        messagebox.showinfo("Categorias", "Categorias atualizadas.")

    def load_categories(self):
        cats_active = CategoryRepository.list_categories(self.conn, only_active=True)
        self.category_name_to_id = {c.name: int(c.id) for c in cats_active if c.id is not None}
        self.category_names = list(self.category_name_to_id.keys())

        # atualiza lista na aba categorias
        cats_all = CategoryRepository.list_categories(self.conn, only_active=False)
        if hasattr(self, "cat_tree"):
            for iid in self.cat_tree.get_children():
                self.cat_tree.delete(iid)
            for c in cats_all:
                self.cat_tree.insert("", "end", iid=c.id, values=(c.name, "Sim" if c.is_active else "Não"))

    def refresh_category_dropdown(self):
        if not self.category_names:
            self.category_menu.configure(values=["(Cadastre uma categoria)"])
            self.category_var.set("(Cadastre uma categoria)")
            return
        self.category_menu.configure(values=self.category_names)
        if self.category_var.get() not in self.category_names:
            self.category_var.set(self.category_names[0])

    def load_products(self):
        for iid in self.products_tree.get_children():
            self.products_tree.delete(iid)

        rows = ProductRepository.get_all_products_rows(self.conn)
        for r in rows:
            self.products_tree.insert(
                "",
                "end",
                iid=r["id"],
                values=(
                    r["sku"],
                    r["name"],
                    r["category_name"],
                    r["brand"] or "",
                    f"{float(r['cost_default']):.2f}",
                    f"{float(r['price_default']):.2f}",
                    int(r["stock_min"]),
                    "Sim" if bool(r["is_active"]) else "Não",
                ),
            )

    def clear_product_form(self):
        self.selected_product_id = None
        self.sku_entry.configure(state="normal")

        for e in [self.sku_entry, self.name_entry, self.brand_entry, self.cost_entry, self.price_entry, self.stock_min_entry, self.variant_attr_entry]:
            e.delete(0, tk.END)

        self.active_var.set(1)
        self.has_variants_var.set(0)
        self._toggle_variants_block()
        self.refresh_category_dropdown()
        self.btn_save.configure(text="Salvar")

    def _on_select_product(self, event):
        sel = self.products_tree.selection()
        if not sel:
            return
        pid = int(sel[0])
        product = ProductRepository.get_product_by_id(self.conn, pid)
        if not product:
            return

        self.selected_product_id = pid
        self.sku_entry.configure(state="normal")
        self.sku_entry.delete(0, tk.END)
        self.sku_entry.insert(0, product.sku)
        # para evitar dor com SKU mudando (afeta SKU das variações), travamos em edição
        self.sku_entry.configure(state="disabled")

        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, product.name)

        # categoria
        # encontra nome pelo id
        cat_name = None
        for name, cid in self.category_name_to_id.items():
            if cid == product.category_id:
                cat_name = name
                break
        if cat_name:
            self.category_var.set(cat_name)

        self.brand_entry.delete(0, tk.END)
        self.brand_entry.insert(0, product.brand or "")

        self.cost_entry.delete(0, tk.END)
        self.cost_entry.insert(0, str(product.cost_default))

        self.price_entry.delete(0, tk.END)
        self.price_entry.insert(0, str(product.price_default))

        self.stock_min_entry.delete(0, tk.END)
        self.stock_min_entry.insert(0, str(product.stock_min))

        self.active_var.set(1 if product.is_active else 0)

        # carrega variações
        variants = VariantRepository.list_variants_by_product(self.conn, pid, only_active=False)
        has_real_variants = any((not v.is_default) and v.is_active for v in variants)
        self.has_variants_var.set(1 if has_real_variants else 0)

        self.variant_attr_entry.delete(0, tk.END)
        self.variant_attr_entry.insert(0, product.variant_attribute_name or ("Cor" if has_real_variants else ""))

        self._toggle_variants_block()
        self._clear_variants_editor()

        if has_real_variants:
            for v in variants:
                if v.is_default:
                    continue
                self.variant_rows.append({"value": v.variant_value, "sku": v.variant_sku, "stock_initial": 0})
                self.variants_tree.insert("", "end", values=(v.variant_value, v.variant_sku, 0))

        self.btn_save.configure(text="Atualizar")

    def save_product(self):
        # categoria obrigatória
        if not self.category_names:
            messagebox.showwarning("Categoria", "Cadastre uma categoria antes de cadastrar produtos.")
            self.nav.set("Categorias")
            self.switch_view("Categorias")
            return

        cat_name = self.category_var.get().strip()
        if cat_name not in self.category_name_to_id:
            messagebox.showwarning("Categoria", "Selecione uma categoria válida.")
            return
        category_id = self.category_name_to_id[cat_name]

        sku = self.sku_entry.get().strip()
        name = self.name_entry.get().strip()
        brand = self.brand_entry.get().strip() or None
        cost = self.cost_entry.get().strip() or "0"
        price = self.price_entry.get().strip() or "0"
        stock_min = self.stock_min_entry.get().strip() or "0"
        is_active = bool(self.active_var.get())

        if not is_non_empty(sku) or not is_non_empty(name):
            messagebox.showwarning("Campos obrigatórios", "Informe SKU e Nome.")
            return
        if not is_non_negative_float(cost) or not is_non_negative_float(price):
            messagebox.showwarning("Valores", "Custo e preço devem ser números >= 0")
            return
        if stock_min and not is_positive_integer(stock_min) and stock_min != "0":
            messagebox.showwarning("Estoque mínimo", "Estoque mínimo deve ser inteiro >= 0")
            return

        has_variants = bool(self.has_variants_var.get())
        attr_name = self.variant_attr_entry.get().strip() or None

        # validações de variação
        if has_variants:
            if not attr_name:
                messagebox.showwarning("Variações", "Informe o nome do atributo (ex: Cor).")
                return
            if not self.variant_rows:
                messagebox.showwarning("Variações", "Adicione ao menos 1 variação.")
                return

        # cria/atualiza produto
        if self.selected_product_id is None:
            product = Product(
                id=None,
                sku=sku,
                name=name,
                category_id=category_id,
                variant_attribute_name=attr_name if has_variants else None,
                brand=brand,
                cost_default=float(cost),
                price_default=float(price),
                stock_min=int(stock_min),
                is_active=is_active,
            )
            product_id = ProductRepository.add_product(self.conn, product)

            # cria variações
            created_variant_ids: list[int] = []
            if has_variants:
                for row in self.variant_rows:
                    v_value = row["value"].strip()
                    v_sku = (row["sku"].strip() or f"{sku}-{_slug(v_value)}")
                    v = ProductVariant(
                        id=None,
                        product_id=product_id,
                        variant_sku=v_sku,
                        variant_value=v_value,
                        is_default=False,
                        is_active=True,
                    )
                    vid = VariantRepository.add_variant(self.conn, v)
                    created_variant_ids.append(vid)

                # Estoque inicial via movimentos (data = hoje)
                from datetime import date as _date
                today = _date.today().isoformat()
                for row, vid in zip(self.variant_rows, created_variant_ids):
                    qty0 = int(row.get("stock_initial", 0) or 0)
                    if qty0 > 0:
                        StockMoveRepository.insert_stock_move(
                            self.conn,
                            {
                                "move_date": today,
                                "variant_id": vid,
                                "move_type": "IN",
                                "reason": "ESTOQUE_INICIAL",
                                "qty": qty0,
                                "unit_cost": float(cost),
                                "ref_type": "MANUAL",
                                "ref_id": None,
                                "notes": "",
                            },
                        )
            else:
                # variação Única
                v = ProductVariant(
                    id=None,
                    product_id=product_id,
                    variant_sku=sku,
                    variant_value="Única",
                    is_default=True,
                    is_active=True,
                )
                vid = VariantRepository.add_variant(self.conn, v)
                # sem estoque inicial aqui (movimente em Movimentações)

            messagebox.showinfo("Produto", "Produto cadastrado com sucesso!")
        else:
            # atualização: não muda SKU (campo travado)
            product_id = int(self.selected_product_id)
            product = Product(
                id=product_id,
                sku=sku,
                name=name,
                category_id=category_id,
                variant_attribute_name=attr_name if has_variants else None,
                brand=brand,
                cost_default=float(cost),
                price_default=float(price),
                stock_min=int(stock_min),
                is_active=is_active,
            )
            ProductRepository.update_product(self.conn, product)

            # estratégia segura (sem deletar histórico):
            # - desativa todas as variações NÃO default
            # - se usuário marcou variações: cria novas ativas
            # - se desmarcou: garante variação default ativa
            cur = self.conn.cursor()
            cur.execute("UPDATE product_variants SET is_active = 0 WHERE product_id = ? AND is_default = 0", (product_id,))
            self.conn.commit()

            if has_variants:
                # desativa default também (mantém por histórico)
                cur.execute("UPDATE product_variants SET is_active = 0 WHERE product_id = ? AND is_default = 1", (product_id,))
                self.conn.commit()
                for row in self.variant_rows:
                    v_value = row["value"].strip()
                    v_sku = (row["sku"].strip() or f"{sku}-{_slug(v_value)}")
                    v = ProductVariant(
                        id=None,
                        product_id=product_id,
                        variant_sku=v_sku,
                        variant_value=v_value,
                        is_default=False,
                        is_active=True,
                    )
                    VariantRepository.add_variant(self.conn, v)
            else:
                # garante default ativo
                # se existir, ativa; se não existir, cria
                cur.execute(
                    "SELECT id FROM product_variants WHERE product_id = ? AND is_default = 1",
                    (product_id,),
                )
                r = cur.fetchone()
                if r:
                    cur.execute("UPDATE product_variants SET is_active = 1, variant_sku = ? WHERE id = ?", (sku, r["id"]))
                    self.conn.commit()
                else:
                    VariantRepository.add_variant(
                        self.conn,
                        ProductVariant(
                            id=None,
                            product_id=product_id,
                            variant_sku=sku,
                            variant_value="Única",
                            is_default=True,
                            is_active=True,
                        ),
                    )

            messagebox.showinfo("Produto", "Produto atualizado!")

        # refresh
        self.load_products()
        self.clear_product_form()

    # ---------------- Categorias ----------------
    def _build_categories_view(self):
        form = ctk.CTkFrame(self.categories_view)
        form.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(form, text="Nome da categoria:").grid(row=0, column=0, sticky="w")
        self.cat_name_entry = ctk.CTkEntry(form, width=280)
        self.cat_name_entry.grid(row=0, column=1, padx=6, pady=6, sticky="w")

        self.cat_active_var = tk.IntVar(value=1)
        self.cat_active_check = ctk.CTkCheckBox(form, text="Ativo", variable=self.cat_active_var)
        self.cat_active_check.grid(row=0, column=2, padx=10, pady=6, sticky="w")

        btns = ctk.CTkFrame(self.categories_view)
        btns.pack(fill="x", padx=10)

        self.cat_save_btn = ctk.CTkButton(btns, text="Salvar", command=self.save_category, width=140)
        self.cat_save_btn.pack(side="left", padx=6, pady=6)

        self.cat_delete_btn = ctk.CTkButton(
            btns,
            text="Remover",
            command=self.delete_category,
            width=140,
            fg_color="#8a2b2b",
            hover_color="#a83a3a",
        )
        self.cat_delete_btn.pack(side="left", padx=6, pady=6)

        self.cat_clear_btn = ctk.CTkButton(
            btns,
            text="Limpar",
            command=self.clear_category_form,
            width=140,
            fg_color="#3a3a3a",
            hover_color="#4a4a4a",
        )
        self.cat_clear_btn.pack(side="left", padx=6, pady=6)

        self.cat_tree = ttk.Treeview(self.categories_view, columns=("name", "active"), show="headings")
        self.cat_tree.heading("name", text="Categoria")
        self.cat_tree.heading("active", text="Ativo")
        self.cat_tree.column("name", width=320, anchor="w")
        self.cat_tree.column("active", width=80, anchor="center")
        self.cat_tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.cat_tree.bind("<ButtonRelease-1>", self.on_tree_select_category)

    def clear_category_form(self):
        self.selected_category_id = None
        self.cat_name_entry.delete(0, tk.END)
        self.cat_active_var.set(1)
        self.cat_save_btn.configure(text="Salvar")

    def on_tree_select_category(self, event):
        sel = self.cat_tree.selection()
        if not sel:
            return
        cid = int(sel[0])
        values = self.cat_tree.item(sel[0], "values")
        self.selected_category_id = cid
        self.cat_name_entry.delete(0, tk.END)
        self.cat_name_entry.insert(0, values[0])
        self.cat_active_var.set(1 if values[1] == "Sim" else 0)
        self.cat_save_btn.configure(text="Atualizar")

    def save_category(self):
        name = self.cat_name_entry.get().strip()
        is_active = bool(self.cat_active_var.get())
        if not is_non_empty(name):
            messagebox.showwarning("Categoria", "Informe o nome da categoria.")
            return
        try:
            if self.selected_category_id is None:
                CategoryRepository.add_category(self.conn, name=name, is_active=is_active)
            else:
                CategoryRepository.update_category(self.conn, self.selected_category_id, name=name, is_active=is_active)
        except Exception as e:
            messagebox.showerror("Erro", str(e))
            return

        self.load_categories()
        self.refresh_category_dropdown()
        self.clear_category_form()
        messagebox.showinfo("Categoria", "Categoria salva!")

    def delete_category(self):
        if self.selected_category_id is None:
            messagebox.showwarning("Categoria", "Selecione uma categoria.")
            return
        cid = int(self.selected_category_id)
        name = self.cat_name_entry.get().strip()
        if not messagebox.askyesno("Confirmar", f"Remover a categoria '{name}'?"):
            return
        # bloqueio simples: se tiver produto usando, não remove
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(1) AS n FROM products WHERE category_id = ?", (cid,))
        n = int(cur.fetchone()["n"])
        if n > 0:
            messagebox.showwarning("Categoria", "Não é possível remover: há produtos usando essa categoria.")
            return
        try:
            CategoryRepository.delete_category(self.conn, cid)
        except Exception as e:
            messagebox.showerror("Erro", str(e))
            return
        self.load_categories()
        self.refresh_category_dropdown()
        self.clear_category_form()
        messagebox.showinfo("Categoria", "Categoria removida.")
