# -*- coding: utf-8 -*-
"""
Script para gerar a estrutura de pastas e arquivos para o novo projeto qCyber FastAPI.

Ao ser executado, este script criará a seguinte estrutura:
.
├── .env_example
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
# Usamos strings raw (r''') para evitar problemas com caracteres especiais.
project_files = {

    "requirements.txt": r'''fastapi
uvicorn[standard]
pydantic
python-dotenv
PyMySQL
passlib[bcrypt]
python-jose[cryptography]
''',

    ".env_example": r'''# --- CONFIGURAÇÕES DO BANCO DE DADOS ---
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
# Permite que o frontend (rodando em outra porta/domínio) acesse a API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, restrinja para o domínio do seu frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui os roteadores na aplicação principal
# Cada roteador gerencia um conjunto de endpoints relacionados
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
import os
from dotenv import load_dotenv
from pydantic import BaseSettings

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

class Settings(BaseSettings):
    """
    Classe para gerenciar as configurações da aplicação.
    O Pydantic lê automaticamente as variáveis de ambiente.
    """
    # Configurações do Banco de Dados
    MYSQL_HOST: str = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "root")
    MYSQL_DB: str = os.getenv("MYSQL_DB", "qcyberDB")

    # Configurações de Segurança (JWT)
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default_secret")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))

    class Config:
        case_sensitive = True

# Instância única das configurações para ser usada em toda a aplicação
settings = Settings()
''',

    "schemas.py": r'''# -*- coding: utf-8 -*-
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
''',

    "security.py": r'''# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import ValidationError

from config import settings
from schemas import TokenData

# Esquema de segurança que define como o token será buscado (no header "Authorization: Bearer <token>")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login/token")

# Contexto para hashing de senhas, usando o algoritmo bcrypt
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
    """
    Cria e retorna uma conexão com o banco de dados.
    Esta é uma implementação simples. Em produção, considere usar um pool de conexões.
    """
    try:
        connection = pymysql.connect(
            host=settings.MYSQL_HOST,
            user=settings.MYSQL_USER,
            password=settings.MYSQL_PASSWORD,
            database=settings.MYSQL_DB,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor  # Retorna resultados como dicionários
        )
        return connection
    except Exception as e:
        print(f"Erro ao conectar ao banco de dados: {e}")
        return None

def get_cursor():
    """
    Dependência FastAPI para obter um cursor de banco de dados.
    Garante que a conexão seja fechada após o uso.
    """
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
        # Busca o usuário pelo email
        cursor.execute("SELECT * FROM usuarios WHERE email = %s", (form_data.username,))
        user = cursor.fetchone()

        # Verifica se o usuário existe e se a senha está correta
        if not user or not security.verify_password(form_data.password, user["senha_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Email ou senha incorretos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verifica se o usuário está ativo
        if not user.get('ativo', True):
             raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Usuário inativo.",
            )

        # Cria o token de acesso
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = security.create_access_token(
            data={"sub": user["email"]}, expires_delta=access_token_expires
        )

        return {"access_token": access_token, "token_type": "bearer"}

    except Exception as e:
        # Evita expor detalhes de erros internos
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
''',

    # Adiciona um __init__.py vazio para que a pasta 'routers' seja um módulo Python
    "routers/__init__.py": ""
}


def create_project_structure():
    """
    Função principal que cria as pastas e arquivos do projeto.
    """
    print("🚀 Iniciando a criação da estrutura do projeto qCyber FastAPI...")

    # Cria o diretório 'routers' se ele não existir
    if not os.path.exists('routers'):
        print("   -> Criando diretório: routers/")
        os.makedirs('routers')

    # Itera sobre o dicionário de arquivos e os cria
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
    print("1. Crie seu arquivo de ambiente: cp .env_example .env")
    print("2. Edite o arquivo .env com suas credenciais do banco e uma SECRET_KEY forte.")
    print("3. Instale as dependências: pip install -r requirements.txt")
    print("4. Execute a API: uvicorn main:app --reload --port 8000")
    print("5. Acesse a documentação interativa em: http://127.0.0.1:8000/docs")


if __name__ == "__main__":
    create_project_structure()
