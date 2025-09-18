# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
import pymysql

import schemas
import security
from services import email_service
from database import get_cursor

from schemas import UserSummary

router = APIRouter(
    prefix="/qcyberapi/usuarios",
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


@router.get("/me", response_model=UserSummary)
def read_users_me(current_user: dict = Depends(security.get_current_user)):
    """Retorna os dados do usuário atualmente autenticado."""
    # O `get_current_user` já retorna um dicionário com os dados do usuário do banco
    # Apenas retornamos esse dicionário, e o FastAPI/Pydantic cuidará da validação
    return current_user


@router.post("/request-password-reset", status_code=status.HTTP_200_OK)
def request_password_reset(
        request_data: schemas.PasswordResetRequest,
        cursor: pymysql.cursors.DictCursor = Depends(get_cursor)
):
    """
    (Usuário) Solicita um link para resetar a senha.
    """
    cursor.execute("SELECT id, nome, email FROM usuarios WHERE email = %s AND ativo = TRUE", (request_data.email,))
    user = cursor.fetchone()

    # Mesmo que o usuário não exista, retornamos sucesso para evitar enumeração de e-mails
    if user:
        token = security.generate_secure_code(length=32)
        hashed_token = security.get_password_hash(token)
        expiration = datetime.utcnow() + timedelta(hours=1)  # Token válido por 1 hora

        cursor.execute(
            "UPDATE usuarios SET reset_senha_token=%s, reset_senha_expiracao=%s WHERE id=%s",
            (hashed_token, expiration, user['id'])
        )

        # Envie um e-mail com o link para resetar a senha
        reset_link = f"http://sua-app-web.com/reset-password?token={token}"  # Adapte este link
        subject = "Redefinição de Senha - Plataforma qCyber"
        email_body = f"Olá {user['nome']},<br><br>Clique no link a seguir para redefinir sua senha: <a href='{reset_link}'>{reset_link}</a>"
        email_service.send_email_html(user['email'], subject, email_body, cursor)

        cursor.connection.commit()

    return {"message": "Se o e-mail estiver cadastrado, um link de recuperação será enviado."}


@router.post("/perform-password-reset", status_code=status.HTTP_200_OK)
def perform_password_reset(
        reset_data: schemas.PasswordResetPerform,
        cursor: pymysql.cursors.DictCursor = Depends(get_cursor)
):
    """
    (Usuário) Efetiva a troca de senha usando o token.
    """
    if not reset_data.token or not reset_data.nova_senha:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token e nova senha são obrigatórios.")

    # Busca todos os usuários para verificar o hash do token (não é o ideal para performance, mas funciona)
    cursor.execute(
        "SELECT id, reset_senha_token, reset_senha_expiracao FROM usuarios WHERE reset_senha_token IS NOT NULL")
    users_with_token = cursor.fetchall()

    target_user = None
    for user in users_with_token:
        if security.verify_password(reset_data.token, user['reset_senha_token']):
            target_user = user
            break

    if not target_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token inválido.")

    if datetime.utcnow() > target_user['reset_senha_expiracao']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expirado.")

    # Tudo certo, atualiza a senha
    new_hashed_password = security.get_password_hash(reset_data.nova_senha)
    cursor.execute(
        "UPDATE usuarios SET senha_hash = %s, reset_senha_token = NULL, reset_senha_expiracao = NULL WHERE id = %s",
        (new_hashed_password, target_user['id'])
    )
    cursor.connection.commit()

    return {"message": "Senha atualizada com sucesso."}
