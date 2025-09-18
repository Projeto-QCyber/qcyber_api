# /history_router.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException
import pymysql
import json
import schemas, security
from database import get_cursor

router = APIRouter(
    prefix="/qcyberapi/history",
    tags=["History"],
    dependencies=[Depends(security.oauth2_scheme)]
)


@router.get("/filter/devices", response_model=List[schemas.FilterItem])
def get_device_filter_list(cursor: pymysql.cursors.DictCursor = Depends(get_cursor)):
    cursor.execute("SELECT id, nome FROM dispositivos WHERE status_id = 1 ORDER BY nome")
    return cursor.fetchall()


@router.get("/filter/threat-types", response_model=List[schemas.FilterItem])
def get_threat_type_filter_list(cursor: pymysql.cursors.DictCursor = Depends(get_cursor)):
    cursor.execute("SELECT id, nome FROM enum_tipo_ataque ORDER BY nome")
    return cursor.fetchall()


@router.get("/by-device/{device_id}", response_model=List[schemas.DetectionHistoryItem])
def get_history_by_device(device_id: int, cursor: pymysql.cursors.DictCursor = Depends(get_cursor)):
    query = """
            SELECT d.id, 
                   d.data_deteccao, 
                   eta.nome  AS tipo_ataque, 
                   disp.nome AS nome_dispositivo, 
                   esr.nome  AS status_resposta
            FROM deteccoes d
                     JOIN dispositivos disp ON d.dispositivo_id = disp.id
                     JOIN enum_tipo_ataque eta ON d.tipo_ataque_id = eta.id
                     JOIN enum_status_resposta esr ON d.status_resposta_id = esr.id
            WHERE d.dispositivo_id = %s 
            ORDER BY d.data_deteccao DESC LIMIT 100; 
            """
    cursor.execute(query, (device_id,))
    return cursor.fetchall()


@router.get("/by-threat/{threat_type_id}", response_model=List[schemas.DetectionHistoryItem])
def get_history_by_threat(threat_type_id: int, cursor: pymysql.cursors.DictCursor = Depends(get_cursor)):
    query = """
            SELECT d.id, 
                   d.data_deteccao, 
                   eta.nome  AS tipo_ataque, 
                   disp.nome AS nome_dispositivo, 
                   esr.nome  AS status_resposta
            FROM deteccoes d
                     JOIN dispositivos disp ON d.dispositivo_id = disp.id
                     JOIN enum_tipo_ataque eta ON d.tipo_ataque_id = eta.id
                     JOIN enum_status_resposta esr ON d.status_resposta_id = esr.id
            WHERE d.tipo_ataque_id = %s 
            ORDER BY d.data_deteccao DESC LIMIT 100; 
            """
    cursor.execute(query, (threat_type_id,))
    return cursor.fetchall()


@router.get("/incident-detail/{detection_id}", response_model=schemas.IncidentDetail)
def get_incident_detail(detection_id: int, cursor: pymysql.cursors.DictCursor = Depends(get_cursor)):
    query = """
            SELECT d.id, 
                 disp.id as dispositivo_id,
                   d.data_deteccao, 
                   eta.nome  AS tipo_ataque, 
                   disp.nome AS nome_dispositivo, 
                   esr.nome  AS status_resposta, 
                   ia.resumo_tecnico, 
                   ia.explicacao_llm, 
                   ia.acoes_recomendadas, 
                   enr.nome  as nivel_risco
            FROM deteccoes d
                     JOIN dispositivos disp ON d.dispositivo_id = disp.id
                     JOIN enum_tipo_ataque eta ON d.tipo_ataque_id = eta.id
                     JOIN enum_status_resposta esr ON d.status_resposta_id = esr.id
                     LEFT JOIN incidentes_analisados ia 
                               ON d.incidente_id = ia.id
                     LEFT JOIN enum_nivel_risco enr ON ia.nivel_risco_id = enr.id
            WHERE d.id = %s; 
            """
    cursor.execute(query, (detection_id,))
    result = cursor.fetchone()
    if not result:
        raise HTTPException(status_code=404, detail="Detecção não encontrada.")

    # Converte a string de ações para uma lista, se necessário
    raw_actions = result.get("acoes_recomendadas")
    if raw_actions and isinstance(raw_actions, str):
        try:
            # Tenta decodificar como JSON primeiro
            result["acoes_recomendadas"] = json.loads(raw_actions)
        except json.JSONDecodeError:
            # Se falhar, faz split por um delimitador
            result["acoes_recomendadas"] = [act.strip() for act in raw_actions.split('•') if act.strip()]

    return result