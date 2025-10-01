# -*- coding: utf-8 -*-
"""
Script para popular o banco de dados qCyber com dados de exemplo (mock data)
que refletem o fluxo de negócio real (detecção -> ação -> análise).

Este script:
1. Limpa as tabelas de dados dinâmicos (deteccoes, incidentes, dispositivos).
2. Insere dispositivos de exemplo.
3. Gera um número definido de detecções.
4. Para uma parte das detecções (ex: 30%), simula uma ação automática executada.
5. Para outra parte (ex: 75%), gera um incidente analisado correspondente.
6. Vincula corretamente as detecções aos seus incidentes.
"""
import os
import pymysql
from dotenv import load_dotenv
from datetime import datetime, timedelta
import random


def get_lookup_ids(cursor, table_name):
    """Busca IDs e nomes de uma tabela de lookup."""
    try:
        cursor.execute(f"SELECT id, nome FROM {table_name}")
        result = cursor.fetchall()
        if not result:
            print(f"⚠️ AVISO: A tabela de lookup '{table_name}' está vazia.")
            return {}
        return {row['nome']: row['id'] for row in result}
    except pymysql.Error as e:
        print(f"❌ ERRO ao buscar dados da tabela '{table_name}': {e}")
        return None


def ensure_risk_levels(cursor):
    """Garante que todos os níveis de risco necessários existam na tabela."""
    print("  - Verificando e inserindo níveis de risco...")
    risk_levels = ["Baixo", "Médio", "Alto", "Crítico", "Desconhecido"]
    try:
        for level in risk_levels:
            cursor.execute("INSERT IGNORE INTO enum_nivel_risco (nome) VALUES (%s)", (level,))
        print("  - Níveis de risco garantidos.")
        return True
    except pymysql.Error as e:
        print(f"❌ ERRO ao inserir níveis de risco: {e}")
        return False


def seed_data():
    """Conecta ao banco e insere os dados de exemplo."""
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
                        f"Falha ao carregar ou tabela enum vazia para '{key}'. Popule as tabelas 'enum' primeiro.")
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
            dispositivo_ids_map = {}
            for nome, host, localizacao, status_id in dispositivos_data:
                cursor.execute("INSERT INTO dispositivos (nome, host, localizacao, status_id) VALUES (%s, %s, %s, %s)",
                               (nome, host, localizacao, status_id))
                dispositivo_ids_map[cursor.lastrowid] = nome
            print(f"  - {len(dispositivo_ids_map)} dispositivos inseridos.")
            conn.commit()

            # PASSO 3: Gerar Detecções e, para algumas, seus Incidentes e Ações correspondentes
            print("\nPASSO 3: Gerando detecções, ações e incidentes...")
            total_deteccoes = 200
            incidentes_criados = 0
            acoes_executadas = 0
            tipos_ataque_random = [0, 1, 5, 6, 7, 8, 9, 10, 12, 13]
            riscos_ponderados = [
                ids['risco_ids']['Crítico'], ids['risco_ids']['Crítico'],
                ids['risco_ids']['Alto'], ids['risco_ids']['Alto'], ids['risco_ids']['Alto'],
                ids['risco_ids']['Médio'], ids['risco_ids']['Médio'],
                ids['risco_ids']['Baixo']
            ]
            acoes_possiveis = list(ids['acao_ids'].values())

            for i in range(total_deteccoes):
                # 1. Prepara dados da detecção
                disp_id = random.choice(list(dispositivo_ids_map.keys()))
                ataque_id = random.choice(tipos_ataque_random)
                status_resp_id = ids['status_resp_ids']['Pendente']
                data_det = datetime.now() - timedelta(days=random.randint(0, 89), hours=random.randint(0, 23))
                relatorio = f'Atividade suspeita de ataque código {ataque_id} detectada.'

                acao_id, acao_param, data_acao = None, None, None

                # --- NOVA LÓGICA PARA SIMULAR AÇÃO ---
                if random.random() < 0.30: # 30% de chance de ter uma ação
                    acoes_executadas += 1
                    acao_id = random.choice(acoes_possiveis)
                    acao_param = f"10.0.{random.randint(1, 254)}.{random.randint(1, 254)}"
                    data_acao = data_det + timedelta(seconds=random.randint(5, 60))
                    status_resp_id = ids['status_resp_ids']['Ação Automática Executada']

                # 2. Insere a detecção com os campos de ação (que podem ser NULL)
                cursor.execute(
                    """INSERT INTO deteccoes (data_deteccao, dispositivo_id, predicao, tipo_ataque_id, relatorio_api,
                                              status_resposta_id, incidente_id, acao_executada_id, acao_parametro, data_acao_executada)
                       VALUES (%s, %s, %s, %s, %s, %s, NULL, %s, %s, %s)""",
                    (data_det, disp_id, ataque_id, ataque_id, relatorio, status_resp_id, acao_id, acao_param, data_acao)
                )
                nova_deteccao_id = cursor.lastrowid

                # 3. Decide se gera um incidente para esta detecção (75% de chance)
                if random.random() < 0.75:
                    incidentes_criados += 1
                    risco_id = random.choice(riscos_ponderados)
                    titulo = f"Análise do Incidente para Detecção #{nova_deteccao_id}"
                    status_id = random.choice(list(ids['status_inc_ids'].values()))

                    cursor.execute(
                        """INSERT INTO incidentes_analisados (titulo, status_id, dispositivo_id, nivel_risco_id,
                                                              data_deteccao, resumo_tecnico)
                           VALUES (%s, %s, %s, %s, %s, %s)""",
                        (titulo, status_id, disp_id, risco_id, data_det,
                         "Evento gerado e analisado automaticamente para teste.")
                    )
                    novo_incidente_id = cursor.lastrowid

                    # 4. ATUALIZA a detecção original com o ID do novo incidente
                    cursor.execute(
                        "UPDATE deteccoes SET incidente_id = %s WHERE id = %s",
                        (novo_incidente_id, nova_deteccao_id)
                    )

            print(f"  - {total_deteccoes} detecções aleatórias inseridas.")
            print(f"  - {acoes_executadas} ações automáticas foram simuladas.")
            print(f"  - {incidentes_criados} incidentes analisados foram criados e vinculados.")
            conn.commit()

            print("\n🎉 Dados de exemplo inseridos com sucesso e com vínculos corretos!")

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
    if not os.path.exists('.env'):
        print("Arquivo .env não encontrado. Criando um com valores padrão (localhost)...")
        with open('.env', 'w') as f:
            f.write("MYSQL_HOST=localhost\n")
            f.write("MYSQL_USER=root\n")
            f.write("MYSQL_PASSWORD=root\n")
            f.write("MYSQL_DB=qcyber_db\n")

    print(f"Este script irá LIMPAR e REINSERIR dados no banco '{os.getenv('MYSQL_DB', 'qcyber_db')}'")
    resposta = input("ATENÇÃO: DADOS ANTERIORES SERÃO APAGADOS. Deseja continuar? (s/N): ")
    if resposta.lower() in ['s', 'sim']:
        seed_data()
    else:
        print("Operação cancelada.")