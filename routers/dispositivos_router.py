# /dispositivos_router.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
import pymysql
import schemas, security
from database import get_cursor

router = APIRouter(
    prefix="/api/dispositivos",
    tags=["Dispositivos"],
    dependencies=[Depends(security.oauth2_scheme)]
)


@router.get("/", response_model=List[schemas.Dispositivo])
def read_dispositivos(cursor: pymysql.cursors.DictCursor = Depends(get_cursor)):
    """Busca e retorna a lista de todos os dispositivos cadastrados."""
    query = """
            SELECT d.id, d.nome, d.host, d.localizacao, esd.nome as status, d.data_cadastro
            FROM dispositivos d
                     LEFT JOIN enum_status_dispositivo esd ON d.status_id = esd.id
            ORDER BY d.nome ASC 
            """
    cursor.execute(query)
    return cursor.fetchall()


@router.post("/", response_model=schemas.Dispositivo, status_code=status.HTTP_201_CREATED)
def create_dispositivo(
        dispositivo: schemas.DispositivoCreate,
        cursor: pymysql.cursors.DictCursor = Depends(get_cursor)
):
    """Cadastra um novo dispositivo no banco de dados."""
    try:
        cursor.execute("SELECT id FROM dispositivos WHERE host = %s", (dispositivo.host,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Este host já está cadastrado."
            )

        sql = "INSERT INTO dispositivos (nome, host, localizacao, status_id) VALUES (%s, %s, %s, 1)"  # Default status 'Ativo'
        cursor.execute(sql, (dispositivo.nome, dispositivo.host, dispositivo.localizacao))
        new_id = cursor.lastrowid

        cursor.execute("""
                       SELECT d.id, d.nome, d.host, d.localizacao, esd.nome as status, d.data_cadastro
                       FROM dispositivos d
                                JOIN enum_status_dispositivo esd ON d.status_id = esd.id
                       WHERE d.id = %s
                       """, (new_id,))
        new_dispositivo = cursor.fetchone()

        cursor.connection.commit()
        return new_dispositivo
    except pymysql.MySQLError as e:
        cursor.connection.rollback()
        raise HTTPException(status_code=500, detail=f"Erro de banco de dados: {e}")
    except Exception as e:
        cursor.connection.rollback()
        raise HTTPException(status_code=500, detail=f"Erro interno: {e}")


@router.put("/{device_id}", response_model=schemas.Dispositivo)
def update_dispositivo(
        device_id: int,
        dispositivo_update: schemas.DispositivoUpdate,
        cursor: pymysql.cursors.DictCursor = Depends(get_cursor)
):
    """Atualiza as informações de um dispositivo (nome e/ou localização)."""
    try:
        cursor.execute("SELECT id FROM dispositivos WHERE id = %s", (device_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Dispositivo não encontrado.")

        update_fields = dispositivo_update.dict(exclude_unset=True)
        if not update_fields:
            raise HTTPException(status_code=400, detail="Nenhum campo para atualizar.")

        set_clause = ", ".join([f"{key} = %s" for key in update_fields.keys()])
        sql = f"UPDATE dispositivos SET {set_clause} WHERE id = %s"

        values = list(update_fields.values()) + [device_id]
        cursor.execute(sql, tuple(values))

        cursor.execute("""
                       SELECT d.id, d.nome, d.host, d.localizacao, esd.nome as status, d.data_cadastro
                       FROM dispositivos d
                                JOIN enum_status_dispositivo esd ON d.status_id = esd.id
                       WHERE d.id = %s
                       """, (device_id,))
        updated_dispositivo = cursor.fetchone()

        cursor.connection.commit()
        return updated_dispositivo
    except pymysql.MySQLError as e:
        cursor.connection.rollback()
        raise HTTPException(status_code=500, detail=f"Erro de banco de dados: {e}")