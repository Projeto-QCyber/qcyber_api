# -*- coding: utf-8 -*-
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime

# --- Schemas de Token ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# --- Schemas de Usuário ---
class UserBase(BaseModel):
    email: EmailStr
    nome: str

class UserInDB(UserBase):
    id: int
    ativo: bool
    is_admin: bool
    senha_hash: str

    class Config:
        orm_mode = True

# --- Schemas de Dispositivo ---
class DispositivoBase(BaseModel):
    nome: str
    host: str
    localizacao: Optional[str] = None

class DispositivoCreate(DispositivoBase):
    pass

class Dispositivo(DispositivoBase):
    id: int
    status: str
    data_cadastro: datetime

    class Config:
        orm_mode = True # Permite que o Pydantic leia dados de objetos (como os do ORM)
