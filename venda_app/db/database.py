"""
Módulo de conexão e inicialização do banco de dados.

Este módulo fornece funções para estabelecer conexão com o banco
SQLite utilizado pela aplicação, bem como inicializar o esquema de
dados a partir do arquivo `schema.sql`. O banco de dados é
armazenado no mesmo diretório do pacote `db` e é criado
automaticamente caso ainda não exista.
"""

import sqlite3
from pathlib import Path
from typing import Optional


# Caminho do arquivo do banco de dados. Ele será criado no mesmo
# diretório deste módulo, com o nome `app.db`.
DB_PATH = Path(__file__).resolve().parent / "app.db"


def get_connection() -> sqlite3.Connection:
    """Obtém uma conexão com o banco de dados SQLite.

    A função define a `row_factory` para retornar linhas como objetos
    do tipo `sqlite3.Row`, permitindo acesso às colunas por nome.

    Returns:
        sqlite3.Connection: Conexão aberta com o banco de dados.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")

    return conn


def init_db(schema_path: Optional[Path] = None) -> None:
    """Inicializa o banco de dados executando o script de esquema.

    Esta função cria o banco de dados se ele não existir e executa
    todas as instruções SQL presentes em `schema.sql` para criar as
    tabelas necessárias. O caminho do arquivo de esquema pode ser
    passado explicitamente; caso contrário, é assumido que o arquivo
    `schema.sql` está no mesmo diretório deste módulo.

    Args:
        schema_path (Optional[Path]): Caminho alternativo para o
            arquivo de definição do esquema.
    """
    # Determina o caminho do arquivo de esquema
    if schema_path is None:
        schema_path = Path(__file__).resolve().parent / "schema.sql"

    # Lê o conteúdo do arquivo de esquema
    with open(schema_path, "r", encoding="utf-8") as f:
        script = f.read()

    conn = get_connection()
    try:
        conn.executescript(script)
        conn.commit()
    finally:
        conn.close()


__all__ = ["get_connection", "init_db", "DB_PATH"]