import datetime
import json

from peewee import Model, CharField, DateTimeField, TextField, DatabaseProxy, IntegerField
from playhouse import db_url as _db_url

db = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = db


class Setu(BaseModel):
    # 渠道
    source = CharField(max_length=16)  # pixiv
    phase = CharField(max_length=32, null=True)  # pixiv:fav; pixiv:follow; pixiv:recommend

    # 基本属性
    id = CharField(max_length=32)
    page = TextField(null=True)
    title = CharField(max_length=500)
    page_count = IntegerField()  # 图片数量
    preview_url = TextField()
    original_url = TextField()  # list
    artist_name = CharField(max_length=100)
    artist_url = TextField()
    create_time = DateTimeField(null=True)
    income_time = DateTimeField(default=datetime.datetime.now)

    # 标签
    r18 = CharField(max_length=1)  # 1: r18; 0: 非r18
    sl = IntegerField()  # 色情程度 0~6
    ai_type = CharField(max_length=1)  # 1-非AI；2-AI生成
    tags = TextField()  # list

    # 其他
    meta = TextField(default="{}")

    class Meta:
        table_name = 'setu'

    @property
    def meta_data(self):
        return json.loads(self.meta) if self.meta else {}

    @meta_data.setter
    def meta_data(self, value):
        self.meta = json.dumps(value)

    @property
    def original_url_data(self) -> list[str]:
        return json.loads(self.original_url) if self.original_url else {}

    @original_url_data.setter
    def original_url_data(self, value: list[str]):
        self.original_url = json.dumps(value)

    @property
    def tags_data(self) -> list[str]:
        return json.loads(self.tags) if self.tags else {}

    @tags_data.setter
    def tags_data(self, value: list[str]):
        self.tags = json.dumps(value)


class ViewHistory(BaseModel):
    userId = CharField(max_length=100)
    setuId = CharField(max_length=32)
    time = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = 'view_history'


def initialize_database(db_url: str):
    db.initialize(_db_url.connect(db_url))
    db.create_tables([Setu, ViewHistory], safe=True)
    db.close()
