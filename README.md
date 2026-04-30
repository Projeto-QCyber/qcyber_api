# QCyber Security API

API para monitoramento de segurança desenvolvida com FastAPI. 

### Pré-requisitos

* **Python 3.13.7**
* Banco de dados MySQL

## Estrutura do .env:
```
# Para o SGBD  (mesmas configurações do repositório QML em relação ao SGBD)
MYSQL_HOST=localhost
MYSQL_PORT=5000
MYSQL_ROOT_PASSWORD=
MYSQL_DATABASE=qcyber_db
MYSQL_USER=
MYSQL_PASSWORD=

# Segurança
SECRET_KEY=""
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Outros
FRONTEND_BASE_URL=
NGINX_PORT=4545
```


## Como Executar a API

Para iniciar o servidor em modo de desenvolvimento (com recarregamento automático), execute o seguinte comando no terminal:

```bash
uvicorn main:app --reload
```



## IMPORTANTE

configuarar a variavel de ambinete apontando para o link do servidor de produção;
Ela esta na config.py e na .env 

```
FRONTEND_BASE_URL
```


## Rotas

Autenticação
POST /login/token: Realiza a autenticação do usuário (recebendo email e senha) e retorna um token de acesso JWT.

Dispositivos
GET /dispositivos/: Retorna a lista de todos os dispositivos cadastrados. Requer autenticação.

POST /dispositivos/: Cadastra um novo dispositivo no sistema. Requer autenticação.

Raiz
GET /: Endpoint inicial da API, usado para verificar se o serviço está online.