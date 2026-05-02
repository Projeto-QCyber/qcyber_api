# -*- coding: utf-8 -*-
import os
from config import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importa os roteadores dos diferentes módulos
from routers import (login_router,
                     dispositivos_router,
                     usuarios_router,
                     dashboard_router,
                     history_router,
                     report_router,
                     admin_router)

# Cria a instância principal da aplicação FastAPI
app = FastAPI(
    title="qCyber Security API",
    description="API para monitoramento de segurança e análise de detecções.",
    version="1.0.0",
    docs_url="/qcyber/api/docs" if os.environ.get("API_ENV")=="dev" else None,
    redoc_url="/qcyber/api/redoc" if os.environ.get("API_ENV")=="dev" else None,
    openapi_url="/qcyber/api/openapi.json" if os.environ.get("API_ENV")=="dev" else None,
    swagger_ui_parameters={"docExpansion": None}  # fecha as rotas, por padrão
)

# Configuração do CORS (Cross-Origin Resource Sharing)
dev_origins = [
    f"http://localhost:{settings.NGINX_PORT}",  # nginx
    f"http://127.0.0.1:{settings.NGINX_PORT}",  # nginx
] if os.environ.get("API_ENV")=="dev" else []
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://192.168.1.152:{settings.NGINX_PORT}",  # nginx
        settings.FRONTEND_BASE_URL.replace("/qcyber/", ""),  # removendo a base url do final
    ] + dev_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui os roteadores na aplicação principal
app.include_router(login_router.router, tags=["Autenticação"])
app.include_router(dispositivos_router.router, tags=["Dispositivos"])
app.include_router(usuarios_router.router, tags=["Usuários"])
app.include_router(dashboard_router.router, tags=["Dashboard"])

app.include_router(history_router.router, tags=["Histórico"])
app.include_router(report_router.router, tags=["Relatórios"])
app.include_router(admin_router.router,tags=["Administração"])


@app.get("/", tags=["Root"])
def read_root():
    """Endpoint inicial para verificar se a API está online."""
    return {"message": "Bem-vindo à qCyber Security API!"}

# Para executar a aplicação:
# uvicorn main:app --reload --port 8000
