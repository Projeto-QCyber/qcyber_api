# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.security import OAuth2PasswordRequestForm
from jose import JWTError, jwt  # <--- Importante: Adicionado para decodificar o token manualmente
import pymysql

from datetime import datetime, timezone

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
    Caso contrário, retorna access_token e refresh_token.
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
        expiration = datetime.utcnow() + timedelta(minutes=5)

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

    # Login normal (Sucesso)
    access_token = security.create_access_token(data={"sub": user["email"]})
    refresh_token = security.create_refresh_token(data={"sub": user["email"]})  # <--- Novo

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/token/2fa", response_model=schemas.Token)
def verify_2fa_login(
        verification_data: schemas.TwoFactorVerify,
        cursor: pymysql.cursors.DictCursor = Depends(get_cursor)
):
    """Verifica o código 2FA do e-mail e retorna os tokens de acesso final."""
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

    if datetime.utcnow() > user['codigo_verificacao_expiracao']:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código 2FA expirado.")

    # Sucesso: Limpa os campos e gera o token final
    sql = "UPDATE usuarios SET codigo_verificacao=NULL, codigo_verificacao_expiracao=NULL, tentativas_verificacao=0 WHERE id=%s"
    cursor.execute(sql, (user['id'],))
    cursor.connection.commit()

    access_token = security.create_access_token(data={"sub": user["email"]})
    refresh_token = security.create_refresh_token(data={"sub": user["email"]})  # <--- Novo

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=schemas.Token)
def refresh_token(
        token_data: schemas.TokenRefresh,
        cursor: pymysql.cursors.DictCursor = Depends(get_cursor)
):
    """
    Recebe um Refresh Token válido e retorna um novo par de tokens.
    Verifica se o token foi revogado (Logout).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido, expirado ou revogado.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. Verifica na Blacklist ANTES de decodificar (economiza CPU)
    if security.is_token_blacklisted(token_data.refresh_token, cursor):
        raise credentials_exception

    try:
        payload = jwt.decode(token_data.refresh_token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")

        if email is None or token_type != "refresh":
            raise credentials_exception

    except JWTError:
        raise credentials_exception

    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
    user = cursor.fetchone()

    if not user or not user.get('ativo', True):
        raise credentials_exception

    # Opcional: Se você quiser fazer rotação de token (o refresh token muda a cada uso)
    # você deve adicionar o token antigo na blacklist AQUI.
    # Por enquanto, vamos manter simples (apenas renova o access).

    new_access_token = security.create_access_token(data={"sub": email})
    # Se quiser manter o mesmo refresh token até expirar, devolva o mesmo.
    # Se quiser gerar um novo (mais seguro), gere um novo aqui.
    new_refresh_token = security.create_refresh_token(data={"sub": email})

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


# --- NOVA ROTA DE LOGOUT ---
@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
        token_data: schemas.TokenRevoke,
        cursor: pymysql.cursors.DictCursor = Depends(get_cursor)
):
    """
    Revoga um token (Logout). Adiciona o token à Blacklist até sua data de expiração.
    """
    try:
        # Decodificamos sem verificar assinatura rigorosamente apenas para pegar a data de expiração
        # Mas é bom validar para não sujar o banco com lixo
        payload = jwt.decode(token_data.token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])

        # Pega o email para achar o ID do usuário (opcional, mas bom para auditoria)
        email = payload.get("sub")
        exp_timestamp = payload.get("exp")

        # Converte timestamp UNIX para datetime
        expiration_date = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)

        # Busca ID do usuário
        cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
        user = cursor.fetchone()
        user_id = user['id'] if user else None

        # Insere na Blacklist
        sql = """
            INSERT INTO token_blacklist (token, tipo_token, usuario_id, data_expiracao)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(sql, (token_data.token, payload.get("type", "refresh"), user_id, expiration_date))
        cursor.connection.commit()

    except Exception as e:
        # Se o token for inválido, tecnicamente o usuário já está "deslogado",
        # então não precisamos retornar erro 500, apenas ignoramos ou retornamos 204.
        pass

    return Response(status_code=status.HTTP_204_NO_CONTENT)