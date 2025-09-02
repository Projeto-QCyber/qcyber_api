# QCyber Security API

API para monitoramento de segurança desenvolvida com FastAPI.

### Pré-requisitos

* **Python 3.13.7**
* Banco de dados MySQL

## Como Executar a API

Para iniciar o servidor em modo de desenvolvimento (com recarregamento automático), execute o seguinte comando no terminal:

```bash
uvicorn main:app --reload



## Rotas

Autenticação
POST /login/token: Realiza a autenticação do usuário (recebendo email e senha) e retorna um token de acesso JWT.

Dispositivos
GET /dispositivos/: Retorna a lista de todos os dispositivos cadastrados. Requer autenticação.

POST /dispositivos/: Cadastra um novo dispositivo no sistema. Requer autenticação.

Raiz
GET /: Endpoint inicial da API, usado para verificar se o serviço está online.