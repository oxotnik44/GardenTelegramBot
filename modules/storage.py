import datetime
import uuid
import json
import os

STORAGE_FILE = "storageData.json"

# Глобальные переменные по умолчанию
user_data = {"photos": [], "questions": []}
user_data_useful = {
    "useful_photo": [],
    "useful_text": [],
    "useful_video": []  # Добавлено для хранения полезных видео
}
group_buffer_useful = {}
group_buffer = {}
product_photos = []   # Список для фотографий товаров
product_videos = []   # Список для видео товаров


def default_serializer(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError(f"Объект типа {type(obj)} не сериализуем")


def delete_record_by_storage(tag, record_uuid):
    """
    Удаляет запись по uuid из указанного тега (question, useful, product).
    Сохраняет обновлённые данные в файл.
    """
    load_storage_data()

    def remove_by_uuid(records):
        return [r for r in records if r.get("uuid") != record_uuid]

    if tag == "question":
        user_data["questions"] = remove_by_uuid(user_data["questions"])
        print(f"🗑 Удалён вопрос с uuid {record_uuid}")

    elif tag == "useful":
        user_data_useful["useful_photo"] = remove_by_uuid(
            user_data_useful["useful_photo"])
        user_data_useful["useful_text"] = remove_by_uuid(
            user_data_useful["useful_text"])
        user_data_useful["useful_video"] = remove_by_uuid(
            user_data_useful.get("useful_video", []))
        print(f"🗑 Удалены полезные данные с uuid {record_uuid} (если были)")

    elif tag == "product":
        global product_photos, product_videos
        product_photos = remove_by_uuid(product_photos)
        product_videos = remove_by_uuid(product_videos)
        print(f"🗑 Удалена запись товара с uuid {record_uuid}")

    else:
        print(f"⚠️ Неизвестный тег {tag}")
        return

    save_storage_data()


def load_storage_data():
    """
    Загружает данные из файла STORAGE_FILE и обновляет глобальные переменные.
    Если файл не найден, остаются значения по умолчанию.
    """
    global user_data, user_data_useful, group_buffer_useful, group_buffer, product_photos, product_videos
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            user_data = data.get("user_data", {"photos": [], "questions": []})
            user_data_useful = data.get("user_data_useful", {
                "useful_photo": [],
                "useful_text": [],
                "useful_video": []
            })
            group_buffer_useful = data.get("group_buffer_useful", {})
            group_buffer = data.get("group_buffer", {})
            product_photos = data.get("product_photos", [])
            product_videos = data.get("product_videos", [])
            # Преобразуем строки дат обратно в datetime, если требуется для фильтрации
            for q in user_data.get("questions", []):
                if isinstance(q.get("saved_date"), str):
                    try:
                        q["saved_date"] = datetime.datetime.fromisoformat(
                            q["saved_date"])
                    except Exception:
                        pass
            for key in ("useful_photo", "useful_text", "useful_video"):
                for r in user_data_useful.get(key, []):
                    if isinstance(r.get("saved_date"), str):
                        try:
                            r["saved_date"] = datetime.datetime.fromisoformat(
                                r["saved_date"])
                        except Exception:
                            pass
            for p in product_photos:
                if isinstance(p.get("saved_date"), str):
                    try:
                        p["saved_date"] = datetime.datetime.fromisoformat(
                            p["saved_date"])
                    except Exception:
                        pass
            for v in product_videos:
                if isinstance(v.get("saved_date"), str):
                    try:
                        v["saved_date"] = datetime.datetime.fromisoformat(
                            v["saved_date"])
                    except Exception:
                        pass
        except Exception as e:
            print(f"⚠️ Ошибка при загрузке данных: {e}")
    else:
        print(
            f"⚠️ Файл {STORAGE_FILE} не найден. Используются значения по умолчанию.")


def save_storage_data():
    """
    Сохраняет текущие глобальные переменные в файл STORAGE_FILE.
    При сохранении объекты datetime сериализуются в ISO-формат.
    """
    data = {
        "user_data": user_data,
        "user_data_useful": user_data_useful,
        "group_buffer_useful": group_buffer_useful,
        "group_buffer": group_buffer,
        "product_photos": product_photos,
        "product_videos": product_videos,
    }
    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, default=default_serializer,
                      ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Ошибка при сохранении данных: {e}")


def filter_old_records(records, days=30):
    """
    Удаляет записи старше указанного количества дней.
    Если поле saved_date представлено строкой, пытается преобразовать его в datetime.
    При изменении списка вызывает сохранение данных в файл.
    """
    now = datetime.datetime.now()
    filtered = []
    for r in records:
        saved_date = r.get("saved_date")
        if isinstance(saved_date, str):
            try:
                saved_date = datetime.datetime.fromisoformat(saved_date)
            except Exception:
                continue
        if isinstance(saved_date, datetime.datetime):
            if (now - saved_date).days <= days:
                filtered.append(r)
    if len(filtered) != len(records):
        records[:] = filtered
        save_storage_data()


def save_user_message(user_id, item, tag):
    """
    Сохраняет сообщение с заданным тегом и добавляет уникальный uuid для каждой записи.
    Данные обновляются из файла и сохраняются обратно после внесения изменений.
    Для tag='useful' поддерживаются фото, текст и видео.
    Для tag='product' поддерживаются фото и видео.
    """
    load_storage_data()  # Обновляем данные из файла
    now = datetime.datetime.now()
    record_uuid = str(uuid.uuid4())

    if tag == "question" and isinstance(item, dict) and "text" in item:
        question_text = item["text"].strip()
        if question_text and "?" in question_text and question_text != "?":
            user_data["questions"].append({
                "user_id": user_id,
                "text": question_text,
                "message_id": item["message_id"],
                "saved_date": now,
                "uuid": record_uuid
            })
            print(f"✅ Сохранён вопрос от {user_id}: {question_text}")

    elif tag == "useful":
        # Определяем тип полезного контента: фото, текст или видео
        if "photo" in item:
            key = "useful_photo"
            value = item.get("photo")
        elif "text" in item:
            key = "useful_text"
            value = item.get("text")
        elif "video" in item:
            key = "useful_video"
            value = item.get("video")
        else:
            print("⚠️ Неопределён тип полезного контента")
            return
        user_data_useful[key].append({
            ("photo" if key == "useful_photo" else ("text" if key == "useful_text" else "video")): value,
            "saved_date": now,
            "uuid": record_uuid
        })
        print(
            f"✅ Сохранён {'фото' if key == 'useful_photo' else ('текст' if key == 'useful_text' else 'видео')}: {value}")

    elif tag == "product":
        # Определяем тип товара: фото или видео
        if isinstance(item, dict) and "video" in item:
            product_videos.append({
                "video": item["video"],
                "saved_date": now,
                "uuid": record_uuid
            })
            print("✅ Сохранено видео продукта")
        elif isinstance(item, dict) and "photo" in item:
            product_photos.append({
                "photo": item["photo"],
                "saved_date": now,
                "uuid": record_uuid
            })
            print("✅ Сохранена фотография продукта")
        else:
            # Если передан не словарь, считаем, что это фотография
            product_photos.append({
                "photo": item,
                "saved_date": now,
                "uuid": record_uuid
            })
            print("✅ Сохранена фотография продукта")
    else:
        print(f"⚠️ Неизвестный тег {tag}")
        return

    save_storage_data()


def get_user_message(tag, filter_tag=None):
    """
    Загружает данные из файла STORAGE_FILE, обновляет глобальные переменные,
    фильтрует устаревшие записи и возвращает список элементов по тегу.
    Для tag='useful' может возвращать фото, текст или видео (при передаче filter_tag).
    Для tag='product' объединяет записи по фото и видео в один список.
    """
    load_storage_data()  # Обновляем данные из файла

    if tag == "question":
        filter_old_records(user_data["questions"])
        save_storage_data()
        return user_data["questions"]

    elif tag == "useful":
        filter_old_records(user_data_useful["useful_photo"])
        filter_old_records(user_data_useful["useful_text"])
        filter_old_records(user_data_useful.get("useful_video", []))
        save_storage_data()
        valid_photos = [r["photo"] for r in user_data_useful["useful_photo"]]
        valid_texts = [r["text"] for r in user_data_useful["useful_text"]]
        valid_videos = [r["video"]
                        for r in user_data_useful.get("useful_video", [])]
        if filter_tag == "photo":
            return valid_photos
        elif filter_tag == "text":
            return valid_texts
        elif filter_tag == "video":
            return valid_videos
        else:
            return {
                "useful_photo": valid_photos,
                "useful_text": valid_texts,
                "useful_video": valid_videos
            }

    elif tag == "product":
        # Фильтруем устаревшие записи для фотографий и видео
        filter_old_records(product_photos)
        filter_old_records(product_videos)
        save_storage_data()

        # Объединяем записи в один список
        products = []
        for p in product_photos:
            products.append({
                "type": "photo",
                "media": p["photo"],
                "saved_date": p["saved_date"],
                "uuid": p["uuid"]
            })
        for v in product_videos:
            products.append({
                "type": "video",
                "media": v["video"],
                "saved_date": v["saved_date"],
                "uuid": v["uuid"]
            })
        return products

    return []
