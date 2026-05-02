# Estágio 1: Estágio de Build (Instalação de Dependências)
# Usamos uma imagem Python leve com suporte a Alpine Linux para um tamanho final reduzido.
FROM python:3.13-slim-bookworm AS builder

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Define variáveis de ambiente para o pip e Python (opcional, mas recomendado)
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instala as dependências: Copia apenas o arquivo de requisitos para aproveitar o cache do Docker
COPY requirements.txt .

# Instala as dependências do Python
# Usamos --no-cache-dir para economizar espaço
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# ---

# Estágio 2: Estágio Final (Runtime)
# Otimiza o tamanho final copiando apenas o mínimo necessário
FROM python:3.13-slim-bookworm

WORKDIR /app

# Copia as bibliotecas instaladas e o código da aplicação
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY . .

# Expõe a porta que o Uvicorn usará (padrão é 8000)
EXPOSE 8000

# Comando para iniciar o servidor Uvicorn com o Gunicorn (recomendado para produção)
ENTRYPOINT [ "/app/entrypoint.sh" ]