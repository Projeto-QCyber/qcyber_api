# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, HTTPException, status
import pymysql

import schemas
import security
from database import get_cursor

router = APIRouter(
    prefix="/usuarios",
    tags=["Usuários"]
)

@router.post("/", response_model=schemas.UserBase, status_code=status.HTTP_201_CREATED)
def create_user(
    user: schemas.UserCreate,
    cursor: pymysql.cursors.DictCursor = Depends(get_cursor)
):
    """
    Cria um novo usuário no sistema.
    """
    # Verifica se o e-mail já existe
    cursor.execute("SELECT id FROM usuarios WHERE email = %s", (user.email,))
    if cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O e-mail fornecido já está cadastrado.",
        )

    # Gera o hash da senha antes de salvar
    hashed_password = security.get_password_hash(user.senha)

    try:
        sql = "INSERT INTO usuarios (nome, email, senha_hash) VALUES (%s, %s, %s)"
        cursor.execute(sql, (user.nome, user.email, hashed_password))
        cursor.connection.commit()

        # Retorna os dados do usuário criado (sem a senha)
        return schemas.UserBase(nome=user.nome, email=user.email)

    except pymysql.MySQLError as e:
        cursor.connection.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro de banco de dados ao criar usuário: {e}"
        )
    except Exception as e:
        cursor.connection.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocorreu um erro inesperado: {e}"
        )