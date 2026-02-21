"""
Configuração básica de logging para a aplicação.

Este módulo centraliza a criação de um logger que pode ser importado
por outros módulos da aplicação. Os logs são enviados tanto para o
console quanto para um arquivo `app.log` no diretório base.
"""

import logging
from pathlib import Path


LOG_FILE = Path(__file__).resolve().parent.parent / "app.log"

# Cria o logger
logger = logging.getLogger("venda_app")
logger.setLevel(logging.DEBUG)

# Formato de log
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

# Handler de console
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# Handler de arquivo
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


__all__ = ["logger"]