import smtplib
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Mapping, Collection, Sequence

from loguru import logger

from litter.adapt import agent, FromConfig
from mmt.api.mail import MailApi


@agent(
    "mmt.agent.mail",
    init_args=(),
    init_kwargs=FromConfig("mail")
)
class MailAgent(MailApi):
    def __init__(self, sender_address: str, password: str,
                 smtp_server: str, smtp_port: int = 465,
                 *, send_name: str | None = None) -> None:
        self.sender_name = send_name or sender_address
        self.sender_address = sender_address
        self.smtp_server = smtp_server
        self.smtp_port = int(smtp_port)
        self.password = password
        self.server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)

    def send(self,
             to: str | Mapping[str, str] | Collection[Mapping[str, str]],
             title: str,
             body: str = "",
             *,
             html: str | None = None,
             attachments: Sequence[tuple[str, bytes]] | None = None,
             ) -> None:
        if isinstance(to, str):
            tos = [{"address": to, "name": to}]
        elif isinstance(to, Mapping):
            assert "address" in to and "name" in to
            tos = [to]
        elif isinstance(to, Collection):
            assert all("address" in x and "name" in x for x in to)
            tos = to
        else:
            raise TypeError("to")

        if html is not None:
            content = html
            subtype = "html"
        else:
            content = body
            subtype = "plain"

        if attachments is None:
            attachments = []

        msg = MIMEMultipart()
        msg['From'] = formataddr((self.sender_name, self.sender_address))
        msg['To'] = ",".join(x["name"] for x in tos)
        msg['Subject'] = title
        msg.attach(MIMEText(content, subtype, "utf-8"))

        for filename, data_bytes in attachments or []:
            mime = MIMEBase("application", "octet-stream")
            mime.add_header("Content-Disposition", f"attachment; filename={filename}")
            mime.set_payload(data_bytes)
            msg.attach(mime)

        logger.info(f"发送邮件到{msg['To']}")
        server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
        server.login(self.sender_address, self.password)
        server.sendmail(self.sender_address, [to["address"] for to in tos], msg.as_string())
        server.quit()
