import datetime

from peewee import Model, DateTimeField, TextField, DatabaseProxy
from playhouse import db_url as _db_url

db = DatabaseProxy()


class LtMessage(Model):
    type = TextField()
    channel = TextField()
    pattern = TextField(null=True)
    data = TextField()
    dtm = DateTimeField(formats='%Y-%m-%dT%H:%M:%S%z', default=datetime.datetime.now)

    class Meta:
        table_name = 'ltmessage'
        database = db


def initialize_database(db_url: str):
    db.initialize(_db_url.connect(db_url))
    db.create_tables([LtMessage], safe=True)
    db.close()
