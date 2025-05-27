import smtplib
import ssl
import socket
from email.message import EmailMessage
import asyncio
from typing import Optional
from app.settings import settings, setup_logging


class AsyncSMTPMailer:
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        username: str,
        password: str,
        source_ip: Optional[str] = None,
        use_tls: bool = True,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.source_ip = source_ip
        self.use_tls = use_tls

    def _send(self, to_email: str, subject: str, html_content: str):
        # Формируем письмо
        msg = EmailMessage()
        msg['From'] = self.username
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.set_content("Ваш почтовый клиент не поддерживает HTML.")
        msg.add_alternative(html_content, subtype='html')

        # TLS контекст
        context = ssl.create_default_context()

        # Соединение
        with smtplib.SMTP(
            host=self.smtp_host,
            port=self.smtp_port,
            source_address=(self.source_ip, 0) if self.source_ip else None
        ) as server:
            server.ehlo()
            if self.use_tls:
                server.starttls(context=context)
                server.ehlo()
            server.login(self.username, self.password)
            server.send_message(msg)

    async def send(self, to_email: str, subject: str, html_content: str):
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            self._send,
            to_email,
            subject,
            html_content,
        )

mailer = AsyncSMTPMailer(
        smtp_host=settings.SMTP_HOST,
        smtp_port=settings.SMTP_PORT,
        username=settings.EMAIL_USERNAME,
        password=settings.EMAIL_PASSWORD,
        source_ip=settings.EMAIL_SOURCE_IP,
        use_tls=True
    )
