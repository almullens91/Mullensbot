from mongoengine import Document, IntField, DynamicField, DictField, StringField


class Channels(Document):
    _id = IntField(primary_key=True)
    user_name = DynamicField(default="")
    user_login = DynamicField(default="")
    channel_details = DictField(default={
        "online": False,
        "online_last": None,
        "branded": False,
        "title": "",
        "game_id": "",
        "game_name": "",
        "content_class": [],
        "tags": []
    })


class Users(Document):
    _id = StringField(primary_key=True)
    name = StringField(default="")
    data_games = DictField(default={})
    data_rank = DictField(default={
        "boost": 0.0,
        "level": 1,
        "xp": 0.0
    })
    data_user = DictField(default={
        "points": 0.0
    })
