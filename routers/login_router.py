# -*- coding: utf-8 -*-
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
import pymysql

import schemas
import security
from config import settings
from database import get_cursor

router = APIRouter(
    prefix="/login"
)

@router.post("/token", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    cursor: pymysql.cursors.DictCursor = Depends(get_cursor)
):
    """
    Endpoint de login. Recebe email (no campo 'username') e senha.
    Verifica as credenciais e retorna um token JWT.
    """
    try:
        cursor.execute("SELECT * FROM usuarios WHERE email = %s", (form_data.username,))
        user = cursor.fetchone()

        if not user or not security.verify_password(form_data.password, user["senha_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.get('ativo', True):
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário inativo.",
            )

        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            data={"sub": user["email"]}, expires_delta=access_token_expires
        )

        return {"access_token": access_token, "token_type": "bearer"}

    except Exception as e:
        print(f"Erro no login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ocorreu um erro interno durante o login."
        )
