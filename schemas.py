# -*- coding: utf-8 -*-
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

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

# --- Schemas de Dispositivo ---
class DispositivoBase(BaseModel):
    nome: str
    host: str
    localizacao: Optional[str] = None

class DispositivoCreate(DispositivoBase):
    pass

class Dispositivo(DispositivoBase):
    id: int
    status: str
    data_cadastro: datetime

    class Config:
        from_attributes = True # ATUALIZADO de orm_mode


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