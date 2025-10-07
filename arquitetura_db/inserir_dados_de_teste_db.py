# -*- coding: utf-8 -*-
"""
Script to populate the qCyber database with mock data that reflects
the real business flow (detection -> action -> analysis).

This script:
1. Clears dynamic data tables (deteccoes, incidentes_analisados, dispositivos)
   and relevant enum tables.
2. Inserts example devices with their statuses.
3. Generates a defined number of detections.
4. For a portion of detections (e.g., 30%), simulates an automated action.
5. For another portion (e.g., 75%), generates a corresponding analyzed incident.
6. Correctly links detections to their incidents.
"""
import os
import pymysql
from dotenv import load_dotenv
from datetime import datetime, timedelta
import random


def get_lookup_ids(cursor, table_name):
    """Fetches IDs and names from a lookup table."""
    try:
        cursor.execute(f"SELECT id, nome FROM {table_name}")
        result = cursor.fetchall()
        if not result:
            print(f"⚠️ WARNING: Lookup table '{table_name}' is empty.")
            return {}
        return {row['nome']: row['id'] for row in result}
    except pymysql.Error as e:
        print(f"❌ ERROR fetching data from table '{table_name}': {e}")
        return None


def ensure_risk_levels(cursor):
    """Ensures that all necessary risk levels exist in the table."""
    print("  - Verifying and inserting risk levels...")
    risk_levels = ["Low", "Medium", "High", "Critical", "Unknown"]
    try:
        for level in risk_levels:
            # INSERT IGNORE does not insert if the 'nome' already exists (assuming 'nome' is UNIQUE)
            cursor.execute("INSERT IGNORE INTO enum_nivel_risco (nome) VALUES (%s)", (level,))
        print("  - Risk levels ensured.")
        return True
    except pymysql.Error as e:
        print(f"❌ ERROR inserting risk levels: {e}")
        return False

def ensure_device_statuses(cursor):
    """Ensures that all necessary device statuses exist in the table."""
    print("  - Verifying and inserting device statuses...")
    statuses = ["Active", "Inactive", "Maintenance"]
    try:
        for status in statuses:
            cursor.execute("INSERT IGNORE INTO enum_status_dispositivo (nome) VALUES (%s)", (status,))
        print("  - Device statuses ensured.")
        return True
    except pymysql.Error as e:
        print(f"❌ ERROR inserting device statuses: {e}")
        return False

def ensure_response_statuses(cursor):
    """Ensures that all necessary response statuses exist in the table."""
    print("  - Verifying and inserting response statuses...")
    statuses = ["Pending", "Automated Action Executed", "Analysis Complete", "False Positive"]
    try:
        for status in statuses:
            cursor.execute("INSERT IGNORE INTO enum_status_resposta (nome) VALUES (%s)", (status,))
        print("  - Response statuses ensured.")
        return True
    except pymysql.Error as e:
        print(f"❌ ERROR inserting response statuses: {e}")
        return False


def seed_data():
    """Connects to the database and inserts the mock data."""
    load_dotenv()
    db_name = os.getenv('MYSQL_DB', 'qcyber_db')

    try:
        conn = pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', 'root'),
            database=db_name,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print(f"✅ Successfully connected to database '{db_name}'!")
    except pymysql.err.OperationalError as e:
        print(f"❌ ERROR: Failed to connect to the database. Check credentials, host, and if the database '{db_name}' exists.")
        print(f"   Details: {e}")
        return

    try:
        with conn.cursor() as cursor:
            # STEP 0: Clean up old tables
            print("\nSTEP 0: Cleaning up old tables...")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            cursor.execute("TRUNCATE TABLE deteccoes;")
            cursor.execute("TRUNCATE TABLE incidentes_analisados;")
            cursor.execute("TRUNCATE TABLE dispositivos;")
            # Also truncate enum tables that will be re-populated
            cursor.execute("TRUNCATE TABLE enum_nivel_risco;")
            cursor.execute("TRUNCATE TABLE enum_status_dispositivo;")
            cursor.execute("TRUNCATE TABLE enum_status_resposta;")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            print("  - Dynamic data and enum tables have been cleared.")

            # STEP 1: Ensure and load base data
            if not ensure_risk_levels(cursor) or \
               not ensure_device_statuses(cursor) or \
               not ensure_response_statuses(cursor):
                raise Exception("Failed to ensure base enum data.")
            conn.commit()

            print("\nSTEP 1: Loading IDs from Enum tables...")
            ids = {
                "status_disp_ids": get_lookup_ids(cursor, "enum_status_dispositivo"),
                "status_inc_ids": get_lookup_ids(cursor, "enum_status_incidente"),
                "risco_ids": get_lookup_ids(cursor, "enum_nivel_risco"),
                "status_resp_ids": get_lookup_ids(cursor, "enum_status_resposta"),
                "acao_ids": get_lookup_ids(cursor, "enum_acao_executada"),
            }
            for key, value in ids.items():
                if value is None or not value:
                    raise Exception(
                        f"Failed to load or enum table is empty for '{key}'. Please populate the 'enum' tables first.")
            print("✅ IDs loaded successfully.")

            # STEP 2: Insert Devices
            print("\nSTEP 2: Inserting devices...")
            dispositivos_data = [
                ('Main Application Server', '192.168.1.10', 'Data Center A',
                 ids['status_disp_ids'].get('Active')),
                ('Database Server', '192.168.1.15', 'Data Center A', ids['status_disp_ids'].get('Active')),
                ('Workstation - Finance', '10.0.5.22', 'Central Office',
                 ids['status_disp_ids'].get('Active')),
                ('Network Gateway', '192.168.0.1', 'Server Room', ids['status_disp_ids'].get('Active')),
                ('Web Server - Legacy', '192.168.2.50', 'Data Center B', ids['status_disp_ids'].get('Inactive'))
            ]
            dispositivo_ids_map = {}
            for nome, host, localizacao, status_id in dispositivos_data:
                cursor.execute("INSERT INTO dispositivos (nome, host, localizacao, status_id) VALUES (%s, %s, %s, %s)",
                               (nome, host, localizacao, status_id))
                dispositivo_ids_map[cursor.lastrowid] = nome
            print(f"  - {len(dispositivo_ids_map)} devices inserted.")
            conn.commit()

            # STEP 3: Generate Detections and, for some, their corresponding Incidents and Actions
            print("\nSTEP 3: Generating detections, actions, and incidents...")
            total_detections = 200
            incidents_created = 0
            actions_executed = 0
            tipos_ataque_random = [0, 1, 5, 6, 7, 8, 9, 10, 12, 13]
            riscos_ponderados = [
                ids['risco_ids']['Critical'], ids['risco_ids']['Critical'],
                ids['risco_ids']['High'], ids['risco_ids']['High'], ids['risco_ids']['High'],
                ids['risco_ids']['Medium'], ids['risco_ids']['Medium'],
                ids['risco_ids']['Low']
            ]
            acoes_possiveis = list(ids['acao_ids'].values())

            for i in range(total_detections):
                # 1. Prepare detection data
                disp_id = random.choice(list(dispositivo_ids_map.keys()))
                ataque_id = random.choice(tipos_ataque_random)
                status_resp_id = ids['status_resp_ids']['Pending']
                data_det = datetime.now() - timedelta(days=random.randint(0, 89), hours=random.randint(0, 23))
                relatorio = f'Suspicious activity from attack code {ataque_id} detected.'

                acao_id, acao_param, data_acao = None, None, None

                # --- NEW LOGIC TO SIMULATE ACTION ---
                if random.random() < 0.30: # 30% chance of having an action
                    actions_executed += 1
                    acao_id = random.choice(acoes_possiveis)
                    acao_param = f"10.0.{random.randint(1, 254)}.{random.randint(1, 254)}"
                    data_acao = data_det + timedelta(seconds=random.randint(5, 60))
                    status_resp_id = ids['status_resp_ids']['Automated Action Executed']

                # 2. Insert the detection with action fields (which can be NULL)
                cursor.execute(
                    """INSERT INTO deteccoes (data_deteccao, dispositivo_id, predicao, tipo_ataque_id, relatorio_api,
                                              status_resposta_id, incidente_id, acao_executada_id, acao_parametro, data_acao_executada)
                       VALUES (%s, %s, %s, %s, %s, %s, NULL, %s, %s, %s)""",
                    (data_det, disp_id, ataque_id, ataque_id, relatorio, status_resp_id, acao_id, acao_param, data_acao)
                )
                new_detection_id = cursor.lastrowid

                # 3. Decide if an incident should be generated for this detection (75% chance)
                if random.random() < 0.75:
                    incidents_created += 1
                    risco_id = random.choice(riscos_ponderados)
                    titulo = f"Incident Analysis for Detection #{new_detection_id}"
                    status_id = random.choice(list(ids['status_inc_ids'].values()))

                    cursor.execute(
                        """INSERT INTO incidentes_analisados (titulo, status_id, dispositivo_id, nivel_risco_id,
                                                              data_deteccao, resumo_tecnico)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (titulo, status_id, disp_id, risco_id, data_det,
                         "Event automatically generated and analyzed for testing.")
                    )
                    new_incident_id = cursor.lastrowid

                    # 4. UPDATE the original detection with the new incident's ID
                    cursor.execute(
                        "UPDATE deteccoes SET incidente_id = %s WHERE id = %s",
                        (new_incident_id, new_detection_id)
                    )

            print(f"  - {total_detections} random detections inserted.")
            print(f"  - {actions_executed} automated actions were simulated.")
            print(f"  - {incidents_created} analyzed incidents were created and linked.")
            conn.commit()

            print("\n🎉 Mock data inserted successfully with correct links!")

    except Exception as e:
        print(f"❌ ERROR during execution: {e}")
        if 'conn' in locals() and conn.open:
            conn.rollback()
            print("  - Rollback executed.")
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()
            print("\n🔌 Database connection closed.")


if __name__ == '__main__':
    if not os.path.exists('.env'):
        print("'.env' file not found. Creating one with default values (localhost)...")
        with open('.env', 'w') as f:
            f.write("MYSQL_HOST=localhost\n")
            f.write("MYSQL_USER=root\n")
            f.write("MYSQL_PASSWORD=root\n")
            f.write("MYSQL_DB=qcyber_db\n")

    db_env = os.getenv('MYSQL_DB', 'qcyber_db')
    print(f"This script will CLEAR and RE-INSERT data into the '{db_env}' database.")
    # In English
    response = input("ATTENTION: PREVIOUS DATA WILL BE DELETED. Do you wish to continue? (y/N): ")
    if response.lower() in ['y', 'yes']:
        seed_data()
    else:
        print("Operation canceled.")