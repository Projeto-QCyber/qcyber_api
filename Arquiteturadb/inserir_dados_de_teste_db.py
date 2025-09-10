# -*- coding: utf-8 -*-
"""
Script para popular o banco de dados qCyber com um grande volume de dados
de exemplo (mock data), ideal para testes de performance e visualização.
(VERSÃO FINAL NORMALIZADA E COM VOLUME AMPLIADO)

Este script:
1. Limpa completamente as tabelas de dados dinâmicos.
2. Garante a existência de todos os níveis de risco, incluindo 'Desconhecido'.
3. Insere um grande volume de incidentes (150) e detecções (200).
4. Distribui os dados ao longo dos últimos 90 dias.
"""
import os
import pymysql
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta
import random
import sys


def get_lookup_ids(cursor, table_name):
    """
    Busca IDs e nomes de uma tabela de lookup e retorna um dicionário
    para fácil acesso. Ex: {'Ativo': 1, 'Inativo': 2}
    """
    try:
        cursor.execute(f"SELECT id, nome FROM {table_name}")
        result = cursor.fetchall()
        if not result:
            print(f"⚠️ AVISO: A tabela de lookup '{table_name}' está vazia.")
            return {}
        return {row['nome']: row['id'] for row in result}
    except pymysql.Error as e:
        print(f"❌ ERRO ao buscar dados da tabela '{table_name}': {e}")
        return None  # Retorna None para indicar falha


def ensure_risk_levels(cursor):
    """Garante que todos os níveis de risco necessários existam na tabela."""
    print("  - Verificando e inserindo níveis de risco...")
    risk_levels = ["Baixo", "Médio", "Alto", "Crítico", "Desconhecido"]
    try:
        for level in risk_levels:
            # Usamos INSERT IGNORE para evitar erros se o nível já existir
            cursor.execute("INSERT IGNORE INTO enum_nivel_risco (nome) VALUES (%s)", (level,))
        print("  - Níveis de risco garantidos.")
        return True
    except pymysql.Error as e:
        print(f"❌ ERRO ao inserir níveis de risco: {e}")
        return False


def seed_data():
    """Conecta ao banco e insere os dados de exemplo."""
    load_dotenv()
    db_name = os.getenv('MYSQL_DB', 'qcyberDB')

    try:
        conn = pymysql.connect(
            host=os.getenv('MYSQL_HOST', 'localhost'),
            user=os.getenv('MYSQL_USER', 'root'),
            password=os.getenv('MYSQL_PASSWORD', 'root'),
            database=db_name,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        print(f"✅ Conectado ao banco de dados '{db_name}' com sucesso!")
    except pymysql.err.OperationalError as e:
        print(f"❌ ERRO: Falha ao conectar ao banco. Verifique as credenciais, o host e se o banco '{db_name}' existe.")
        print(f"   Detalhes: {e}")
        return

    try:
        with conn.cursor() as cursor:
            # PASSO 0: Limpar tabelas
            print("\nPASSO 0: Limpando tabelas antigas...")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            cursor.execute("TRUNCATE TABLE deteccoes;")
            cursor.execute("TRUNCATE TABLE incidentes_analisados;")
            cursor.execute("TRUNCATE TABLE dispositivos;")
            cursor.execute("TRUNCATE TABLE enum_nivel_risco;")
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            print("  - Tabelas de dados dinâmicos limpas.")

            # PASSO 1: Garantir e carregar dados base
            if not ensure_risk_levels(cursor):
                raise Exception("Não foi possível garantir os níveis de risco.")
            conn.commit()

            print("\nPASSO 1: Carregando IDs das tabelas de Enum...")
            lookup_tables = {
                "status_disp_ids": "enum_status_dispositivo",
                "status_inc_ids": "enum_status_incidente",
                "risco_ids": "enum_nivel_risco",
                "status_resp_ids": "enum_status_resposta",
                "acao_ids": "enum_acao_executada",
            }
            ids = {}
            for key, table_name in lookup_tables.items():
                ids[key] = get_lookup_ids(cursor, table_name)
                if ids[key] is None or not ids[key]:
                    raise Exception(
                        f"Falha ao carregar ou tabela vazia: '{table_name}'. Popule as tabelas 'enum' primeiro.")

            print("✅ IDs carregados.")

            # PASSO 2: Inserir Dispositivos
            print("\nPASSO 2: Inserindo dispositivos...")
            dispositivos_data = [
                ('Servidor de Aplicação Principal', '192.168.1.10', 'Data Center A',
                 ids['status_disp_ids'].get('Ativo')),
                ('Servidor de Banco de Dados', '192.168.1.15', 'Data Center A', ids['status_disp_ids'].get('Ativo')),
                ('Estação de Trabalho - Finanças', '10.0.5.22', 'Escritório Central',
                 ids['status_disp_ids'].get('Ativo')),
                ('Gateway de Rede', '192.168.0.1', 'Sala de Servidores', ids['status_disp_ids'].get('Ativo')),
                ('Servidor Web - Legado', '192.168.2.50', 'Data Center B', ids['status_disp_ids'].get('Inativo'))
            ]
            dispositivo_ids = {}
            for nome, host, localizacao, status_id in dispositivos_data:
                cursor.execute("INSERT INTO dispositivos (nome, host, localizacao, status_id) VALUES (%s, %s, %s, %s)",
                               (nome, host, localizacao, status_id))
                dispositivo_ids[nome] = cursor.lastrowid
            print(f"  - {len(dispositivo_ids)} dispositivos inseridos.")
            conn.commit()

            # PASSO 3: Gerar e Inserir Incidentes
            print("\nPASSO 3: Gerando e inserindo incidentes analisados...")
            riscos_ponderados = [
                ids['risco_ids']['Crítico'], ids['risco_ids']['Crítico'],
                ids['risco_ids']['Alto'], ids['risco_ids']['Alto'], ids['risco_ids']['Alto'],
                ids['risco_ids']['Médio'], ids['risco_ids']['Médio'],
                ids['risco_ids']['Baixo'],
                ids['risco_ids']['Desconhecido']
            ]
            total_incidentes = 150
            for i in range(total_incidentes):
                risco_id = random.choice(riscos_ponderados)
                disp_nome = random.choice(list(dispositivo_ids.keys()))
                disp_id = dispositivo_ids[disp_nome]
                titulo = f"Incidente Aleatório #{i + 1} ({random.choice(['Acesso Anômalo', 'Tráfego Suspeito', 'Alerta de Malware'])})"
                status_id = random.choice(list(ids['status_inc_ids'].values()))
                data_det = datetime.now() - timedelta(days=random.randint(0, 89), hours=random.randint(0, 23),
                                                      minutes=random.randint(0, 59))

                cursor.execute(
                    """INSERT INTO incidentes_analisados (titulo, status_id, dispositivo_id, nivel_risco_id,
                                                          data_deteccao, resumo_tecnico)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (titulo, status_id, disp_id, risco_id, data_det, "Evento gerado automaticamente para teste.")
                )
            print(f"  - {total_incidentes} incidentes aleatórios inseridos.")
            conn.commit()

            # PASSO 4: Gerar e Inserir Detecções
            print("\nPASSO 4: Gerando e inserindo detecções...")
            total_deteccoes = 200
            tipos_ataque_random = [0, 1, 5, 6, 7, 8, 9, 10, 12, 13]
            start_time = datetime.now()
            for _ in range(total_deteccoes):
                disp_id = random.choice(list(dispositivo_ids.values()))
                ataque_id = random.choice(tipos_ataque_random)
                status_resp_id = random.choice(list(ids['status_resp_ids'].values()))
                dynamic_timestamp = start_time - timedelta(hours=random.randint(0, 72), minutes=random.randint(0, 59))
                relatorio = f'Atividade suspeita de ataque código {ataque_id} detectada no dispositivo.'

                cursor.execute(
                    """INSERT INTO deteccoes (data_deteccao, dispositivo_id, predicao, tipo_ataque_id, relatorio_api,
                                              status_resposta_id)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (dynamic_timestamp, disp_id, ataque_id, ataque_id, relatorio, status_resp_id)
                )
            print(f"  - {total_deteccoes} detecções aleatórias inseridas.")
            conn.commit()

            print("\n🎉 Dados de exemplo inseridos com sucesso em maior volume!")

    except Exception as e:
        print(f"❌ ERRO durante a execução: {e}")
        if 'conn' in locals() and conn.open:
            conn.rollback()
            print("  - Rollback executado.")
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()
            print("\n🔌 Conexão com o banco de dados fechada.")


if __name__ == '__main__':
    # Cria um arquivo .env de exemplo se não existir.
    # Em um ambiente real, este arquivo deve ser criado manualmente e não deve ser versionado.
    if not os.path.exists('.env'):
        print("Arquivo .env não encontrado. Criando um com valores padrão (localhost)...")
        with open('.env', 'w') as f:
            f.write("MYSQL_HOST=localhost\n")
            f.write("MYSQL_USER=root\n")
            f.write("MYSQL_PASSWORD=root\n")
            f.write("MYSQL_DB=qcyberDB\n")

    print(f"Este script irá LIMPAR e REINSERIR dados no banco '{os.getenv('MYSQL_DB', 'qcyberDB')}'")
    resposta = input("ATENÇÃO: DADOS ANTERIORES SERÃO APAGADOS. Deseja continuar? (s/N): ")
    if resposta.lower() in ['s', 'sim']:
        seed_data()
    else:
        print("Operação cancelada.")