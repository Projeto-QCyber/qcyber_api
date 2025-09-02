# -*- coding: utf-8 -*-
"""
Script para gerar a estrutura de pastas e arquivos para o novo projeto qCyber FastAPI.

Este script já está corrigido para ser compatível com Pydantic V2 e FastAPI recentes.

Ao ser executado, este script criará a seguinte estrutura:
.
├── .env
├── requirements.txt
├── main.py
├── config.py
├── database.py
├── schemas.py
├── security.py
└── routers/
    ├── __init__.py
    ├── dispositivos_router.py
    └── login_router.py

Basta salvar este arquivo como 'setup_fastapi_project.py' e executá-lo com:
python setup_fastapi_project.py
"""
import os

# --- CONTEÚDO DOS ARQUIVOS ---

# Dicionário onde a chave é o caminho do arquivo e o valor é o seu conteúdo.
project_files = {

    "requirements.txt": r'''fastapi
uvicorn[standard]
pydantic
pydantic-settings
python-dotenv
PyMySQL
passlib[bcrypt]
python-jose[cryptography]
''',

    ".env": r'''# --- CONFIGURAÇÕES DO BANCO DE DADOS ---
# Renomeie este arquivo para .env e preencha com seus dados
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=root
MYSQL_DB=qcyberDB

# --- CONFIGURAÇÕES DE SEGURANÇA (JWT) ---
# Gere uma chave secreta forte. Você pode usar: openssl rand -hex 32
SECRET_KEY="sua_chave_secreta_super_forte_aqui"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30
''',

    "main.py": r'''# -*- coding: utf-8 -*-
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importa os roteadores dos diferentes módulos
from routers import login_router, dispositivos_router

# Cria a instância principal da aplicação FastAPI
app = FastAPI(
    title="qCyber Security API",
    description="API para monitoramento de segurança e análise de detecções.",
    version="1.0.0"
)

# Configuração do CORS (Cross-Origin Resource Sharing)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, restrinja para o domínio do seu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui os roteadores na aplicação principal
app.include_router(login_router.router, tags=["Autenticação"])
app.include_router(dispositivos_router.router, tags=["Dispositivos"])


@app.get("/", tags=["Root"])
def read_root():
    """Endpoint inicial para verificar se a API está online."""
    return {"message": "Bem-vindo à qCyber Security API!"}

# Para executar a aplicação:
# uvicorn main:app --reload --port 8000
''',

    "config.py": r'''# -*- coding: utf-8 -*-
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """
    Classe para gerenciar as configurações da aplicação a partir de variáveis de ambiente.
    """
    # Configurações do Banco de Dados
    MYSQL_HOST: str
    MYSQL_USER: str
    MYSQL_PASSWORD: str
    MYSQL_DB: str

    # Configurações de Segurança (JWT)
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int

    class Config:
        env_file = ".env"  # Especifica o arquivo .env a ser lido
        case_sensitive = True

# Instância única das configurações para ser usada em toda a aplicação
settings = Settings()
''',

    "schemas.py": r'''# -*- coding: utf-8 -*-
from pydantic import BaseModel, EmailStr
from typing import Optional
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
        from_attributes = True  # ATUALIZADO de orm_mode

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
        from_attributes = True # ATUALIZADO de orm_mode
''',

    "security.py": r'''# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from config import settings
from schemas import TokenData

# Esquema de segurança que define como o token será buscado
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/token")

# Contexto para hashing de senhas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica se a senha em texto plano corresponde à senha hasheada."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Gera o hash de uma senha."""
    return pwd_context.hash(password)

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
''',

    "database.py": r'''# -*- coding: utf-8 -*-
import pymysql
from config import settings
from fastapi import HTTPException

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    try:
        connection = pymysql.connect(
            host=settings.MYSQL_HOST,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            database=settings.MYSQL_DB,
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
''',

    "routers/login_router.py": r'''# -*- coding: utf-8 -*-
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
''',

    "routers/dispositivos_router.py": r'''# -*- coding: utf-8 -*-
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
import pymysql

import schemas
import security
from database import get_cursor

router = APIRouter(
    prefix="/dispositivos",
    dependencies=[Depends(security.oauth2_scheme)] 
)

@router.get("/", response_model=List[schemas.Dispositivo])
def read_dispositivos(cursor: pymysql.cursors.DictCursor = Depends(get_cursor)):
    """Busca e retorna a lista de todos os dispositivos cadastrados."""
    try:
        cursor.execute("SELECT id, nome, host, localizacao, status, data_cadastro FROM dispositivos ORDER BY nome ASC")
        return cursor.fetchall()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao buscar dispositivos: {e}")

@router.post("/", response_model=schemas.Dispositivo, status_code=status.HTTP_201_CREATED)
def create_dispositivo(
    dispositivo: schemas.DispositivoCreate, 
    cursor: pymysql.cursors.DictCursor = Depends(get_cursor)
):
    """Cadastra um novo dispositivo no banco de dados."""
    try:
        cursor.execute("SELECT id FROM dispositivos WHERE host = %s", (dispositivo.host,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este host já está cadastrado."
            )

        sql = "INSERT INTO dispositivos (nome, host, localizacao) VALUES (%s, %s, %s)"
        cursor.execute(sql, (dispositivo.nome, dispositivo.host, dispositivo.localizacao))
        new_id = cursor.lastrowid

        cursor.execute("SELECT id, nome, host, localizacao, status, data_cadastro FROM dispositivos WHERE id = %s", (new_id,))
        new_dispositivo = cursor.fetchone()

        cursor.connection.commit()

        return new_dispositivo

    except pymysql.MySQLError as e:
        cursor.connection.rollback()
        raise HTTPException(status_code=500, detail=f"Erro de banco de dados: {e}")
    except Exception as e:
        cursor.connection.rollback()
        raise HTTPException(status_code=500, detail=f"Erro interno: {e}")
''',

    "routers/__init__.py": ""
}


def create_project_structure():
    """Função principal que cria as pastas e arquivos do projeto."""
    print("🚀 Iniciando a criação da estrutura do projeto qCyber FastAPI...")

    if not os.path.exists('../routers'):
        print("   -> Criando diretório: routers/")
        os.makedirs('../routers')

    for file_path, content in project_files.items():
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"   ✅ Arquivo criado: {file_path}")
        except Exception as e:
            print(f"   ❌ Erro ao criar o arquivo {file_path}: {e}")
            return

    print("\n🎉 Estrutura do projeto criada com sucesso!")
    print("\n--- PRÓXIMOS PASSOS ---")
    print("1. Apague a estrutura antiga, se houver.")
    print("2. Crie seu arquivo de ambiente: cp .env .env")
    print("3. Edite o arquivo .env com suas credenciais e uma SECRET_KEY forte.")
    print("4. Instale as dependências: pip install -r requirements.txt")
    print("5. Execute a API: uvicorn main:app --reload --port 8000")
    print("6. Acesse a documentação interativa em: http://127.0.0.1:8000/docs")


if __name__ == "__main__":
    create_project_structure()

