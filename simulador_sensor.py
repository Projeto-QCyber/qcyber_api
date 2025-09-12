# simulador_sensor.py
import os
import time
import json
import random
import pandas as pd
import pymysql
import requests  # Importa a biblioteca para fazer requisições HTTP
from dotenv import load_dotenv
from datetime import datetime

# --- CONFIGURAÇÕES ---
# Endereço da sua nova API de análise (rodando no desktop)
API_ANALISE_URL = "http://192.168.1.68:5000/analisar"
DATA_PATH = "data/dados_de_teste.csv"


# --- FUNÇÕES DE BANCO DE DADOS ---
def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados MySQL."""
    load_dotenv()
    try:
        conn = pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', 'root'),
            database=os.getenv('MYSQL_DB', 'qcyberDB'),
            cursorclass=pymysql.cursors.DictCursor
        )
        return conn
    except Exception as e:
        print(f"❌ ERRO de conexão com o banco de dados: {e}")
        return None


def get_active_device_ids(cursor):
    """Busca os IDs de todos os dispositivos ativos."""
    cursor.execute("SELECT id FROM dispositivos WHERE status_id = 1")
    return [row['id'] for row in cursor.fetchall()]


# --- FUNÇÃO PRINCIPAL DO SIMULADOR ---
def run_simulator():
    """
    Lê dados do CSV e os envia para a API de análise para simular um sensor de rede.
    """
    conn = get_db_connection()
    if not conn:
        return

    with conn.cursor() as cursor:
        device_ids = get_active_device_ids(cursor)

    if not device_ids:
        print("❌ Nenhum dispositivo ativo encontrado no banco. O simulador não pode atribuir ataques.")
        return

    conn.close()

    try:
        attack_data = pd.read_csv(DATA_PATH)
    except FileNotFoundError:
        print(f"❌ ERRO: Arquivo de dados não encontrado em '{DATA_PATH}'")
        return

    print(f"🚀 Simulador iniciado. Enviando {len(attack_data)} eventos de ataque para a API de análise...")

    for index, row in attack_data.iterrows():
        try:
            print("\n" + "=" * 50)
            print(f"[{datetime.now()}] Enviando evento {index + 1}/{len(attack_data)} para análise...")

            # Prepara os dados da linha para enviar como JSON
            features = row.drop(["Attack_label", "Attack_type"]).to_dict()

            # Escolhe um dispositivo aleatório para o qual o ataque será simulado
            target_device_id = random.choice(device_ids)

            # Monta o payload para a API
            payload = {
                'device_id': target_device_id,
                'features': features
            }

            # Envia a requisição POST para a API de análise
            response = requests.post(API_ANALISE_URL, json=payload)

            # Verifica a resposta da API
            if response.status_code == 201:
                print(f"✅ Sucesso! API analisou e salvou a detecção. Resposta: {response.json()}")
            else:
                print(f"⚠️ Falha! A API retornou status {response.status_code}. Resposta: {response.text}")

        except Exception as e:
            print(f"❌ ERRO ao enviar a requisição para a linha {index}: {e}")

        time.sleep(random.uniform(2, 5))  # Espera entre 2 e 5 segundos

    print("\n🏁 Simulação concluída.")


if __name__ == "__main__":
    run_simulator()