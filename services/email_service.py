# /email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pymysql
from database import get_cursor


def _send_email(to_email: str, subject: str, html_content: str, cursor: pymysql.cursors.DictCursor) -> bool:
    """
    Função interna e genérica para enviar e-mails.
    Busca as configurações de SMTP do banco e envia a mensagem com o conteúdo HTML fornecido.
    """
    try:
        # Busca as configurações de SMTP no banco de dados
        cursor.execute("SELECT chave, valor FROM configuracoes WHERE chave LIKE 'SMTP_%'")
        configs_list = cursor.fetchall()

        # Converte a lista de dicionários para um único dicionário
        smtp_configs = {item['chave']: item['valor'] for item in configs_list}

        smtp_server = smtp_configs.get('SMTP_SERVER')
        smtp_port = int(smtp_configs.get('SMTP_PORT', 587))
        smtp_user = smtp_configs.get('SMTP_USER')
        smtp_password = smtp_configs.get('SMTP_PASSWORD')
        sender_name = smtp_configs.get('SMTP_SENDER_NAME', 'qCyber Platform')

        if not all([smtp_server, smtp_port, smtp_user, smtp_password]):
            print("❌ ERRO: Configurações de SMTP incompletas no banco de dados.")
            return False

        # Cria a mensagem do e-mail
        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{sender_name} <{smtp_user}>"
        message["To"] = to_email

        # Anexa o conteúdo HTML passado como argumento
        message.attach(MIMEText(html_content, "html"))

        # Envia o e-mail
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_email, message.as_string())

        print(f"✅ E-mail enviado com sucesso para {to_email} com o assunto '{subject}'")
        return True

    except Exception as e:
        print(f"❌ ERRO ao enviar e-mail: {e}")
        return False


def send_verification_email(to_email: str, code: str, subject: str, cursor: pymysql.cursors.DictCursor):
    """
    Prepara e envia um e-mail de VERIFICAÇÃO DE CÓDIGO.
    Esta função monta o HTML específico para o código e chama a função de envio principal.
    """
    html = f"""
    <html>
    <body>
        <p>Olá,</p>
        <p>Seu código de verificação é:</p>
        <h2 style="font-size: 24px; letter-spacing: 2px; text-align: center;">{code}</h2>
        <p>Este código irá expirar em 5 minutos.</p>
        <p>Se você não solicitou este código, por favor, ignore este e-mail.</p>
        <p>Atenciosamente,<br>Equipe qCyber</p>
    </body>
    </html>
    """
    return _send_email(to_email, subject, html, cursor)


def send_email_html(to_email: str, subject: str, html_content: str, cursor: pymysql.cursors.DictCursor):
    """
    Envia um e-mail com um CORPO HTML totalmente personalizado.
    Esta é a função que você chamará da sua rota de admin.
    """
    return _send_email(to_email, subject, html_content, cursor)