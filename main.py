# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importa os roteadores dos diferentes módulos
from routers import login_router, dispositivos_router, usuarios_router, dashboard_router

# Cria a instância principal da aplicação FastAPI
app = FastAPI(
    title="qCyber Security API",
    description="API para monitoramento de segurança e análise de detecções.",
    version="1.0.0"
)

# Configuração do CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, restrinja para o domínio do seu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui os roteadores na aplicação principal
app.include_router(login_router.router, tags=["Autenticação"])
app.include_router(dispositivos_router.router, tags=["Dispositivos"])
app.include_router(usuarios_router.router, tags=["Usuários"])
app.include_router(dashboard_router.router, tags=["Dashboard"])


@app.get("/", tags=["Root"])
def read_root():
    """Endpoint inicial para verificar se a API está online."""
    return {"message": "Bem-vindo à qCyber Security API!"}

# Para executar a aplicação:
# uvicorn main:app --reload --port 8000
