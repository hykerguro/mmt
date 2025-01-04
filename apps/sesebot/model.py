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
    source = CharField(max_length=16, help_text="来源：pixiv, stash")
    phase = CharField(max_length=32, null=True, help_text="二级来源：<source>:<phase>")

    # 基本属性
    id = CharField(max_length=32, help_text="ID")
    page = TextField(null=True, help_text="主页")
    title = CharField(max_length=500, help_text="标题")
    page_count = IntegerField(help_text="数量")
    preview_url = TextField(help_text="预览图")
    original_url = TextField(help_text="原图：json化的list")
    artist_name = CharField(max_length=100, null=True, help_text="作者")
    artist_url = TextField(help_text="作者主页")
    create_time = DateTimeField(null=True, help_text="创建时间")
    income_time = DateTimeField(default=datetime.datetime.now, help_text="入库时间")

    # 标签
    r18 = CharField(max_length=1, help_text="R18：0不确定；1-否；2-是")
    sl = IntegerField(help_text="涩度：0不确定；2~6")  # 色情程度 0~6
    ai_type = CharField(max_length=1, help_text="AI生成：0-不确定；1-否；2-是")
    real = CharField(max_length=1, help_text="真人涩情：0-不确定；1-否；2-是")
    tags = TextField(help_text="标签：json化的list")  # list

    # 其他
    meta = TextField(default="{}", help_text="元数据：json字符串")

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
    user_id = CharField(max_length=100, help_text="用户ID")
    setu_id = CharField(max_length=32, help_text="涩图ID")
    setu_source = CharField(max_length=16, help_text="涩图来源")
    time = DateTimeField(default=datetime.datetime.now, help_text="浏览时间")

    class Meta:
        table_name = 'view_history'


class UserConfig(BaseModel):
    user_id = CharField(max_length=100, help_text="用户ID")
    config = TextField(help_text="用户配置：json字符串")
    modified_time = DateTimeField(default=datetime.datetime.now, help_text="修改时间")

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
