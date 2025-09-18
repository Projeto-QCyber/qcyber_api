# /routers/admin_router.py

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
import pymysql

import schemas
import security
from database import get_cursor

router = APIRouter(
    prefix="/qcyberapi/admin",
    tags=["Administração"],
    dependencies=[Depends(security.get_current_admin_user)] # Protege todas as rotas neste arquivo
)

# --- Gestão de Usuários ---

@router.get("/users", response_model=List[schemas.UserSummary])
def get_user_list(search: str = "", cursor: pymysql.cursors.DictCursor = Depends(get_cursor)):
    """Lista todos os usuários, com opção de busca por nome ou email."""
    try:
        # A busca usa o operador LIKE para encontrar correspondências parciais
        query = """
            SELECT id, nome, email, is_admin, tem_permissao_sistema, ativo
            FROM usuarios
            WHERE nome LIKE %s OR email LIKE %s
            ORDER BY nome
        """
        search_term = f"%{search}%"
        cursor.execute(query, (search_term, search_term))
        users = cursor.fetchall()
        return users
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def update_user_permissions(
    user_id: int,
    permissions: schemas.UserPermissionUpdate,
    cursor: pymysql.cursors.DictCursor = Depends(get_cursor)
):
    """Atualiza as permissões de um usuário específico."""
    try:
        query = "UPDATE usuarios SET is_admin = %s, tem_permissao_sistema = %s WHERE id = %s"
        cursor.execute(query, (permissions.is_admin, permissions.tem_permissao_sistema, user_id))
        cursor.connection.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")
        return
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


# --- Parâmetros do Sistema ---

@router.get("/settings", response_model=dict)
def get_system_settings(cursor: pymysql.cursors.DictCursor = Depends(get_cursor)):
    """Retorna todas as configurações do sistema da tabela 'configuracoes'."""
    try:
        cursor.execute("SELECT chave, valor FROM configuracoes")
        settings_list = cursor.fetchall()
        # Converte a lista de dicionários para um único dicionário (chave: valor)
        settings_dict = {item['chave']: item['valor'] for item in settings_list}
        return settings_dict
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.put("/settings", status_code=status.HTTP_204_NO_CONTENT)
def update_system_settings(
    settings: schemas.SettingsUpdate,
    cursor: pymysql.cursors.DictCursor = Depends(get_cursor)
):
    """Atualiza múltiplos parâmetros do sistema em uma única transação."""
    try:
        # Usamos executemany para atualizar todas as chaves de uma vez
        update_data = [(v, k) for k, v in settings.model_dump().items()]
        query = "UPDATE configuracoes SET valor = %s WHERE chave = %s"
        cursor.executemany(query, update_data)
        cursor.connection.commit()
        return
    except Exception as e:
        cursor.connection.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/users/{user_id}/reset-password", status_code=status.HTTP_200_OK)
def admin_reset_user_password(
    user_id: int,
    cursor: pymysql.cursors.DictCursor = Depends(get_cursor)
):
    """
    (Admin) Gera uma nova senha temporária para um usuário e a envia por e-mail.
    """
    # Busca o e-mail do usuário
    cursor.execute("SELECT email, nome FROM usuarios WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado")

    # Gera uma senha temporária segura
    temp_password = security.generate_secure_code(length=10)
    hashed_password = security.get_password_hash(temp_password)

    # Atualiza a senha no banco
    cursor.execute("UPDATE usuarios SET senha_hash = %s WHERE id = %s", (hashed_password, user_id))

    # Envia o e-mail (você precisará criar um template de e-mail para isso)
    # Exemplo simples:
    subject = "Sua senha na Plataforma qCyber foi redefinida"
    email_body = f"""
    Olá {user['nome']},<br><br>
    Sua senha foi redefinida por um administrador.<br>
    Sua nova senha temporária é: <b>{temp_password}</b><br><br>
    Recomendamos que você faça login e altere esta senha o mais rápido possível.
    """
    # (A função de enviar e-mail precisa ser adaptada para aceitar um corpo HTML)
    #email_service.send_email_html(user['email'], subject, email_body, cursor) # Supõe que criaremos essa função

    cursor.connection.commit()
    return {"message": "Senha temporária enviada para o e-mail do usuário."}