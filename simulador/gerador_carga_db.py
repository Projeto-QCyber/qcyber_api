# gerador_carga_db.py
import os
import json
import random
import pandas as pd
import pymysql
from dotenv import load_dotenv
from datetime import datetime, timedelta

# --- CONFIGURAÇÕES ---
DATA_PATH = "../data/dados_de_teste.csv"


# --- FUNÇÕES DE BANCO DE DADOS ---
def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados MySQL."""
    load_dotenv()
    try:
        conn = pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', 'root'),
            database=os.getenv('MYSQL_DATABASE', 'qcyber_db'),
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


# --- LÓGICA DE SIMULAÇÃO DE ANÁLISE (COPIADA DA API_SIMULADA) ---
def _gerar_analise_detalhada(tipo_ataque_id, tipo_ataque_nome):
    """
    Simula a análise detalhada de um agente de IA.
    Retorna um dicionário com resumo, explicação do LLM, risco e ações recomendadas.
    """
    niveis_risco = {'Baixo': 1, 'Médio': 2, 'Alto': 3, 'Crítico': 4}

    analises_predefinidas = {
        10: {
            "resumo": "Foi detectada uma tentativa de injeção de SQL...",
            "explicacao_llm": "O invasor tentou 'enganar' o banco de dados inserindo comandos maliciosos...",
            "risco_id": niveis_risco['Crítico'], "acoes": ["Bloquear IP...", "Validar queries...", "Revisar logs..."]
        },
        3: {
            "resumo": "Identificado um volume anômalo de pacotes TCP SYN...",
            "explicacao_llm": "O sistema foi inundado com pedidos de conexão falsos...",
            "risco_id": niveis_risco['Alto'],
            "acoes": ["Ativar rate limiting...", "Usar mitigação de DDoS...", "Aumentar pool..."]
        },
    }

    analise_default = {
        "resumo": f"Uma atividade suspeita classificada como '{tipo_ataque_nome}' foi detectada...",
        "explicacao_llm": f"O sistema identificou um padrão de comportamento incomum classificado como '{tipo_ataque_nome}'...",
        "risco_id": niveis_risco['Médio'], "acoes": ["Isolar o host...", "Analisar logs...", "Verificar processos..."]
    }

    return analises_predefinidas.get(tipo_ataque_id, analise_default)


# --- FUNÇÃO PRINCIPAL DO GERADOR DE CARGA ---
def run_generator():
    """
    Lê dados do CSV e os insere diretamente no banco de dados,
    simulando a lógica da API e distribuindo os dados ao longo de 40 dias.
    """
    conn = get_db_connection()
    if not conn:
        return

    try:
        attack_data = pd.read_csv(DATA_PATH)
    except FileNotFoundError:
        print(f"❌ ERRO: Arquivo de dados não encontrado em '{DATA_PATH}'")
        return

    with conn.cursor() as cursor:
        device_ids = get_active_device_ids(cursor)

        # Cache para nomes de ataques para evitar queries repetidas no loop
        cursor.execute("SELECT id, nome FROM enum_tipo_ataque")
        attack_names = {row['id']: row['nome'] for row in cursor.fetchall()}

    if not device_ids:
        print("❌ Nenhum dispositivo ativo encontrado. Gerador encerrado.")
        conn.close()
        return

    # --- LÓGICA DE DATA SIMULADA (40 DIAS) ---
    total_records = len(attack_data)
    start_date = datetime.now()
    end_date = start_date + timedelta(days=40)  # Alterado para 40 dias
    total_duration_seconds = (end_date - start_date).total_seconds()
    time_increment_per_record = total_duration_seconds / total_records

    print(f"🚀 Gerador de carga iniciado. Inserindo {total_records} registros no banco...")
    print(f"Período de simulação: de {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")

    for index, row in attack_data.iterrows():
        try:
            # --- PREPARAÇÃO DOS DADOS ---
            seconds_to_add = time_increment_per_record * index
            current_simulated_time = start_date + timedelta(seconds=seconds_to_add)
            target_device_id = random.choice(device_ids)

            # --- LÓGICA DE SIMULAÇÃO (80% ACURÁCIA) ---
            if random.random() < 0.8:
                predicao = random.randint(0, 13)
            else:
                predicao = 99  # ID para 'Normal'

            tipo_ataque_nome = attack_names.get(predicao, "Desconhecido")

            # --- TRANSAÇÃO NO BANCO DE DADOS ---
            with conn.cursor() as cursor:
                # 1. INSERE A DETECÇÃO
                sql_deteccao = """
                               INSERT INTO deteccoes (dispositivo_id, predicao, tipo_ataque_id, relatorio_api, \
                                                      status_resposta_id, data_deteccao)
                               VALUES (%s, %s, %s, %s, %s, %s) \
                               """
                cursor.execute(sql_deteccao,
                               (target_device_id, predicao, predicao, f"Carga Direta: Detectado '{tipo_ataque_nome}'",
                                1, current_simulated_time))
                deteccao_id = cursor.lastrowid

                incidente_id = None
                # 2. SE FOR ATAQUE, GERA E INSERE O INCIDENTE
                if predicao != 99:
                    analise = _gerar_analise_detalhada(predicao, tipo_ataque_nome)

                    sql_incidente = """
                                    INSERT INTO incidentes_analisados (titulo, status_id, dispositivo_id, \
                                                                       nivel_risco_id, data_deteccao, resumo_tecnico, \
                                                                       explicacao_llm, acoes_recomendadas)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) \
                                    """
                    cursor.execute(sql_incidente, (
                        f"Incidente de Carga: {tipo_ataque_nome} no dispositivo {target_device_id}",
                        1, target_device_id, analise['risco_id'], current_simulated_time,
                        analise['resumo'], analise['explicacao_llm'], json.dumps(analise['acoes'])
                    ))
                    incidente_id = cursor.lastrowid

                    # 3. ATUALIZA A DETECÇÃO COM O LINK PARA O INCIDENTE
                    sql_update_deteccao = "UPDATE deteccoes SET incidente_id = %s, status_resposta_id = %s WHERE id = %s"
                    cursor.execute(sql_update_deteccao, (incidente_id, 3, deteccao_id))

            conn.commit()  # Salva a transação para este registro

            print(
                f"Progresso: {index + 1}/{total_records} | Data: {current_simulated_time.strftime('%Y-%m-%d')} | Detecção ID: {deteccao_id} | Incidente ID: {incidente_id or 'N/A'}")

        except Exception as e:
            print(f"❌ ERRO ao inserir a linha {index}: {e}")
            conn.rollback()  # Desfaz a transação em caso de erro

    conn.close()
    print("\n🏁 Carga de dados concluída.")


if __name__ == "__main__":
    # Limpe as tabelas antes de executar, se necessário:
    # TRUNCATE TABLE deteccoes;
    # TRUNCATE TABLE incidentes_analisados;
    run_generator()