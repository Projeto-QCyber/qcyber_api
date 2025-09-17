# /email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pymysql
from database import get_cursor


def send_verification_email(to_email: str, code: str, subject: str, cursor: pymysql.cursors.DictCursor):
    """
    Busca as configurações de SMTP do banco e envia um e-mail.
    Esta função será usada tanto para verificação de conta quanto para 2FA.
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
        message.attach(MIMEText(html, "html"))

        # Envia o e-mail
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_email, message.as_string())

        print(f"✅ E-mail de verificação enviado para {to_email}")
        return True

    except Exception as e:
        print(f"❌ ERRO ao enviar e-mail: {e}")
        return False