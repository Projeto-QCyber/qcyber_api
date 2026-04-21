# /email_service.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import settings


def _send_email(to_email: str, subject: str, html_content: str) -> bool:
    """
    Função interna e genérica para enviar e-mails usando SMTP definido no .env.
    """
    try:
        smtp_server = settings.SMTP_SERVER
        smtp_port = settings.SMTP_PORT
        smtp_user = settings.SMTP_USER
        smtp_password = settings.SMTP_PASSWORD
        sender_name = settings.SMTP_SENDER_NAME or "qCyber Platform"

        if not all([smtp_server, smtp_user, smtp_password]):
            print(
                "❌ ERRO: Configurações de SMTP incompletas. "
                "Defina SMTP_SERVER, SMTP_USER e SMTP_PASSWORD no .env."
            )
            return False

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = f"{sender_name} <{smtp_user}>"
        message["To"] = to_email

        message.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_email, message.as_string())

        print(f"✅ E-mail enviado com sucesso para {to_email} com o assunto '{subject}'")
        return True

    except Exception as e:
        print(f"❌ ERRO ao enviar e-mail: {e}")
        return False


def send_verification_email(to_email: str, code: str, subject: str):
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
    return _send_email(to_email, subject, html)


def send_email_html(to_email: str, subject: str, html_content: str):
    """
    Envia um e-mail com um CORPO HTML totalmente personalizado.
    """
    return _send_email(to_email, subject, html_content)
