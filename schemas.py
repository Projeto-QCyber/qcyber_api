# schemas.py
# -*- coding: utf-8 -*-
from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import List, Optional

# =================================
#       AUTENTICAÇÃO E USUÁRIOS
# =================================

class Token(BaseModel):
    """Schema para o token de acesso final."""
    access_token: str
    refresh_token: str
    token_type: str

class TokenData(BaseModel):
    """Schema para os dados decodificados do token."""
    email: Optional[str] = None

class TokenRefresh(BaseModel):
    refresh_token: str

class TokenRevoke(BaseModel):
    token: str # O token que será cancelado (Refresh Token)

class UserBase(BaseModel):
    """Schema base para dados do usuário."""
    email: EmailStr
    nome: str

class UserCreate(UserBase):
    """Schema para a criação de um novo usuário."""
    senha: str

class EmailVerification(BaseModel):
    """Schema para a verificação de e-mail após o registro."""
    email: EmailStr
    code: str

class TwoFactorVerify(BaseModel):
    """Schema para a verificação do código 2FA durante o login."""
    temp_token: str
    code: str

# =================================
#       GESTÃO DE DISPOSITIVOS
# =================================

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

# =================================
#       TELAS DE HISTÓRICO E DETALHES
# =================================

# --- ADICIONADO DE VOLTA ---
class FilterItem(BaseModel):
    """Schema para itens de filtro (ex: lista de dispositivos)."""
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
    acoes_recomendadas: Optional[list[str]] = []
    nivel_risco: Optional[str] = "Desconhecido"

    class Config:
        from_attributes = True

class AcaoDetail(BaseModel):
    """Detalhes de uma ação automática executada."""
    data_acao_executada: datetime
    acao_parametro: Optional[str] = None
    nome_acao: str

class IncidenteDetailPopUp(BaseModel): # Renomeado para evitar conflito
    """Detalhes de um incidente recente para pop-ups ou listas."""
    titulo: str
    nivel_risco: str
    data_criacao: datetime

class DispositivoDetail(BaseModel):
    """Detalhes de um dispositivo ativo."""
    nome: str
    host: str

# =================================
#       DASHBOARD
# =================================

class KpisSummary(BaseModel):
    total_deteccoes: int
    acoes_executadas: int
    dispositivos_ativos: int
    incidentes_criados: int

class AtaquePorTipo(BaseModel):
    nome_ataque: str
    total: int
    descricao: str

class UltimaDeteccao(BaseModel):
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
    kpis: KpisSummary
    ataques_por_tipo: list[AtaquePorTipo]
    ultimas_deteccoes: list[UltimaDeteccao]
    deteccoes_por_hora: list[DeteccoesPorHora]
    dispositivos_atacados: list[DispositivosAtacados]
    incidentes_por_risco: list[IncidentesPorRisco]


# =================================
#       ADMINISTRAÇÃO
# =================================

class UserSummary(BaseModel):
    """Schema para a lista de usuários na tela de admin."""
    id: int
    nome: str
    email: str
    is_admin: bool
    tem_permissao_sistema: bool
    ativo: bool

    class Config:
        from_attributes = True

class UserPermissionUpdate(BaseModel):
    """Schema para atualizar as permissões de um usuário."""
    is_admin: bool
    tem_permissao_sistema: bool

class PasswordResetRequest(BaseModel):
    """Schema para solicitar o reset de senha."""
    email: EmailStr

class PasswordResetPerform(BaseModel):
    """Schema para efetivar a troca de senha com o token."""
    token: str
    nova_senha: str