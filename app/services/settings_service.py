from app.database import db
from app.models.models import Setting

def get_all_settings():
    settings = Setting.query.all()
    return {s.key: s.value for s in settings}

def get_setting(key):
    setting = Setting.query.filter_by(key=key).first()
    return setting.value if setting else None

def update_setting(key, value):
    setting = Setting.query.filter_by(key=key).first()
    if not setting:
        setting = Setting(key=key)
        db.session.add(setting)
    setting.value = value
    db.session.commit()
    return setting
