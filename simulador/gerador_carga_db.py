# gerador_carga_db.py
import os
import json
import random
import pandas as pd
import pymysql
from dotenv import load_dotenv
from datetime import datetime, timedelta

# --- CONFIGURATION ---
DATA_PATH = "../data/dados_de_teste.csv"


# --- DATABASE FUNCTIONS ---
def get_db_connection():
    """Creates and returns a connection to the MySQL database."""
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
        print(f"❌ Database connection ERROR: {e}")
        return None


def get_active_device_ids(cursor):
    """Fetches the IDs of all active devices."""
    cursor.execute("SELECT id FROM dispositivos WHERE status_id = 1")
    return [row['id'] for row in cursor.fetchall()]


# --- ANALYSIS SIMULATION LOGIC (COPIED FROM SIMULATED_API) ---
def _gerar_analise_detalhada(tipo_ataque_id, tipo_ataque_nome):
    """
    Simulates a detailed analysis by an AI agent.
    Returns a dictionary with a summary, LLM explanation, risk, and recommended actions.
    """
    niveis_risco = {'Low': 1, 'Medium': 2, 'High': 3, 'Critical': 4}

    analises_predefinidas = {
        10: {
            "resumo": "An SQL injection attempt was detected...",
            "explicacao_llm": "The attacker tried to 'trick' the database by inserting malicious commands...",
            "risco_id": niveis_risco['Critical'], "acoes": ["Block IP...", "Validate queries...", "Review logs..."]
        },
        3: {
            "resumo": "An anomalous volume of TCP SYN packets was identified...",
            "explicacao_llm": "The system was flooded with fake connection requests...",
            "risco_id": niveis_risco['High'],
            "acoes": ["Activate rate limiting...", "Use DDoS mitigation...", "Increase pool..."]
        },
    }

    analise_default = {
        "resumo": f"Suspicious activity classified as '{tipo_ataque_nome}' has been detected...",
        "explicacao_llm": f"The system identified an unusual behavior pattern classified as '{tipo_ataque_nome}'...",
        "risco_id": niveis_risco['Medium'], "acoes": ["Isolate the host...", "Analyze logs...", "Check processes..."]
    }

    return analises_predefinidas.get(tipo_ataque_id, analise_default)


# --- MAIN LOAD GENERATOR FUNCTION ---
def run_generator():
    """
    Reads data from a CSV and inserts it directly into the database,
    simulating the API logic and distributing the data over a 40-day period.
    """
    conn = get_db_connection()
    if not conn:
        return

    try:
        attack_data = pd.read_csv(DATA_PATH)
    except FileNotFoundError:
        print(f"❌ ERROR: Data file not found at '{DATA_PATH}'")
        return

    with conn.cursor() as cursor:
        device_ids = get_active_device_ids(cursor)

        # Cache for attack names to avoid repeated queries in the loop
        cursor.execute("SELECT id, nome FROM enum_tipo_ataque")
        attack_names = {row['id']: row['nome'] for row in cursor.fetchall()}

    if not device_ids:
        print("❌ No active devices found. Generator shutting down.")
        conn.close()
        return

    # --- SIMULATED DATE LOGIC (40 DAYS) ---
    total_records = len(attack_data)
    start_date = datetime.now()
    end_date = start_date + timedelta(days=40)
    total_duration_seconds = (end_date - start_date).total_seconds()
    time_increment_per_record = total_duration_seconds / total_records

    print(f"🚀 Load generator started. Inserting {total_records} records into the database...")
    print(f"Simulation period: from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    for index, row in attack_data.iterrows():
        try:
            # --- DATA PREPARATION ---
            seconds_to_add = time_increment_per_record * index
            current_simulated_time = start_date + timedelta(seconds=seconds_to_add)
            target_device_id = random.choice(device_ids)

            # --- SIMULATION LOGIC (80% ACCURACY) ---
            if random.random() < 0.8:
                predicao = random.randint(0, 13)
            else:
                predicao = 99  # ID for 'Normal'

            tipo_ataque_nome = attack_names.get(predicao, "Unknown")

            # --- DATABASE TRANSACTION ---
            with conn.cursor() as cursor:
                # 1. INSERT THE DETECTION
                sql_deteccao = """
                               INSERT INTO deteccoes (dispositivo_id, predicao, tipo_ataque_id, relatorio_api, \
                                                      status_resposta_id, data_deteccao)
                               VALUES (%s, %s, %s, %s, %s, %s) \
                               """
                cursor.execute(sql_deteccao,
                               (target_device_id, predicao, predicao, f"Direct Load: Detected '{tipo_ataque_nome}'",
                                1, current_simulated_time))
                deteccao_id = cursor.lastrowid

                incidente_id = None
                # 2. IF IT'S AN ATTACK, GENERATE AND INSERT THE INCIDENT
                if predicao != 99:
                    analise = _gerar_analise_detalhada(predicao, tipo_ataque_nome)

                    sql_incidente = """
                                    INSERT INTO incidentes_analisados (titulo, status_id, dispositivo_id, \
                                                                       nivel_risco_id, data_deteccao, resumo_tecnico, \
                                                                       explicacao_llm, acoes_recomendadas)
                                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s) \
                                    """
                    cursor.execute(sql_incidente, (
                        f"Load Incident: {tipo_ataque_nome} on device {target_device_id}",
                        1, target_device_id, analise['risco_id'], current_simulated_time,
                        analise['resumo'], analise['explicacao_llm'], json.dumps(analise['acoes'])
                    ))
                    incidente_id = cursor.lastrowid

                    # 3. UPDATE THE DETECTION WITH THE LINK TO THE INCIDENT
                    sql_update_deteccao = "UPDATE deteccoes SET incidente_id = %s, status_resposta_id = %s WHERE id = %s"
                    cursor.execute(sql_update_deteccao, (incidente_id, 3, deteccao_id))

            conn.commit()  # Commit the transaction for this record

            print(
                f"Progress: {index + 1}/{total_records} | Date: {current_simulated_time.strftime('%Y-%m-%d')} | Detection ID: {deteccao_id} | Incident ID: {incidente_id or 'N/A'}")

        except Exception as e:
            print(f"❌ ERROR inserting row {index}: {e}")
            conn.rollback()  # Roll back the transaction in case of error

    conn.close()
    print("\n🏁 Data load complete.")


if __name__ == "__main__":
    # Clear the tables before running, if necessary:
    # TRUNCATE TABLE deteccoes;
    # TRUNCATE TABLE incidentes_analisados;
    run_generator()