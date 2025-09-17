# -*- coding: utf-8 -*-
"""
Script para popular o banco de dados qCyber com dados de exemplo (mock data)
que refletem o fluxo de negócio real (detecção -> análise).
(VERSÃO CORRIGIDA COM VÍNCULO ENTRE DETECÇÕES E INCIDENTES)

Este script:
1. Limpa as tabelas de dados dinâmicos.
2. Insere dispositivos.
3. Para cada detecção criada, decide aleatoriamente se um incidente
   analisado correspondente deve ser gerado.
4. Se um incidente é gerado, o `id` dele é usado para atualizar a detecção
   original, criando o vínculo correto na coluna `incidente_id`.
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
    db_name = os.getenv('MYSQL_DATABASE', 'qcyber_db')

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
            # Checagem de erro robusta
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

            # --- INÍCIO DA LÓGICA CORRIGIDA ---

            # PASSO 3: Gerar Detecções e, para algumas, seus Incidentes correspondentes
            print("\nPASSO 3: Gerando detecções e vinculando incidentes analisados...")
            total_deteccoes = 200
            incidentes_criados = 0
            tipos_ataque_random = [0, 1, 5, 6, 7, 8, 9, 10, 12, 13]
            riscos_ponderados = [
                ids['risco_ids']['Crítico'], ids['risco_ids']['Crítico'],
                ids['risco_ids']['Alto'], ids['risco_ids']['Alto'], ids['risco_ids']['Alto'],
                ids['risco_ids']['Médio'], ids['risco_ids']['Médio'],
                ids['risco_ids']['Baixo']
            ]

            for i in range(total_deteccoes):
                # 1. Cria a detecção
                disp_id = random.choice(list(dispositivo_ids_map.keys()))
                ataque_id = random.choice(tipos_ataque_random)
                status_resp_id = random.choice(list(ids['status_resp_ids'].values()))
                data_det = datetime.now() - timedelta(days=random.randint(0, 89), hours=random.randint(0, 23))
                relatorio = f'Atividade suspeita de ataque código {ataque_id} detectada.'

                # Insere a detecção com incidente_id NULO por padrão
                cursor.execute(
                    """INSERT INTO deteccoes (data_deteccao, dispositivo_id, predicao, tipo_ataque_id, relatorio_api,
                                              status_resposta_id, incidente_id)
                       VALUES (%s, %s, %s, %s, %s, %s, NULL)""",
                    (data_det, disp_id, ataque_id, ataque_id, relatorio, status_resp_id)
                )
                nova_deteccao_id = cursor.lastrowid

                # 2. Decide se gera um incidente para esta detecção (75% de chance)
                if random.random() < 0.75:
                    incidentes_criados += 1

                    # 3. Cria o incidente analisado correspondente
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
            print(f"  - {incidentes_criados} incidentes analisados foram criados e vinculados.")
            conn.commit()

            # --- FIM DA LÓGICA CORRIGIDA ---

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
    # Cria um arquivo .env de exemplo se não existir.
    # Em um ambiente real, este arquivo deve ser criado manualmente e não deve ser versionado.
    if not os.path.exists('.env'):
        print("Arquivo .env não encontrado. Criando um com valores padrão (localhost)...")
        with open('.env', 'w') as f:
            f.write("MYSQL_HOST=localhost\n")
            f.write("MYSQL_USER=root\n")
            f.write("MYSQL_PASSWORD=root\n")
            f.write("MYSQL_DATABASE=qcyber_db\n")

    print(f"Este script irá LIMPAR e REINSERIR dados no banco '{os.getenv('MYSQL_DATABASE', 'qcyber_db')}'")
    resposta = input("ATENÇÃO: DADOS ANTERIORES SERÃO APAGADOS. Deseja continuar? (s/N): ")
    if resposta.lower() in ['s', 'sim']:
        seed_data()
    else:
        print("Operação cancelada.")