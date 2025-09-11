# -*- coding: utf-8 -*-
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional

# --- Schemas de Token ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# --- Schemas de Usuário ---
class UserBase(BaseModel):
    email: EmailStr
    nome: str

class UserCreate(UserBase):
    senha: str

class UserInDB(UserBase):
    id: int
    ativo: bool
    is_admin: bool
    senha_hash: str

    class Config:
        from_attributes = True  # ATUALIZADO de orm_mode


#####################################################
#####################################################
# /schemas.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional


# --- Schemas para Gestão de Dispositivos ---

class DispositivoBase(BaseModel):
    nome: str
    host: str
    localizacao: Optional[str] = None


class DispositivoCreate(DispositivoBase):
    pass


class DispositivoUpdate(BaseModel):
    nome: Optional[str] = None
    localizacao: Optional[str] = None


class Dispositivo(DispositivoBase):
    id: int
    status: str
    data_cadastro: datetime

    class Config:
        from_attributes = True


# --- Schemas para Telas de Histórico e Detalhes ---

class FilterItem(BaseModel):
    id: int
    nome: str

    class Config:
        from_attributes = True


class DetectionHistoryItem(BaseModel):
    id: int
    data_deteccao: datetime
    tipo_ataque: str
    nome_dispositivo: str
    status_resposta: str

    class Config:
        from_attributes = True


class IncidentDetail(DetectionHistoryItem):
    dispositivo_id: int
    resumo_tecnico: Optional[str] = "N/A"
    explicacao_llm: Optional[str] = "Análise detalhada não disponível."
    acoes_recomendadas: Optional[List[str]] = []
    nivel_risco: Optional[str] = "Desconhecido"

    class Config:
        from_attributes = True
#####################################################
#####################################################




class KpisSummary(BaseModel):
    """Métricas (KPIs) principais do dashboard."""
    total_deteccoes: int
    acoes_executadas: int
    dispositivos_ativos: int
    incidentes_criados: int

class AtaquePorTipo(BaseModel):
    """Estrutura para o gráfico de ataques por tipo."""
    nome_ataque: str
    total: int
    descricao: str

class UltimaDeteccao(BaseModel):
    """Estrutura para a lista de últimas detecções."""
    id: int
    data_deteccao: datetime
    nome_dispositivo: str
    tipo_ataque: str
    status_resposta: str


class DeteccoesPorHora(BaseModel):
    hora: datetime
    total: int

class DispositivosAtacados(BaseModel):
    nome_dispositivo: str
    total: int

class IncidentesPorRisco(BaseModel):
    nivel_risco: str
    total: int

class DashboardSummary(BaseModel):
    """Modelo principal que agrupa todos os dados do dashboard."""
    kpis: KpisSummary
    ataques_por_tipo: list[AtaquePorTipo]
    ultimas_deteccoes: list[UltimaDeteccao]
    deteccoes_por_hora: list[DeteccoesPorHora]
    dispositivos_atacados: list[DispositivosAtacados]
    incidentes_por_risco: list[IncidentesPorRisco]



class AcaoDetail(BaseModel):
    """Detalhes de uma ação automática executada."""
    data_acao_executada: datetime
    acao_parametro: Optional[str] = None
    nome_acao: str

class IncidenteDetail(BaseModel):
    """Detalhes de um incidente recente."""
    titulo: str
    nivel_risco: str
    data_criacao: datetime

class DispositivoDetail(BaseModel):
    """Detalhes de um dispositivo ativo."""
    nome: str
    host: str