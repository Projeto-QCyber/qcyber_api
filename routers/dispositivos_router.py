# -*- coding: utf-8 -*-
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
import pymysql

import schemas
import security
from database import get_cursor

router = APIRouter(
    prefix="/dispositivos",
    # A dependência aqui garante que todas as rotas neste arquivo exigirão um token válido
    dependencies=[Depends(security.oauth2_scheme)] 
)

@router.get("/", response_model=List[schemas.Dispositivo])
def read_dispositivos(cursor: pymysql.cursors.DictCursor = Depends(get_cursor)):
    """Busca e retorna a lista de todos os dispositivos cadastrados."""
    try:
        cursor.execute("SELECT id, nome, host, localizacao, status, data_cadastro FROM dispositivos ORDER BY nome ASC")
        dispositivos = cursor.fetchall()
        return dispositivos
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar dispositivos: {e}")

@router.post("/", response_model=schemas.Dispositivo, status_code=status.HTTP_201_CREATED)
def create_dispositivo(
    dispositivo: schemas.DispositivoCreate, 
    cursor: pymysql.cursors.DictCursor = Depends(get_cursor)
):
    """Cadastra um novo dispositivo no banco de dados."""
    try:
        # Verifica se o host já existe
        cursor.execute("SELECT id FROM dispositivos WHERE host = %s", (dispositivo.host,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este host já está cadastrado."
            )

        sql = "INSERT INTO dispositivos (nome, host, localizacao) VALUES (%s, %s, %s)"
        cursor.execute(sql, (dispositivo.nome, dispositivo.host, dispositivo.localizacao))
        new_id = cursor.lastrowid

        # Busca o registro recém-criado para retornar o objeto completo
        cursor.execute("SELECT id, nome, host, localizacao, status, data_cadastro FROM dispositivos WHERE id = %s", (new_id,))
        new_dispositivo = cursor.fetchone()

        cursor.connection.commit() # Salva as alterações no banco

        return new_dispositivo

    except pymysql.MySQLError as e:
        cursor.connection.rollback()
        raise HTTPException(status_code=500, detail=f"Erro de banco de dados: {e}")
    except Exception as e:
        cursor.connection.rollback()
        raise HTTPException(status_code=500, detail=f"Erro interno: {e}")
