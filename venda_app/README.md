# Controle de Vendas e Estoque

Este projeto é um esqueleto de aplicação desktop escrita em Python para
gerenciar vendas, entradas e saídas de estoque, cadastro de produtos e
gastos financeiros. Ele foi pensado para servir como base para
construções mais completas e segue as recomendações descritas pelo
usuário no enunciado.

Visão geral do fluxo

Produtos → sempre geram pelo menos 1 variação (Única).

Estoque → só existe via stock_moves (IN/OUT/ADJ) por variant_id.

Venda → cria sales + sale_items (por variant_id) + baixa estoque (stock_moves OUT).

Embalagem (caixa/envelope) → selecionada manualmente na venda (autocomplete filtrado em MATERIAIS) + baixa automática (stock_moves OUT, qty = volumes).

Cancelar venda → muda status pra CANCELADO e reverte todos os movimentos daquela venda.

main.py

Responsabilidade: iniciar o app.

Chama: ui.dashboard.run_app()

db/database.py
Funções

get_connection()

abre SQLite

define row_factory = sqlite3.Row

ativa PRAGMA foreign_keys = ON

init_db()

lê schema.sql

executa executescript() para criar tabelas/índices

db/schema.sql
Tabelas (modelo atualizado)

categories

products (com category_id FK + opcional variant_attribute_name)

product_variants (sempre existe; produto sem variação tem “Única”)

sales (com status: A_ENVIAR / ENVIADO / CONCLUIDO / CANCELADO)

sale_items (por variant_id)

stock_moves (por variant_id)

expenses

Estoque sempre vem da soma de movimentos por variant_id.

db/repositories.py
Models (dataclasses)

Category

Product

Variant (se você tiver criado dataclass; se não, retorna Row)

Repositórios
CategoryRepository

add_category(name, is_active)

update_category(id, name, is_active)

delete_category(id) (idealmente bloqueia se tiver produto usando)

list_categories(only_active=False/True)

get_category_by_name(name) (útil)

ProductRepository

add_product(Product) → exige category_id

update_product(Product)

delete_product(product_id)

get_all_products() → JOIN em categories (retorna Row com category_name)

get_product_by_sku(sku)

get_product_by_id(id)

VariantRepository

search_variants(q, limit=12, category_name=None)

busca por SKU / nome produto / valor variação

se category_name vier, filtra por categoria case-insensitive (LOWER(c.name)=LOWER(?))

get_variant_by_sku(variant_sku)

valida SKU digitado manualmente

get_variant_id_by_sku(variant_sku) (atalho)

list_variants_by_product(product_id) (se você implementou pra tela de produto)

add_variant(product_id, variant_value, variant_sku, ...)

delete_variant(variant_id)

ensure_single_variant(product)

cria “Única” se não tiver variações

SaleRepository

insert_sale(sale_data) → inclui status default A_ENVIAR

insert_sale_item(item_data) → por variant_id

(opcional) update_sale_status(sale_id, status)

StockMoveRepository

insert_stock_move(move_data) → por variant_id

list_moves(...) (se você tem)

delete_moves_by_ref(ref_type, ref_id) (se você usa na reversão)

ExpenseRepository

add_expense(expense_data)

list_expenses(...) (se tiver)

services/inventory_service.py
Funções (estoque por variante)

get_stock_levels_by_variant(conn)

retorna dict variant_id -> qty

(opcional) get_stock_levels_by_product(conn)

soma variantes do mesmo produto

(opcional) get_low_stock(conn)

compara com mínimo e devolve alertas (pra dashboard)

services/sales_service.py
Funções principais

create_sale(...)

cria registro em sales com status A_ENVIAR

cria itens em sale_items por variant_id

gera stock_moves OUT para cada item vendido

se “Baixar embalagem” estiver marcado:

valida box_variant_sku e env_variant_sku

gera stock_moves OUT pra cada um com qty = volumes

cancel_sale(sale_id)

seta status = CANCELADO

cria movimentos inversos (estoque volta):

para cada stock_move da venda, insere outro com qty inverso (ou move_type invertido)

evita cancelar duas vezes (idempotente)

update_sale_status(sale_id, status)

muda pra ENVIADO / CONCLUIDO sem mexer no estoque (porque já baixou na criação)

Ponto crucial: cancelar reverte, enviado/concluído só muda status.

services/reports_service.py

get_financial_summary(date_from, date_to)

soma vendas (revenue/cost/profit)

soma gastos (expenses)

calcula resultado

ui/autocomplete.py
AutocompleteEntry

Entry com dropdown de sugestões

aceita:

provider(query) → retorna lista de Rows

on_select(item) (opcional)

atalhos:

↓ foca lista

Enter seleciona

Esc fecha

ui/dashboard.py
O que mostra

Cards com ícones e KPIs (mês atual):

Receita

Lucro

Gastos

Abaixo do mínimo

Navegação lateral:

Dashboard / Produtos / Vendas / Estoque / Movimentações / Financeiro / Gastos

De onde vêm os KPIs

reports_service.get_financial_summary

inventory_service.get_low_stock ou query equivalente

ui/products.py
Sub-nav interno

Produtos | Categorias (CTkSegmentedButton)

Produtos

Cadastro de produto com:

categoria (dropdown carregado de categories)

atributo de variação (ex: “Cor”, “Dimensão”) opcional

seção de variações (opcional por produto)

Se produto não tiver variação marcada:

cria automaticamente variação Única

Se tiver variações:

adiciona valores (ex: “16x11x5”) e gera SKU automaticamente (editável)

opção de estoque inicial → cria stock_moves IN

Categorias

CRUD completo

ui/sales.py
Venda

Form de venda + grid de itens

SKU de item com autocomplete (VariantRepository.search_variants sem filtro)

Bloco Embalagem

checkbox “Baixar embalagem”

volumes

Caixa (autocomplete filtrado category_name="MATERIAIS")

Envelope (autocomplete filtrado category_name="MATERIAIS")

Status

Campo/Dropdown status:

A_ENVIAR / ENVIADO / CONCLUIDO / CANCELADO

Ações:

Salvar venda (baixa estoque)

Cancelar venda (reverte movimentos e marca CANCELADO)

ui/moves.py

Entrada/Saída/Ajuste por variant_sku com autocomplete

Insere stock_moves manualmente (ref_type="MANUAL")

Lista últimos movimentos

ui/stock.py

Mostra estoque por variação:

variant_sku / produto / atributo / valor / qty

filtros:

buscar SKU

(opcional) somente MATERIAIS

alerta de mínimo (se implementado)

ui/expenses.py

CRUD simples de gastos

ui/finance.py

resumo por período

mostra receita / custo / lucro / gastos / resultado

utils/validators.py

validações de string, inteiro, float etc.

## Requisitos

* **Python 3.11** ou superior.
* **CustomTkinter** para a interface gráfica (`pip install customtkinter`).
* **Pandas** e **openpyxl** se desejar importar/exportar planilhas Excel.

O banco de dados utiliza **SQLite** e é criado automaticamente na primeira
execução. As tabelas estão definidas em `db/schema.sql`.

## Utilização

Para iniciar a aplicação, execute o arquivo `main.py` com Python:

```bash
python3 main.py
```

Ao executar pela primeira vez, o banco de dados será criado no caminho
`venda_app/app.db`. A interface inicial apresenta um menu com opções
básicas. Apenas a tela de produtos está implementada como exemplo; as
demais telas são esboços e podem ser completadas conforme a sua
necessidade.

## Extensões Futuras

O projeto foi estruturado para permitir evolução fácil. Você pode:

* Implementar as telas restantes (`sales.py`, `stock.py`, `moves.py`,
  `finance.py`, `expenses.py`) seguindo o padrão de componentes.
* Adicionar funcionalidades nos serviços e repositórios para cálculos
  financeiros, relatórios e integrações com marketplace.
* Customizar a interface com temas e animações do CustomTkinter.

---

### Referências

* A combinação de **Python**, **SQLite** e **CustomTkinter** foi escolhida
  por ser leve, sem necessidade de servidor e adequada para aplicativos
  desktop. O SQLite é um banco de dados embutido que funciona sem
  configuração adicional【514122692445519†L54-L70】【514122692445519†L81-L83】. O
  CustomTkinter fornece widgets modernos baseados em Tkinter e é
  recomendado para interfaces elegantes【267799201876033†L18-L28】.
