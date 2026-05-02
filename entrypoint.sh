#!/usr/bin/env bash


# Espera o MySQL ficar pronto
/app/wait-for-it.sh mysql:3306 --timeout=35 --strict -- echo "MySQL está pronto! Ouvindo na porta interna 3306"

# Executa bootstrap do banco antes de iniciar a API (única vez no boot)
python - <<'PY'
import sys
print('[ENTRYPOINT] Executando bootstrap inicial do banco...')
try:
    from arquitetura_db.create_qcyber_db import ensure_bootstrap
    ok = ensure_bootstrap()
    print(f'[ENTRYPOINT] Bootstrap concluído: {ok}')
except Exception as e:
    print(f'[ENTRYPOINT] Falha no bootstrap: {e}')
PY


# Substitua 'main:app' pelo caminho real do seu arquivo e da sua instância Fastapi.
python -m uvicorn main:app --host 0.0.0.0 --port $MAIN_API_PORT
