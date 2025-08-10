import datetime
import json

from peewee import Model, CharField, BooleanField, DateTimeField, TextField, DatabaseProxy
from playhouse import db_url as _db_url

db = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = db


class BookmarkWork(BaseModel):
    illust_id = CharField(primary_key=True, max_length=255)
    bookmark_id = CharField(max_length=255)
    is_private = BooleanField(default=False)
    bookmark_datetime = DateTimeField(formats='%Y-%m-%dT%H:%M:%S%z', default=datetime.datetime.now)
    create_datetime = DateTimeField(formats='%Y-%m-%dT%H:%M:%S%z')
    update_datetime = DateTimeField(formats='%Y-%m-%dT%H:%M:%S%z')
    meta = TextField()

    class Meta:
        table_name = 'bookmark_work'

    @property
    def meta_data(self):
        return json.loads(self.meta) if self.meta else {}

    @meta_data.setter
    def meta_data(self, value):
        self.meta = json.dumps(value)


class FollowWork(BaseModel):
    illust_id = CharField(primary_key=True, max_length=255)
    create_datetime = DateTimeField(formats='%Y-%m-%dT%H:%M:%S%z')
    update_datetime = DateTimeField(formats='%Y-%m-%dT%H:%M:%S%z')
    meta = TextField()

    class Meta:
        table_name = 'follow_work'

    @property
    def meta_data(self):
        return json.loads(self.meta) if self.meta else {}

    @meta_data.setter
    def meta_data(self, value):
        self.meta = json.dumps(value)


def initialize_database(db_url: str):
    db.initialize(_db_url.connect(db_url))
    db.create_tables([BookmarkWork, FollowWork], safe=True)
    db.close()
