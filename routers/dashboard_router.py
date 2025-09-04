# -*- coding: utf-8 -*-
from fastapi import APIRouter, Depends, Query
import pymysql
from datetime import datetime, timedelta
from typing import Optional

import schemas
from database import get_cursor

from typing import List

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)

# Em routers/dashboard_router.py

@router.get("/summary", response_model=schemas.DashboardSummary)
def get_dashboard_summary(
    cursor: pymysql.cursors.DictCursor = Depends(get_cursor),
    start_date: Optional[datetime] = Query(None, description="Data de início (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Data de fim (ISO format)")
):
    """
    Retorna um resumo de dados para o dashboard principal.
    Aceita um intervalo de datas opcional. Por padrão, retorna as últimas 24 horas.
    """
    if start_date is None or end_date is None:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)

    try:
        # Query para os KPIs
        kpi_query = """
        SELECT
            (SELECT COUNT(*) FROM deteccoes WHERE data_deteccao BETWEEN %s AND %s) AS total_deteccoes,
            (SELECT COUNT(*) FROM deteccoes WHERE status_resposta_id = 2 AND data_deteccao BETWEEN %s AND %s) AS acoes_executadas,
            (SELECT COUNT(*) FROM dispositivos WHERE status_id = 1) AS dispositivos_ativos,
            (SELECT COUNT(*) FROM incidentes_analisados WHERE data_criacao BETWEEN %s AND %s) AS incidentes_criados;
        """
        cursor.execute(kpi_query, (start_date, end_date, start_date, end_date, start_date, end_date))
        kpis_result = cursor.fetchone()

        # Query para o gráfico de ataques por tipo
        ataques_query = """
        SELECT eta.nome AS nome_ataque, eta.descricao AS descricao, COUNT(d.id) AS total
        FROM deteccoes d JOIN enum_tipo_ataque eta ON d.tipo_ataque_id = eta.id
        WHERE d.data_deteccao BETWEEN %s AND %s
        GROUP BY eta.nome, eta.descricao ORDER BY total DESC LIMIT 5;
        """
        cursor.execute(ataques_query, (start_date, end_date))
        ataques_result = cursor.fetchall()

        # Query para a tabela de últimas detecções
        deteccoes_query = """
        SELECT d.id, d.data_deteccao, disp.nome AS nome_dispositivo, eta.nome AS tipo_ataque, esr.nome AS status_resposta
        FROM deteccoes d
        JOIN dispositivos disp ON d.dispositivo_id = disp.id
        JOIN enum_tipo_ataque eta ON d.tipo_ataque_id = eta.id
        JOIN enum_status_resposta esr ON d.status_resposta_id = esr.id
        WHERE d.data_deteccao BETWEEN %s AND %s
        ORDER BY d.data_deteccao DESC LIMIT 10;
        """
        cursor.execute(deteccoes_query, (start_date, end_date))
        deteccoes_result = cursor.fetchall()

        # Query para o gráfico de linha (deteccões ao longo do tempo)
        time_format = "%%Y-%%m-%%d" if (end_date - start_date).days > 1 else "%%Y-%%m-%%d %%H:00:00"
        deteccoes_tempo_query = f"""
        SELECT DATE_FORMAT(data_deteccao, '{time_format}') AS hora, COUNT(id) AS total
        FROM deteccoes WHERE data_deteccao BETWEEN %s AND %s
        GROUP BY hora ORDER BY hora ASC;
        """
        cursor.execute(deteccoes_tempo_query, (start_date, end_date))
        deteccoes_tempo_result = cursor.fetchall()

        # Query para o gráfico de barras (dispositivos mais atacados)
        dispositivos_query = """
        SELECT disp.nome AS nome_dispositivo, COUNT(d.id) AS total
        FROM deteccoes d JOIN dispositivos disp ON d.dispositivo_id = disp.id
        WHERE d.data_deteccao BETWEEN %s AND %s
        GROUP BY nome_dispositivo ORDER BY total DESC LIMIT 5;
        """
        cursor.execute(dispositivos_query, (start_date, end_date))
        dispositivos_result = cursor.fetchall()

        # Query para o gráfico de colunas (incidentes por risco)
        risco_query = """
        SELECT enr.nome as nivel_risco, COUNT(ia.id) as total
        FROM incidentes_analisados ia JOIN enum_nivel_risco enr ON ia.nivel_risco_id = enr.id
        WHERE ia.data_criacao BETWEEN %s AND %s
        GROUP BY nivel_risco ORDER BY enr.id;
        """
        cursor.execute(risco_query, (start_date, end_date))
        risco_result = cursor.fetchall()

        # Monta o objeto de resposta final
        dashboard_data = schemas.DashboardSummary(
            kpis=schemas.KpisSummary(**kpis_result),
            ataques_por_tipo=[schemas.AtaquePorTipo(**row) for row in ataques_result],
            ultimas_deteccoes=[schemas.UltimaDeteccao(**row) for row in deteccoes_result],
            deteccoes_por_hora=[schemas.DeteccoesPorHora(**row) for row in deteccoes_tempo_result],
            dispositivos_atacados=[schemas.DispositivosAtacados(**row) for row in dispositivos_result],
            incidentes_por_risco=[schemas.IncidentesPorRisco(**row) for row in risco_result]
        )

        # # >>> ADICIONE ESTAS LINHAS PARA DEBUG <<<
        # print("\n" + "=" * 20 + " DADOS ENVIADOS PARA O FRONTEND " + "=" * 20)
        # # Usamos .model_dump() para ver a representação em dicionário dos dados
        # # Isso ajuda a garantir que a conversão Pydantic -> JSON está correta
        # print(dashboard_data.model_dump())
        # print("=" * 63 + "\n")
        # # >>> FIM DO DEBUG <<<

        # Monta o objeto de resposta final
        return dashboard_data

    except Exception as e:
        print(f"Erro ao buscar dados do dashboard: {e}")
        # CORREÇÃO DEFINITIVA: Retorna um objeto completo com valores padrão para todos os campos
        return schemas.DashboardSummary(
            kpis=schemas.KpisSummary(total_deteccoes=0, acoes_executadas=0, dispositivos_ativos=0, incidentes_criados=0),
            ataques_por_tipo=[],
            ultimas_deteccoes=[],
            deteccoes_por_hora=[],
            dispositivos_atacados=[],
            incidentes_por_risco=[]
        )


@router.get("/details/deteccoes", response_model=List[schemas.UltimaDeteccao])
def get_deteccoes_details(
    cursor: pymysql.cursors.DictCursor = Depends(get_cursor),
    start_date: Optional[datetime] = Query(None, description="Data de início (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="Data de fim (ISO format)")
):
    """
    Retorna uma lista detalhada das últimas 20 detecções para o modal de KPI.
    """
    if start_date is None or end_date is None:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=1)

    try:
        deteccoes_query = """
        SELECT
            d.id,
            d.data_deteccao,
            disp.nome AS nome_dispositivo,
            eta.nome AS tipo_ataque,
            esr.nome AS status_resposta
        FROM deteccoes d
        JOIN dispositivos disp ON d.dispositivo_id = disp.id
        JOIN enum_tipo_ataque eta ON d.tipo_ataque_id = eta.id
        JOIN enum_status_resposta esr ON d.status_resposta_id = esr.id
        WHERE d.data_deteccao BETWEEN %s AND %s
        ORDER BY d.data_deteccao DESC
        LIMIT 20;
        """
        cursor.execute(deteccoes_query, (start_date, end_date))
        return cursor.fetchall()

    except Exception as e:
        print(f"Erro ao buscar detalhes das detecções: {e}")
        return []


@router.get("/details/acoes", response_model=List[schemas.AcaoDetail])
def get_acoes_details(
    cursor: pymysql.cursors.DictCursor = Depends(get_cursor),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    """Retorna as últimas 20 ações automáticas executadas."""
    if start_date is None or end_date is None:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30) # Busca em um período maior
    try:
        query = """
        SELECT d.data_acao_executada, d.acao_parametro, ea.nome as nome_acao
        FROM deteccoes d
        JOIN enum_acao_executada ea ON d.acao_executada_id = ea.id
        WHERE d.acao_executada_id IS NOT NULL AND d.data_acao_executada BETWEEN %s AND %s
        ORDER BY d.data_acao_executada DESC
        LIMIT 20;
        """
        cursor.execute(query, (start_date, end_date))
        return cursor.fetchall()
    except Exception as e:
        print(f"Erro ao buscar detalhes das ações: {e}")
        return []

@router.get("/details/incidentes", response_model=List[schemas.IncidenteDetail])
def get_incidentes_details(
    cursor: pymysql.cursors.DictCursor = Depends(get_cursor),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None)
):
    """Retorna os últimos 20 incidentes criados."""
    if start_date is None or end_date is None:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
    try:
        query = """
        SELECT ia.titulo, enr.nome as nivel_risco, ia.data_criacao
        FROM incidentes_analisados ia
        JOIN enum_nivel_risco enr ON ia.nivel_risco_id = enr.id
        WHERE ia.data_criacao BETWEEN %s AND %s
        ORDER BY ia.data_criacao DESC
        LIMIT 20;
        """
        cursor.execute(query, (start_date, end_date))
        return cursor.fetchall()
    except Exception as e:
        print(f"Erro ao buscar detalhes dos incidentes: {e}")
        return []

@router.get("/details/dispositivos", response_model=List[schemas.DispositivoDetail])
def get_dispositivos_details(cursor: pymysql.cursors.DictCursor = Depends(get_cursor)):
    """Retorna a lista de dispositivos com status 'Ativo'."""
    try:
        # O status_id=1 corresponde a 'Ativo' no seu script de criação do DB
        query = "SELECT nome, host FROM dispositivos WHERE status_id = 1 ORDER BY nome;"
        cursor.execute(query)
        return cursor.fetchall()
    except Exception as e:
        print(f"Erro ao buscar detalhes dos dispositivos: {e}")
        return []