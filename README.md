# Diag_360
Diagnostiquer la résilience territoriale pour mieux agir sur du long terme pour les collectivités

## Utilisation

Le projet utilise [uv](https://docs.astral.sh/uv/) pour gérer l'environnement et [ruff](https://docs.astral.sh/ruff/) pour le lint et le formatage.

```bash
uv sync                       # crée .venv, installe tout, génère uv.lock
uv run scr/i131_asso.py       # lance un script dans cet environnement
uv run ruff check . && uv run ruff format .
```
