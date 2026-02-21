-- schema.sql (Controle de Vendas e Estoque)
-- IMPORTANTE: este arquivo deve conter APENAS SQL.

PRAGMA foreign_keys = ON;

-- =====================
-- CATEGORIAS
-- =====================
CREATE TABLE IF NOT EXISTS categories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_categories_name ON categories(name);

-- =====================
-- PRODUTOS
-- =====================
CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sku TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  category_id INTEGER NOT NULL,
  variant_attribute_name TEXT,                 -- ex: "Cor", "Modelo" (opcional)
  brand TEXT,
  cost_default REAL NOT NULL DEFAULT 0,
  price_default REAL NOT NULL DEFAULT 0,
  stock_min INTEGER NOT NULL DEFAULT 0,
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_products_category_id ON products(category_id);

-- =====================
-- VARIAÇÕES
-- Regra: TODO produto tem ao menos 1 variação.
-- Se não houver variações reais, criamos a variação "Única".
-- =====================
CREATE TABLE IF NOT EXISTS product_variants (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  product_id INTEGER NOT NULL,
  variant_sku TEXT NOT NULL UNIQUE,            -- SKU vendável
  variant_value TEXT NOT NULL,                 -- ex: "Preto", "Rosa", "Única"
  is_default INTEGER NOT NULL DEFAULT 0,        -- 1 para "Única"
  cost_override REAL,                          -- opcional
  price_override REAL,                         -- opcional
  is_active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_variants_product_id ON product_variants(product_id);
CREATE INDEX IF NOT EXISTS idx_variants_sku ON product_variants(variant_sku);

-- =====================
-- VENDAS
-- =====================
CREATE TABLE IF NOT EXISTS sales (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sale_date TEXT NOT NULL,
  channel TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'A_ENVIAR',
  order_ref TEXT,
  customer_name TEXT,
  notes TEXT,
  packaging_enabled INTEGER NOT NULL DEFAULT 0,
  packaging_volumes INTEGER NOT NULL DEFAULT 1,
  packaging_box_variant_id INTEGER,
  packaging_env_variant_id INTEGER,
  total_gross REAL NOT NULL DEFAULT 0,
  total_fees REAL NOT NULL DEFAULT 0,
  total_discount REAL NOT NULL DEFAULT 0,
  total_net REAL NOT NULL DEFAULT 0,
  total_cost REAL NOT NULL DEFAULT 0,
  total_profit REAL NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (packaging_box_variant_id) REFERENCES product_variants(id),
  FOREIGN KEY (packaging_env_variant_id) REFERENCES product_variants(id)
);

-- Itens de cada venda (por variação)
CREATE TABLE IF NOT EXISTS sale_items (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sale_id INTEGER NOT NULL,
  variant_id INTEGER NOT NULL,
  qty INTEGER NOT NULL CHECK(qty > 0),
  unit_price REAL NOT NULL DEFAULT 0,
  unit_cost REAL NOT NULL DEFAULT 0,
  fees REAL NOT NULL DEFAULT 0,
  discount REAL NOT NULL DEFAULT 0,
  net REAL NOT NULL DEFAULT 0,
  profit REAL NOT NULL DEFAULT 0,
  FOREIGN KEY (sale_id) REFERENCES sales(id) ON DELETE CASCADE,
  FOREIGN KEY (variant_id) REFERENCES product_variants(id)
);

CREATE INDEX IF NOT EXISTS idx_sale_items_sale_id ON sale_items(sale_id);
CREATE INDEX IF NOT EXISTS idx_sale_items_variant_id ON sale_items(variant_id);

-- =====================
-- MOVIMENTAÇÕES DE ESTOQUE (por variação)
-- =====================
CREATE TABLE IF NOT EXISTS stock_moves (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  move_date TEXT NOT NULL,
  variant_id INTEGER NOT NULL,
  move_type TEXT NOT NULL CHECK(move_type IN ('IN','OUT','ADJ')),
  reason TEXT NOT NULL,
  qty INTEGER NOT NULL,
  unit_cost REAL NOT NULL DEFAULT 0,
  ref_type TEXT,
  ref_id INTEGER,
  notes TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  FOREIGN KEY (variant_id) REFERENCES product_variants(id)
);

CREATE INDEX IF NOT EXISTS idx_stock_moves_variant_id ON stock_moves(variant_id);
CREATE INDEX IF NOT EXISTS idx_stock_moves_date ON stock_moves(move_date);

-- =====================
-- GASTOS
-- =====================
CREATE TABLE IF NOT EXISTS expenses (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  exp_date TEXT NOT NULL,
  category TEXT NOT NULL,
  description TEXT NOT NULL,
  amount REAL NOT NULL CHECK(amount >= 0),
  payment_method TEXT,
  notes TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(exp_date);
