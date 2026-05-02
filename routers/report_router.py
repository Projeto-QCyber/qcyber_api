# /report_router.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
import pymysql
import io
from datetime import datetime, timezone
import schemas, security
from database import get_cursor

# --- Importações do ReportLab ---
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import Paragraph, Table, TableStyle, Spacer
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib import colors

import ast

router = APIRouter(
    prefix="/api/report",
    tags=["Reports"],
    dependencies=[Depends(security.oauth2_scheme)]
)


class PDFGenerator:
    def __init__(self, buffer, pagesize):
        self.buffer = buffer
        self.canvas = canvas.Canvas(buffer, pagesize=pagesize)
        self.width, self.height = pagesize
        self.styles = getSampleStyleSheet()
        self.page_number = 1

        self.margin_x = 0.75 * inch
        self.top_margin_y = self.height - 0.75 * inch
        self.bottom_margin_y = 0.75 * inch

        self.y_position = self.height - 1.5 * inch

    def _draw_static_content(self, title):
        self.canvas.saveState()

        try:
            logo_path = 'assets/logo.png'
            self.canvas.drawImage(logo_path, self.margin_x, self.height - 1.5 * inch,
                                  width=1.2 * inch, preserveAspectRatio=True, mask='auto')
        except Exception:
            self.canvas.drawString(self.margin_x, self.height - 1 * inch, "[LOGO]")

        self.canvas.setFont("Helvetica-Bold", 16)
        self.canvas.drawCentredString(self.width / 2.0, self.height - 1.0 * inch, title)

        self.canvas.line(self.margin_x, self.height - 1.25 * inch, self.width - self.margin_x,
                         self.height - 1.25 * inch)

        today_date = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
        self.canvas.setFont("Helvetica", 9)
        # --- TRADUZIDO ---
        self.canvas.drawString(self.margin_x, self.bottom_margin_y - 0.2 * inch, f"Generated on: {today_date}")
        # --- TRADUZIDO ---
        self.canvas.drawRightString(self.width - self.margin_x, self.bottom_margin_y - 0.2 * inch,
                                    f"Page {self.page_number}")

        self.canvas.restoreState()

    def new_page(self, title):
        self.canvas.showPage()
        self.page_number += 1
        self._draw_static_content(title)
        self.y_position = self.height - 1.5 * inch

    def draw_flowables(self, flowables, title):
        for flowable in flowables:
            f_width, f_height = flowable.wrapOn(self.canvas, self.width - 2 * self.margin_x, self.height)

            is_splittable_table = f_height > (self.top_margin_y - self.bottom_margin_y - 0.5 * inch) and isinstance(
                flowable, Table)

            if is_splittable_table:
                rows = flowable._cellvalues
                header_row = rows[0]
                chunk_size = 25
                data_chunks = [rows[i:i + chunk_size] for i in range(1, len(rows), chunk_size)]

                for chunk_data in data_chunks:
                    table_chunk_data = [header_row] + chunk_data
                    table_chunk = Table(table_chunk_data, repeatRows=1, colWidths=flowable._colWidths)

                    if hasattr(flowable, 'custom_style'):
                        table_chunk.setStyle(flowable.custom_style)
                    chunk_w, chunk_h = table_chunk.wrapOn(self.canvas, self.width - 2 * self.margin_x, self.height)
                    if self.y_position - chunk_h < self.bottom_margin_y:
                        self.new_page(title)
                    table_chunk.drawOn(self.canvas, self.margin_x, self.y_position - chunk_h)
                    self.y_position -= (chunk_h + 0.15 * inch)

                continue
            self.draw_flowable(flowable, title)


    def draw_flowable(self, flowable, title):
        f_width, f_height = flowable.wrapOn(self.canvas, self.width - 2 * self.margin_x, self.height)
        if self.y_position - f_height < self.bottom_margin_y:
            self.new_page(title)
        flowable.drawOn(self.canvas, self.margin_x, self.y_position - f_height)
        self.y_position -= (f_height + 0.15 * inch)

    def build(self, title, elements):
        self._draw_static_content(title)
        self.draw_flowables(elements, title)
        self.canvas.save()
        self.buffer.seek(0)
        return self.buffer.getvalue()


def create_key_value_table(data, styles):
    table_data = [[Paragraph(f"<b>{key}:</b>", styles['BodyText']), Paragraph(str(value), styles['BodyText'])] for
                  key, value in data.items()]
    table = Table(table_data, colWidths=[1.5 * inch, 5.5 * inch])
    table.setStyle(TableStyle([('VALIGN', (0, 0), (-1, -1), 'TOP'), ('LEFTPADDING', (0, 0), (-1, -1), 0),
                               ('BOTTOMPADDING', (0, 0), (-1, -1), 6), ]))
    return table


def create_data_table(headers, data, styles):
    header_row = [Paragraph(f"<b>{h}</b>", styles['BodyText']) for h in headers]
    content_rows = [[Paragraph(str(item), styles['BodyText']) for item in row] for row in data]
    table_data = [header_row] + content_rows
    table = Table(table_data, repeatRows=1)
    style = TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0d47a1")),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'), ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'), ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor("#e3f2fd")),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black),
                        ('INNERGRID', (0, 0), (-1, -1), 0.25, colors.black), ])
    table.setStyle(style)
    table.custom_style = style
    return table

def create_paragraph(title, text_content, styles):
    style = styles["BodyText"]
    style.alignment = TA_JUSTIFY
    text_content = text_content.replace('\n', '<br/>')
    p_title = Paragraph(title, styles["h2"])
    p_content = Paragraph(text_content, style)
    return p_title, p_content


# --- Rotas ---
@router.get("/by-device/{device_id}")
def generate_device_report_pdf(device_id: int, cursor: pymysql.cursors.DictCursor = Depends(get_cursor)):
    cursor.execute("SELECT nome FROM dispositivos WHERE id = %s", (device_id,))
    device = cursor.fetchone()
    if not device: raise HTTPException(status_code=404, detail="Device not found") # TRADUZIDO
    cursor.execute(
        "SELECT DATE_FORMAT(d.data_deteccao, '%%d/%%m/%%Y %%H:%%i') as data, eta.nome AS ataque, esr.nome AS resposta FROM deteccoes d JOIN enum_tipo_ataque eta ON d.tipo_ataque_id = eta.id JOIN enum_status_resposta esr ON d.status_resposta_id = esr.id WHERE d.dispositivo_id = %s ORDER BY d.data_deteccao DESC LIMIT 200;",
        (device_id,))
    detections = cursor.fetchall()
    buffer = io.BytesIO()
    pdf = PDFGenerator(buffer, letter)
    # --- TRADUZIDO ---
    title = f"Detections Report - {device['nome']}"
    elements = []
    if not detections:
        # --- TRADUZIDO ---
        elements.append(Paragraph("No detections found for this device.", pdf.styles['BodyText']))
    else:
        # --- TRADUZIDO ---
        headers = ["Date", "Attack", "Response"]
        data = [[d['data'], d['ataque'], d['resposta']] for d in detections]
        elements.append(create_data_table(headers, data, pdf.styles))
    pdf_bytes = pdf.build(title, elements)
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=report_device_{device_id}.pdf"})


@router.get("/by-threat/{threat_type_id}")
def generate_threat_report_pdf(threat_type_id: int, cursor: pymysql.cursors.DictCursor = Depends(get_cursor)):
    cursor.execute("SELECT nome FROM enum_tipo_ataque WHERE id = %s", (threat_type_id,))
    threat = cursor.fetchone()
    if not threat: raise HTTPException(status_code=404, detail="Threat type not found") # TRADUZIDO
    cursor.execute(
        "SELECT disp.nome as dispositivo, DATE_FORMAT(d.data_deteccao, '%%d/%%m/%%Y %%H:%%i') as data, esr.nome AS resposta FROM deteccoes d JOIN dispositivos disp ON d.dispositivo_id = disp.id JOIN enum_status_resposta esr ON d.status_resposta_id = esr.id WHERE d.tipo_ataque_id = %s ORDER BY d.data_deteccao DESC LIMIT 200;",
        (threat_type_id,))
    detections = cursor.fetchall()
    buffer = io.BytesIO()
    pdf = PDFGenerator(buffer, letter)
    # --- TRADUZIDO ---
    title = f"Threat Report: {threat['nome']}"
    elements = []
    if not detections:
        # --- TRADUZIDO ---
        elements.append(Paragraph("No detections found for this threat.", pdf.styles['BodyText']))
    else:
        # --- TRADUZIDO ---
        headers = ["Device", "Date", "Response"]
        data = [[d['dispositivo'], d['data'], d['resposta']] for d in detections]
        elements.append(create_data_table(headers, data, pdf.styles))
    pdf_bytes = pdf.build(title, elements)
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=report_threat_{threat_type_id}.pdf"})


@router.get("/by-detection/{detection_id}")
def generate_detection_report_pdf(detection_id: int, cursor: pymysql.cursors.DictCursor = Depends(get_cursor)):
    query = "SELECT d.id, disp.nome AS nome_dispositivo, eta.nome AS tipo_ataque, DATE_FORMAT(d.data_deteccao, '%%d/%%m/%%Y %%H:%%i') as data_deteccao, esr.nome AS status_resposta, enr.nome as nivel_risco, ia.resumo_tecnico, ia.explicacao_llm, ia.acoes_recomendadas FROM deteccoes d JOIN dispositivos disp ON d.dispositivo_id = disp.id JOIN enum_tipo_ataque eta ON d.tipo_ataque_id = eta.id JOIN enum_status_resposta esr ON d.status_resposta_id = esr.id LEFT JOIN incidentes_analisados ia ON d.incidente_id = ia.id LEFT JOIN enum_nivel_risco enr ON ia.nivel_risco_id = enr.id WHERE d.id = %s;"
    cursor.execute(query, (detection_id,))
    detail = cursor.fetchone()
    if not detail: raise HTTPException(status_code=404, detail="Detection not found.") # TRADUZIDO
    buffer = io.BytesIO()
    pdf = PDFGenerator(buffer, letter)
    # --- TRADUZIDO ---
    title = f"Detection Report #{detail['id']}"
    elements = []
    # --- TRADUZIDO ---
    info_block_data = {"Attack": detail.get('tipo_ataque', 'N/A'),
                       "Device": detail.get('nome_dispositivo', 'N/A'),
                       "Date": detail.get('data_deteccao', 'N/A'),
                       "Status": detail.get('status_resposta', 'N/A'),
                       "Risk Level": detail.get('nivel_risco', 'Unknown')}
    elements.append(create_key_value_table(info_block_data, pdf.styles))

    if detail.get('resumo_tecnico'):
        # --- TRADUZIDO ---
        elements.extend(create_paragraph("Technical Summary", detail['resumo_tecnico'], pdf.styles))

    if detail.get('explicacao_llm'):
        # --- TRADUZIDO ---
        elements.extend(create_paragraph("Detailed Analysis (LLM)", detail['explicacao_llm'], pdf.styles))

    if detail.get('acoes_recomendadas'):
        try:
            lista_acoes = ast.literal_eval(detail['acoes_recomendadas'])
            texto_formatado = ""
            if isinstance(lista_acoes, list):
                texto_formatado = "<br/>".join([f"• {acao}" for acao in lista_acoes])
            else:
                texto_formatado = detail['acoes_recomendadas']
            # --- TRADUZIDO ---
            elements.extend(create_paragraph("Recommended Actions", texto_formatado, pdf.styles))
        except (ValueError, SyntaxError):
            # --- TRADUZIDO ---
            elements.extend(create_paragraph("Recommended Actions", detail['acoes_recomendadas'], pdf.styles))

    pdf_bytes = pdf.build(title, elements)
    return Response(content=pdf_bytes, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=report_detection_{detection_id}.pdf"})