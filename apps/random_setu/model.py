import datetime
import json

from peewee import Model, CharField, DateTimeField, TextField, DatabaseProxy, IntegerField, DoesNotExist, fn
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

    @classmethod
    def get_random(cls, user_id: int, *, ai_type: int = 0, r18: int = 0, sl: int = 0):
        condition = []
        if ai_type != 0:
            condition.append(cls.ai_type == ai_type)
        if r18 != 0:
            condition.append(cls.r18 == r18)
        if r18 == 1 and sl != 0:
            condition.append(cls.sl <= sl)
        recent_setus = cls.select().where(*condition) if condition else cls.select()
        viewed = ViewHistory.select(ViewHistory.setu_id).where(ViewHistory.user_id == user_id)
        return recent_setus.where(cls.id.not_in(viewed)).order_by(fn.Rand()).limit(1).first()


class ViewHistory(BaseModel):
    user_id = CharField(max_length=100)
    setu_id = CharField(max_length=32)
    time = DateTimeField(default=datetime.datetime.now)

    class Meta:
        table_name = 'view_history'


class UserConfig(BaseModel):
    user_id = CharField(max_length=100)
    config = TextField()
    modified_time = DateTimeField(default=datetime.datetime.now)

    DEFAULT_CONFIG = json.dumps({
        "ai_type": 0,
        "r18": 0,
        "sl": 6,
    })

    class Meta:
        table_name = 'user_config'

    @property
    def config_data(self):
        return json.loads(self.config) if self.config else {}

    @config_data.setter
    def config_data(self, value):
        self.config = json.dumps(value)

    @classmethod
    def get_or_default(cls, user_id: int):
        ucf, _ = cls.get_or_create(user_id=user_id, defaults={
            'user_id': user_id,
            'config': cls.DEFAULT_CONFIG,
        })
        return ucf

    @classmethod
    def update_config(cls, user_id: int, config: dict):
        try:
            ucf = cls.get(cls.user_id == user_id)
            ucf.config = json.dumps(config)
            ucf.save()
        except DoesNotExist:
            ucf = cls.create(user_id=user_id, config=json.dumps(config))
        return ucf


def initialize_database(db_url: str):
    db.initialize(_db_url.connect(db_url))
    db.create_tables([Setu, ViewHistory, UserConfig], safe=True)
    db.close()
