# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv
from pydantic import BaseSettings

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

class Settings(BaseSettings):
    """
    Classe para gerenciar as configurações da aplicação.
    O Pydantic lê automaticamente as variáveis de ambiente.
    """
    # Configurações do Banco de Dados
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "root")
    MYSQL_DB: str = os.getenv("MYSQL_DB", "qcyberDB")

    # Configurações de Segurança (JWT)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default_secret")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

    class Config:
        case_sensitive = True

# Instância única das configurações para ser usada em toda a aplicação
settings = Settings()
