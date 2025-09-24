# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
import pymysql

import schemas
import security
from services import email_service
from config import settings
from database import get_cursor

router = APIRouter(
    prefix="/qcyberapi/login",
    tags=["Autenticação"]
)


@router.post("/token")
def login_for_access_token(
        response: Response,
        form_data: OAuth2PasswordRequestForm = Depends(),
        cursor: pymysql.cursors.DictCursor = Depends(get_cursor)
):
    """
    Endpoint de login. Se o 2FA estiver ativo, envia código por e-mail e retorna token temporário.
    """
    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (form_data.username,))
    user = cursor.fetchone()

    if not user or not security.verify_password(form_data.password, user["senha_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Email ou senha incorretos")

    if not user.get('email_verificado', False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="E-mail não verificado. Por favor, ative sua conta.")

    if not user.get('ativo', True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário inativo.")

    if user.get('dois_fatores_ativo', False):
        # Gera e envia código 2FA
        code = security.generate_secure_code()
        hashed_code = security.get_password_hash(code)
        expiration = datetime.now(timezone.utc) + timedelta(minutes=5)

        sql = "UPDATE usuarios SET codigo_verificacao=%s, codigo_verificacao_expiracao=%s, tentativas_verificacao=0 WHERE id=%s"
        cursor.execute(sql, (hashed_code, expiration, user['id']))

        email_service.send_verification_email(user['email'], code, "Seu código de login qCyber", cursor)
        cursor.connection.commit()

        # Retorna desafio com token temporário
        temp_token = security.create_access_token(
            data={"sub": user["email"], "scope": "2fa_login"},
            expires_delta=timedelta(minutes=5)
        )
        response.status_code = status.HTTP_202_ACCEPTED
        return {"message": "Autenticação de dois fatores necessária.", "temp_token": temp_token}

    # Login normal
    access_token = security.create_access_token(data={"sub": user["email"]})
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/token/2fa", response_model=schemas.Token)
def verify_2fa_login(
        verification_data: schemas.TwoFactorVerify,
        cursor: pymysql.cursors.DictCursor = Depends(get_cursor)
):
    """Verifica o código 2FA do e-mail e retorna o token de acesso final."""
    token_data = security.decode_access_token(
        token=verification_data.temp_token,
        credentials_exception=HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                            detail="Token temporário inválido")
    )

    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (token_data["sub"],))
    user = cursor.fetchone()

    # Lógica de tentativas
    if user['tentativas_verificacao'] >= 3:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Muitas tentativas inválidas. Por favor, tente fazer o login novamente.")

    if not user or not user['codigo_verificacao'] or not security.verify_password(verification_data.code,
                                                                                  user['codigo_verificacao']):
        cursor.execute("UPDATE usuarios SET tentativas_verificacao = tentativas_verificacao + 1 WHERE id=%s",
                       (user['id'],))
        cursor.connection.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Código 2FA inválido.")

    if datetime.now(timezone.utc) > user['codigo_verificacao_expiracao']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código 2FA expirado.")

    # Sucesso: Limpa os campos e gera o token final
    sql = "UPDATE usuarios SET codigo_verificacao=NULL, codigo_verificacao_expiracao=NULL, tentativas_verificacao=0 WHERE id=%s"
    cursor.execute(sql, (user['id'],))
    cursor.connection.commit()

    access_token = security.create_access_token(data={"sub": user["email"]})
    return {"access_token": access_token, "token_type": "bearer"}