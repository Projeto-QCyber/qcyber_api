# -*- coding: utf-8 -*-
import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv


load_dotenv()

class Settings(BaseSettings):
    """
    Classe para gerenciar as configurações da aplicação a partir de variáveis de ambiente.
    """
    # Configurações do Banco de Dados
    MYSQL_HOST: str
    MYSQL_PORT: int
    MYSQL_ROOT_PASSWORD: str
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DATABASE: str

    # Configurações de Segurança (JWT)
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    # URL base do frontend para montar links em e-mails
    FRONTEND_BASE_URL: str = str(os.getenv("FRONTEND_BASE_URL"))

    # Porta NGINX
    NGINX_PORT: str = str(os.getenv("NGINX_PORT"))

    class Config:
        env_file = ".env"  # Especifica o arquivo .env a ser lido
        case_sensitive = True

# Instância única das configurações para ser usada em toda a aplicação
settings = Settings()
