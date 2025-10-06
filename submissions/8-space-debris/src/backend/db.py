from datetime import datetime
from peewee import *

db = SqliteDatabase("orbit_data.db")

class BaseModel(Model):
    class Meta:
        database = db

class OrbitData(BaseModel):
    id = PrimaryKeyField()
    timestamp = DateTimeField(default=datetime.now)
    classification = TextField()
    image = BlobField() 
