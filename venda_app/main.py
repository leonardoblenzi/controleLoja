"""
Ponto de entrada da aplicação.

Este script simplesmente importa e executa a classe principal da UI
definida em `ui.dashboard`. Para iniciar a aplicação execute:

```
python3 main.py
```
"""
from .ui.dashboard import run_app

if __name__ == "__main__":
    run_app()