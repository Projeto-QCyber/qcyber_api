# -*- coding: utf-8 -*-
import pymysql
from config import settings
from fastapi import HTTPException


def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    try:
        connection = pymysql.connect(
            host=settings.MYSQL_HOST,
            port=settings.MYSQL_PORT,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            database=settings.MYSQL_DATABASE,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None

def get_cursor():
    """Dependência FastAPI para obter um cursor de banco de dados."""
    connection = get_db_connection()
    if connection is None:
        raise HTTPException(
            status_code=503, # Service Unavailable
            detail="Não foi possível conectar ao banco de dados."
        )
    try:
        yield connection.cursor()
    finally:
        connection.close()
