# /report_router.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
import pymysql
import io
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
import schemas, security
from database import get_cursor

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph
from reportlab.lib.enums import TA_JUSTIFY

router = APIRouter(
    prefix="/report",
    tags=["Reports"],
    dependencies=[Depends(security.oauth2_scheme)]
)


class PDFGenerator:
    def __init__(self, buffer, pagesize):
        self.buffer = buffer
        self.canvas = canvas.Canvas(buffer, pagesize=pagesize)
        self.width, self.height = pagesize
        self.y_position = self.height - inch

    def draw_header(self, title):
        self.canvas.setFont("Helvetica-Bold", 16)
        self.canvas.drawCentredString(self.width / 2.0, self.y_position, title)
        self.y_position -= 0.5 * inch
        self.canvas.line(inch, self.y_position, self.width - inch, self.y_position)
        self.y_position -= 0.25 * inch

    def draw_text_block(self, data):
        self.canvas.setFont("Helvetica", 10)
        for key, value in data.items():
            text = f"{key}: {value}"
            self.canvas.drawString(inch, self.y_position, text)
            self.y_position -= 0.25 * inch
            if self.y_position < inch:
                self.canvas.showPage()
                self.canvas.setFont("Helvetica", 10)
                self.y_position = self.height - inch
        self.y_position -= 0.2 * inch

    def draw_paragraph(self, title, text_content):
        styles = getSampleStyleSheet()
        style = styles["BodyText"]
        style.alignment = TA_JUSTIFY

        # Título da Seção
        self.canvas.setFont("Helvetica-Bold", 12)
        self.canvas.drawString(inch, self.y_position, title)
        self.y_position -= 0.25 * inch

        # Parágrafo
        p = Paragraph(text_content, style)
        p_width, p_height = p.wrapOn(self.canvas, self.width - 2 * inch, self.height)

        if self.y_position < p_height + inch:
            self.canvas.showPage()
            self.y_position = self.height - inch

        p.drawOn(self.canvas, inch, self.y_position - p_height)
        self.y_position -= p_height + 0.25 * inch

    def save(self):
        self.canvas.save()
        self.buffer.seek(0)
        return self.buffer.getvalue()




@router.get("/by-device/{device_id}")
def generate_device_report_pdf(device_id: int, cursor: pymysql.cursors.DictCursor = Depends(get_cursor)):
    cursor.execute("SELECT nome FROM dispositivos WHERE id = %s", (device_id,))
    device = cursor.fetchone()
    if not device:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado")

    cursor.execute("""
                   SELECT DATE_FORMAT(d.data_deteccao, '%%d/%%m/%%Y %%H:%%i') as data, 
               eta.nome AS ataque, 
               esr.nome AS resposta
        FROM deteccoes d
        JOIN enum_tipo_ataque eta ON d.tipo_ataque_id = eta.id
        JOIN enum_status_resposta esr ON d.status_resposta_id = esr.id
        WHERE d.dispositivo_id = %s 
        ORDER BY d.data_deteccao DESC;
                   """, (device_id,))
    detections = cursor.fetchall()

    buffer = io.BytesIO()
    pdf = PDFGenerator(buffer, letter)
    pdf.draw_header(f"Relatório de Detecções - {device['nome']}")

    if not detections:
        pdf.draw_text_block({"Status": "Nenhuma detecção encontrada para este dispositivo."})
    else:
        for detection in detections:
            pdf.draw_text_block(detection)

    pdf_bytes = pdf.save()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=relatorio_{device_id}.pdf"}
    )


@router.get("/by-threat/{threat_type_id}")
def generate_threat_report_pdf(threat_type_id: int, cursor: pymysql.cursors.DictCursor = Depends(get_cursor)):
    """Gera um relatório em PDF listando todos os dispositivos afetados por um tipo de ameaça."""

    # 1. Buscar o nome da ameaça
    cursor.execute("SELECT nome FROM enum_tipo_ataque WHERE id = %s", (threat_type_id,))
    threat = cursor.fetchone()
    if not threat:
        raise HTTPException(status_code=404, detail="Tipo de ameaça não encontrado")

    # 2. Buscar todas as detecções para essa ameaça
    cursor.execute("""
                   SELECT 
            disp.nome as dispositivo, 
            DATE_FORMAT(d.data_deteccao, '%%d/%%m/%%Y %%H:%%i') as data, 
            esr.nome AS resposta
        FROM deteccoes d
        JOIN dispositivos disp ON d.dispositivo_id = disp.id
        JOIN enum_status_resposta esr ON d.status_resposta_id = esr.id
        WHERE d.tipo_ataque_id = %s 
        ORDER BY d.data_deteccao DESC LIMIT 100;
                   """, (threat_type_id,))
    detections = cursor.fetchall()

    # 3. Gerar o PDF
    buffer = io.BytesIO()
    pdf = PDFGenerator(buffer, letter)
    pdf.draw_header(f"Relatório de Ameaça: {threat['nome']}")

    if not detections:
        pdf.draw_text_block({"Status": "Nenhuma detecção encontrada para esta ameaça."})
    else:
        for detection in detections:
            pdf.draw_text_block(detection)

    pdf_bytes = pdf.save()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=relatorio_ameaca_{threat_type_id}.pdf"}
    )


@router.get("/by-detection/{detection_id}")
def generate_detection_report_pdf(detection_id: int, cursor: pymysql.cursors.DictCursor = Depends(get_cursor)):
    """Gera um relatório detalhado em PDF para uma única detecção."""

    # 1. Busca os detalhes completos do incidente (reutilizando a query do history_router)
    query = """
             SELECT
            d.id, disp.nome AS nome_dispositivo, eta.nome AS tipo_ataque,
            DATE_FORMAT(d.data_deteccao, '%%d/%%m/%%Y %%H:%%i') as data_deteccao,
            esr.nome AS status_resposta, enr.nome as nivel_risco,
            ia.resumo_tecnico, ia.explicacao_llm, ia.acoes_recomendadas
        FROM deteccoes d
        JOIN dispositivos disp ON d.dispositivo_id = disp.id
        JOIN enum_tipo_ataque eta ON d.tipo_ataque_id = eta.id
        JOIN enum_status_resposta esr ON d.status_resposta_id = esr.id
        LEFT JOIN incidentes_analisados ia ON d.incidente_id = ia.id
        LEFT JOIN enum_nivel_risco enr ON ia.nivel_risco_id = enr.id
        WHERE d.id = %s;
            """
    cursor.execute(query, (detection_id,))
    detail = cursor.fetchone()

    if not detail:
        raise HTTPException(status_code=404, detail="Detecção não encontrada.")

    # 2. Gerar o PDF com os detalhes
    buffer = io.BytesIO()
    pdf = PDFGenerator(buffer, letter)
    pdf.draw_header(f"Relatório de Detecção #{detail['id']}")

    # Bloco de informações principais
    info_block = {
        "Ataque": detail.get('tipo_ataque', 'N/A'),
        "Dispositivo": detail.get('nome_dispositivo', 'N/A'),
        "Data": detail.get('data_deteccao', 'N/A'),
        "Status da Resposta": detail.get('status_resposta', 'N/A'),
        "Nível de Risco": detail.get('nivel_risco', 'Desconhecido')
    }
    pdf.draw_text_block(info_block)

    # Bloco de análise do LLM
    if detail.get('explicacao_llm'):
        pdf.draw_paragraph("Análise Detalhada (LLM)", detail['explicacao_llm'])

    # Bloco de ações recomendadas
    if detail.get('acoes_recomendadas'):
        pdf.draw_paragraph("Ações Recomendadas", detail['acoes_recomendadas'].replace('•', '\n• '))

    pdf_bytes = pdf.save()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=relatorio_deteccao_{detection_id}.pdf"}
    )
