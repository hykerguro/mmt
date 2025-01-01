from peewee import Model, TextField, DatabaseProxy, IntegerField, AutoField
from playhouse import db_url as _db_url

db = DatabaseProxy()


class BaseModel(Model):
    class Meta:
        database = db


class GalleryEntity(BaseModel):
    id = AutoField(primary_key=True, )
    gid = IntegerField()
    token = TextField()
    title = TextField()
    title_jpn = TextField()
    thumb = TextField()
    eh_category = TextField()
    uploader = TextField()
    expunged = IntegerField()
    date = TextField(null=True)
    filecount = IntegerField()

    class Meta:
        table_name = 'gallery'


def initialize_database(db_url: str):
    db.initialize(_db_url.connect(db_url))
    db.create_tables([GalleryEntity], safe=True)
    db.close()
