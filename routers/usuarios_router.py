# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
import pymysql

import schemas
import security
from services import email_service
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
    Cria um novo usuário (inativo) e envia um e-mail de verificação.
    """
    cursor.execute("SELECT id FROM usuarios WHERE email = %s", (user.email,))
    if cursor.fetchone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O e-mail fornecido já está cadastrado.",
        )

    hashed_password = security.get_password_hash(user.senha)
    verification_code = security.generate_secure_code()
    hashed_code = security.get_password_hash(verification_code)
    expiration_time = datetime.utcnow() + timedelta(minutes=5)

    try:
        sql = """
              INSERT INTO usuarios (nome, email, senha_hash, codigo_verificacao, codigo_verificacao_expiracao)
              VALUES (%s, %s, %s, %s, %s) 
              """
        cursor.execute(sql, (user.nome, user.email, hashed_password, hashed_code, expiration_time))

        # Envia o e-mail de verificação
        email_service.send_verification_email(
            to_email=user.email,
            code=verification_code,
            subject="Verifique sua conta qCyber",
            cursor=cursor
        )

        cursor.connection.commit()
        return schemas.UserBase(nome=user.nome, email=user.email)

    except Exception as e:
        cursor.connection.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Ocorreu um erro inesperado: {e}"
        )


@router.post("/verify-email", status_code=status.HTTP_200_OK)
def verify_user_email(
        verification_data: schemas.EmailVerification,  # Você precisará criar este schema
        cursor: pymysql.cursors.DictCursor = Depends(get_cursor)
):
    """Verifica o código de e-mail e ativa a conta do usuário."""
    cursor.execute(
        "SELECT * FROM usuarios WHERE email = %s", (verification_data.email,)
    )
    user = cursor.fetchone()

    if not user or not user['codigo_verificacao'] or not security.verify_password(verification_data.code,
                                                                                  user['codigo_verificacao']):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código inválido.")

    if datetime.utcnow() > user['codigo_verificacao_expiracao']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código expirado.")

    # Ativa o usuário e limpa os campos de verificação
    sql = """
          UPDATE usuarios 
          SET email_verificado             = TRUE, 
              ativo                        = TRUE, 
              codigo_verificacao           = NULL, 
              codigo_verificacao_expiracao = NULL, 
              tentativas_verificacao       = 0
          WHERE email = %s 
          """
    cursor.execute(sql, (verification_data.email,))
    cursor.connection.commit()

    return {"message": "E-mail verificado com sucesso! Você já pode fazer login."}