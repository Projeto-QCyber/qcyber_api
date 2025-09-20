# api_simulada.py
import os
import json
import random
import pymysql
from datetime import datetime
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# --- CONFIGURAÇÃO DA APLICAÇÃO FLASK ---
app = Flask(__name__)


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


# --- LÓGICA DE SIMULAÇÃO DE ANÁLISE DETALHADA ---
def _gerar_analise_detalhada(tipo_ataque_id, tipo_ataque_nome):
    """
    Simula a análise detalhada de um agente de IA.
    Retorna um dicionário com resumo, explicação do LLM, risco e ações recomendadas.
    """
    niveis_risco = {'Baixo': 1, 'Médio': 2, 'Alto': 3, 'Crítico': 4}

    # Dicionário de análises pré-definidas por tipo de ataque
    analises_predefinidas = {
        10: {  # SQL Injection
            "resumo": "Foi detectada uma tentativa de injeção de SQL. Padrões maliciosos foram encontrados nos parâmetros de entrada da aplicação, visando manipular queries no banco de dados.",
            "explicacao_llm": "O invasor tentou 'enganar' o banco de dados inserindo comandos maliciosos em campos de texto, como um formulário de login. É como se, em vez de apenas dar seu nome, você desse seu nome e uma ordem para o sistema entregar todos os dados dos outros usuários.",
            # <-- ALTERADO
            "risco_id": niveis_risco['Crítico'],
            "acoes": [
                "Bloquear o endereço IP de origem no firewall imediatamente.",
                "Validar e parametrizar todas as consultas SQL na aplicação (prepared statements).",
                "Revisar logs do banco de dados para identificar qualquer acesso ou modificação não autorizada."
            ]
        },
        3: {  # DDoS_TCP
            "resumo": "Identificado um volume anômalo de pacotes TCP SYN, característico de um ataque de negação de serviço distribuído (DDoS). O objetivo é esgotar os recursos do servidor.",
            "explicacao_llm": "O sistema foi inundado com pedidos de conexão falsos, como um restaurante que recebe milhares de chamadas de pessoas que pedem para esperar na linha mas nunca fazem o pedido. Isso ocupa todas as linhas e impede que clientes reais sejam atendidos.",
            # <-- ALTERADO
            "risco_id": niveis_risco['Alto'],
            "acoes": [
                "Ativar regras de rate limiting para o IP de origem.",
                "Utilizar serviços de mitigação de DDoS na nuvem para filtrar o tráfego malicioso.",
                "Aumentar temporariamente a capacidade do pool de conexões do servidor."
            ]
        },
        # Adicione outros tipos de ataque aqui...
    }

    # Se o ataque não estiver pré-definido, usa um modelo genérico
    analise_default = {
        "resumo": f"Uma atividade suspeita classificada como '{tipo_ataque_nome}' foi detectada. Recomenda-se uma investigação manual para determinar a natureza e o impacto da ameaça.",
        "explicacao_llm": f"O sistema identificou um padrão de comportamento que não é comum para o tráfego normal e o classificou como '{tipo_ataque_nome}'. A natureza exata da ameaça ainda precisa ser confirmada, mas ela se desvia do padrão esperado de operações seguras.",
        # <-- ALTERADO
        "risco_id": niveis_risco['Médio'],
        "acoes": [
            "Isolar o host afetado da rede para evitar a propagação.",
            "Coletar e analisar os logs do dispositivo no momento da detecção.",
            "Verificar se há processos ou conexões de rede incomuns no dispositivo."
        ]
    }

    return analises_predefinidas.get(tipo_ataque_id, analise_default)


# --- ROTA PRINCIPAL DA API DE ANÁLISE ---
@app.route('/analisar', methods=['POST'])
def analisar_dados():
    data = request.json
    if not data or 'device_id' not in data or 'features' not in data:
        return jsonify({"erro": "Payload inválido"}), 400

    device_id = data['device_id']

    if random.random() < 0.8:
        predicao = random.randint(0, 13)
    else:
        predicao = 99

    conn = get_db_connection()
    if not conn:
        return jsonify({"erro": "Não foi possível conectar ao banco de dados"}), 500

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT nome FROM enum_tipo_ataque WHERE id = %s", (predicao,))
            tipo_ataque_nome = cursor.fetchone()['nome']

            sql_deteccao = """
                           INSERT INTO deteccoes (dispositivo_id, predicao, tipo_ataque_id, relatorio_api, \
                                                  status_resposta_id)
                           VALUES (%s, %s, %s, %s, %s) \
                           """
            cursor.execute(sql_deteccao,
                           (device_id, predicao, predicao, f"Simulação: Detectado '{tipo_ataque_nome}'", 1))
            deteccao_id = cursor.lastrowid

            incidente_id = None
            if predicao != 99:
                analise = _gerar_analise_detalhada(predicao, tipo_ataque_nome)

                sql_incidente = """
                                INSERT INTO incidentes_analisados
                                (titulo, status_id, dispositivo_id, nivel_risco_id, data_deteccao, resumo_tecnico, \
                                 explicacao_llm, acoes_recomendadas)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s) \
                                """  # <-- ALTERADO (adicionado explicacao_llm)

                cursor.execute(sql_incidente, (
                    f"Incidente Automático: {tipo_ataque_nome} no dispositivo {device_id}",
                    1,
                    device_id,
                    analise['risco_id'],
                    datetime.now(),
                    analise['resumo'],
                    analise['explicacao_llm'],  # <-- ALTERADO (adicionado o novo campo)
                    json.dumps(analise['acoes'])
                ))
                incidente_id = cursor.lastrowid

                sql_update_deteccao = "UPDATE deteccoes SET incidente_id = %s, status_resposta_id = %s WHERE id = %s"
                cursor.execute(sql_update_deteccao, (incidente_id, 3, deteccao_id))

            conn.commit()

        print(f"✅ Detecção registrada com ID {deteccao_id}. Incidente ID: {incidente_id or 'N/A'}")
        return jsonify({
            "mensagem": "Detecção analisada e registrada com sucesso!",
            "deteccao_id": deteccao_id,
            "incidente_id": incidente_id,
            "tipo_ataque_detectado": tipo_ataque_nome
        }), 201

    except Exception as e:
        conn.rollback()
        print(f"❌ ERRO ao processar detecção: {e}")
        return jsonify({"erro": "Ocorreu um erro interno"}), 500
    finally:
        conn.close()


if __name__ == '__main__':
    print("🚀 API Simulada (v2) iniciada. Aguardando requisições em http://0.0.0.0:5000/analisar")
    app.run(host='0.0.0.0', port=5000, debug=True)