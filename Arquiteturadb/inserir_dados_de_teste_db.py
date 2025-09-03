# -*- coding: utf-8 -*-
"""
Script para popular o banco de dados qCyber com dados de exemplo (mock data).
(VERSÃO FINAL NORMALIZADA)

Este script insere dados realistas nas tabelas, respeitando a estrutura
final com todas as tabelas de lookup (enum_*).
"""
import os
import pymysql
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta
import random


def get_lookup_ids(cursor, table_name):
    """
    Busca IDs e nomes de uma tabela de lookup e retorna um dicionário
    para fácil acesso. Ex: {'Ativo': 1, 'Inativo': 2}
    """
    cursor.execute(f"SELECT id, nome FROM {table_name}")
    return {row['nome']: row['id'] for row in cursor.fetchall()}


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
        print("✅ Conectado ao banco de dados com sucesso!")
    except Exception as e:
        print(f"❌ ERRO: Falha ao conectar ao banco de dados: {e}")
        return

    try:
        with conn.cursor() as cursor:
            # PASSO 0: Carregar IDs das tabelas de lookup
            print("\nPASSO 0: Carregando IDs das tabelas de Enum...")
            status_disp_ids = get_lookup_ids(cursor, 'enum_status_dispositivo')
            status_inc_ids = get_lookup_ids(cursor, 'enum_status_incidente')
            risco_ids = get_lookup_ids(cursor, 'enum_nivel_risco')
            status_resp_ids = get_lookup_ids(cursor, 'enum_status_resposta')
            acao_ids = get_lookup_ids(cursor, 'enum_acao_executada')

            label_map = {
                'Backdoor': 0, 'DDoS_HTTP': 1, 'DDoS_ICMP': 2, 'DDoS_TCP': 3, 'DDoS_UDP': 4,
                'Fingerprinting': 5, 'MITM': 6, 'Password': 7, 'Port_Scanning': 8, 'Ransomware': 9,
                'SQL_injection': 10, 'Uploading': 11, 'Vulnerability_scanner': 12, 'XSS': 13, 'Normal': 99
            }
            print("✅ IDs carregados.")

            print("\nPASSO 1: Inserindo dispositivos...")
            dispositivos = [
                ('Servidor de Aplicação Principal', '192.168.1.10', 'Data Center A', status_disp_ids.get('Ativo')),
                ('Servidor de Banco de Dados', '192.168.1.15', 'Data Center A', status_disp_ids.get('Ativo')),
                ('Estação de Trabalho - Finanças', '10.0.5.22', 'Escritório Central', status_disp_ids.get('Ativo')),
                ('Gateway de Rede', '192.168.0.1', 'Sala de Servidores', status_disp_ids.get('Ativo'))
                # Alterado para Ativo para gerar dados
            ]
            dispositivo_ids = {}
            for nome, host, localizacao, status_id in dispositivos:
                cursor.execute("SELECT id FROM dispositivos WHERE host = %s", (host,))
                result = cursor.fetchone()
                if not result:
                    cursor.execute(
                        "INSERT INTO dispositivos (nome, host, localizacao, status_id) VALUES (%s, %s, %s, %s)",
                        (nome, host, localizacao, status_id)
                    )
                    dispositivo_ids[nome] = cursor.lastrowid
                    print(f"  - Dispositivo '{nome}' inserido.")
                else:
                    dispositivo_ids[nome] = result['id']
            conn.commit()

            print("\nPASSO 2: Inserindo incidentes analisados...")
            incidentes = [
                ('Tentativa de Acesso SSH Anômala', status_inc_ids.get('Resolvido'),
                 dispositivo_ids.get('Servidor de Aplicação Principal'), risco_ids.get('Crítico'),
                 datetime.now() - timedelta(days=2), 'Tentativas de login falhas a partir do IP 189.45.3.1',
                 'O LLM identificou o IP como malicioso.', json.dumps(["Bloquear IP", "Rotacionar credenciais"])),
                ('Tráfego Incomum para Porta de Banco de Dados', status_inc_ids.get('Em Análise'),
                 dispositivo_ids.get('Servidor de Banco de Dados'), risco_ids.get('Alto'),
                 datetime.now() - timedelta(days=1), 'Múltiplas conexões na porta 1433 de fontes não usuais.',
                 'Pode ser uma tentativa de brute force.', json.dumps(["Analisar logs do firewall"]))
            ]
            incidente_ids = {}
            for titulo, status_id, disp_id, risco_id, data_det, resumo, llm, acoes in incidentes:
                cursor.execute("SELECT id FROM incidentes_analisados WHERE titulo = %s", (titulo,))
                result = cursor.fetchone()
                if not result:
                    cursor.execute(
                        """INSERT INTO incidentes_analisados (titulo, status_id, dispositivo_id, nivel_risco_id,
                                                              data_deteccao, resumo_tecnico, explicacao_llm,
                                                              acoes_recomendadas)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                        (titulo, status_id, disp_id, risco_id, data_det, resumo, llm, acoes)
                    )
                    incidente_ids[titulo] = cursor.lastrowid
                    print(f"  - Incidente '{titulo}' inserido.")
                else:
                    incidente_ids[titulo] = result['id']
            conn.commit()

            print("\nPASSO 3: Gerando e inserindo detecções com timestamps dinâmicos...")
            deteccoes = [
                (dispositivo_ids.get('Servidor de Aplicação Principal'), 7, label_map['Password'],
                 'Múltiplas tentativas...', status_resp_ids.get('Análise Manual Necessária'), None, None, None,
                 incidente_ids.get('Tentativa de Acesso SSH Anômala')),
                (dispositivo_ids.get('Gateway de Rede'), 0, label_map['Backdoor'], 'Dispositivo contactando C2...',
                 status_resp_ids.get('Ação Automática Executada'), acao_ids.get('BLOCK_IP'), '203.11.5.88',
                 datetime.now() - timedelta(minutes=10), None),
                (dispositivo_ids.get('Estação de Trabalho - Finanças'), 9, label_map['Ransomware'],
                 'Processo suspeito de criptografia...', status_resp_ids.get('Ação Automática Executada'),
                 acao_ids.get('ISOLATE_HOST'), '10.0.5.22', datetime.now() - timedelta(hours=1), None),
                (dispositivo_ids.get('Estação de Trabalho - Finanças'), 13, label_map['XSS'],
                 'Usuário acessou URL phishing.', status_resp_ids.get('Pendente'), None, None, None, None),
                (dispositivo_ids.get('Servidor de Banco de Dados'), 10, label_map['SQL_injection'],
                 'Query com padrões suspeitos.', status_resp_ids.get('Pendente'), None, None, None, None),
                (dispositivo_ids.get('Servidor de Aplicação Principal'), 99, label_map['Normal'],
                 'Tráfego HTTP normal.', status_resp_ids.get('Ignorado'), None, None, None, None),
            ]

            tipos_ataque_random = [0, 1, 5, 8, 9, 10, 12, 13]
            # Aumentado para 50 para ter mais dados para os gráficos
            for _ in range(50):
                disp_nome = random.choice(list(dispositivo_ids.keys()))
                disp_id = dispositivo_ids[disp_nome]
                ataque_id = random.choice(tipos_ataque_random)
                deteccoes.append(
                    (disp_id, ataque_id, ataque_id, f'Atividade suspeita de ataque código {ataque_id} detectada.',
                     status_resp_ids.get('Pendente'), None, None, None, None))

            cursor.execute("TRUNCATE TABLE deteccoes")
            print("  - Tabela 'deteccoes' limpa.")

            # --- LÓGICA DE INSERÇÃO ATUALIZADA ---
            start_time = datetime.now() - timedelta(days=7)

            # Usamos enumerate para ter um contador (i) para espalhar o tempo
            for i, (disp_id, pred, tipo_id, relatorio, status_id, acao_id, acao_param, data_acao, inc_id) in enumerate(
                    deteccoes):
                # Calcula um timestamp dinâmico para cada registro
                dynamic_timestamp = start_time + timedelta(hours=i * 2, minutes=random.randint(0, 120))

                # Adicionamos a coluna 'data_deteccao' ao INSERT
                cursor.execute(
                    """INSERT INTO deteccoes (data_deteccao, dispositivo_id, predicao, tipo_ataque_id, relatorio_api,
                                              status_resposta_id, acao_executada_id, acao_parametro,
                                              data_acao_executada, incidente_id)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (dynamic_timestamp, disp_id, pred, tipo_id, relatorio, status_id, acao_id, acao_param, data_acao,
                     inc_id)
                )
            print(f"  - {len(deteccoes)} novas detecções inseridas com timestamps distribuídos.")

            conn.commit()
            print("\n🎉 Dados de exemplo inseridos com sucesso!")

    except Exception as e:
        print(f"❌ ERRO durante a inserção de dados: {e}")
        conn.rollback()
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    print("Este script irá inserir dados de exemplo no banco 'qcyberDB' (versão normalizada).")
    resposta = input("Deseja continuar? (s/N): ")
    if resposta.lower() in ['s', 'sim', 'y', 'yes']:
        seed_data()
    else:
        print("Operação cancelada.")