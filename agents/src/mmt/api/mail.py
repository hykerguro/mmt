from typing import Mapping, Sequence, Collection

from .framework import api, ApiBase


@api("mmt.agent.mail")
class MailApi(ApiBase):
    def send(self,
             to: str | Mapping[str, str] | Collection[Mapping[str, str]],
             title: str,
             body: str = "",
             *,
             html: str | None = None,
             attachments: Sequence[tuple[str, bytes]] | None = None,
             ) -> None:
        """
        发送邮件

        :param to: 收件人。格式：
            1. who@email.sample
            2. {"address": "who@email.sample", "name": "your name"}
            3. [{"address": "who1@email.sample", "name": "your name1"}, {"address": "who2@email.sample", "name": "your name2"}]
        :param title: 标题
        :param body: 内容（纯文本）
        :param html: html格式的内容
        :param attachments: 附件。格式：
            [("filename.xyz", b'somebytes'), ("filename.xyz", b'somebytes')]
        :return:
        """
        ...
