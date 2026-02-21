# Controle de Vendas e Estoque

Este projeto é um esqueleto de aplicação desktop escrita em Python para
gerenciar vendas, entradas e saídas de estoque, cadastro de produtos e
gastos financeiros. Ele foi pensado para servir como base para
construções mais completas e segue as recomendações descritas pelo
usuário no enunciado.

venda_app/
├── main.py                     # Ponto de entrada da aplicação
├── db/
│   ├── __init__.py
│   ├── database.py             # Conexão SQLite + init_db (PRAGMA foreign_keys=ON)
│   ├── schema.sql              # Tabelas: categories, products, product_variants, sales, sale_items, stock_moves, expenses
│   └── repositories.py         # Repos: CategoryRepository, ProductRepository, VariantRepository, SaleRepository, StockMoveRepository, ExpenseRepository
├── services/
│   ├── __init__.py
│   ├── inventory_service.py    # Estoque calculado por variant_id (movimentos)
│   ├── sales_service.py        # Salva venda + itens por variant_id + gera stock_moves OUT
│   └── reports_service.py      # Resumos financeiros (placeholder/ok)
├── ui/
│   ├── __init__.py
│   ├── dashboard.py            # Dashboard com KPIs + navegação
│   ├── products.py             # Produtos + Categorias (sub-nav) + Variações (opcional) + SKU variação auto
│   ├── sales.py                # Vendas usando variant_sku (com autocomplete)
│   ├── moves.py                # Movimentações usando variant_sku (com autocomplete)
│   ├── stock.py                # Estoque por variação (e opcional agrupado por produto)
│   ├── finance.py              # Financeiro (gastos x lucro)
│   ├── expenses.py             # Lançamento e listagem de gastos
│   └── autocomplete.py         # Componente AutocompleteEntry (dropdown de sugestões)
└── utils/
    ├── __init__.py
    ├── logger.py               # Logging
    └── validators.py           # Validações

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
