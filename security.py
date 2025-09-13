# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import secrets
import string

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
import pymysql

from config import settings
from database import get_cursor

# Esquema de segurança que define como o token será buscado
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/token")

# Contexto para hashing de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ====================
#   SENHAS E CÓDIGOS
# ====================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha em texto plano corresponde à senha hasheada."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Gera o hash de uma senha."""
    return pwd_context.hash(password)


def generate_secure_code(length: int = 6) -> str:
    """Gera um código alfanumérico seguro. Mais fácil de digitar do que com caracteres especiais."""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))

# ====================
#   JWT TOKENS
# ====================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Cria um novo token de acesso (JWT)."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str, credentials_exception: HTTPException) -> Dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception

def get_current_user(token: str = Depends(oauth2_scheme), cursor: pymysql.cursors.DictCursor = Depends(get_cursor)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token, credentials_exception)
    if payload.get("scope") == "2fa_login":
         raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token inválido para esta operação. Complete a verificação 2FA.",
        )
    cursor.execute("SELECT * FROM usuarios WHERE email = %s", (payload["sub"],))
    user = cursor.fetchone()
    if user is None:
        raise credentials_exception
    return user

