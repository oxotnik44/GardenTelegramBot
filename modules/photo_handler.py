# photo_handler.py
import datetime

# {user_id: {"photos": [(timestamp, file_id)], "questions": [question_text]}}
user_data = {}


def save_photo(user_id, file_id):
    """Сохраняет фото пользователя"""
    user_data.setdefault(user_id, {"photos": [], "questions": []})[
        "photos"].append((datetime.datetime.now(), file_id))


def get_fresh_photos(user_id):
    """Возвращает фото, загруженные за последние полтора месяца (45 дней)"""
    now = datetime.datetime.now()
    photos = user_data.get(user_id, {}).get("photos", [])
    return [file_id for time, file_id in photos if now - time <= datetime.timedelta(days=45)]
