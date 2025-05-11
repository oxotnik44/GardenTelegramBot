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
product_texts = []   # Список для видео товаров


def default_serializer(obj):
    if isinstance(obj, datetime.datetime):
        return obj.isoformat()
    raise TypeError(f"Объект типа {type(obj)} не сериализуем")


def delete_record_by_storage(tag, record_uuid):
    load_storage_data()

    def remove_by_uuid(records):
        return [r for r in records if r.get("uuid") != record_uuid]

    if tag == "question":
        user_data["questions"] = remove_by_uuid(user_data["questions"])
    elif tag == "useful":
        for key in ("useful_photo", "useful_text", "useful_video"):
            user_data_useful[key] = remove_by_uuid(user_data_useful[key])
    elif tag == "product":
        global product_photos, product_videos, product_texts
        product_photos = remove_by_uuid(product_photos)
        product_videos = remove_by_uuid(product_videos)
        product_texts = remove_by_uuid(product_texts)
    else:
        print(f"⚠️ Неизвестный тег {tag}")
        return

    save_storage_data()


def load_storage_data():
    global user_data, user_data_useful, group_buffer_useful, group_buffer
    global product_photos, product_videos, product_texts

    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"⚠️ Ошибка при чтении {STORAGE_FILE}: {e}")
            return

        user_data = data.get("user_data", {"photos": [], "questions": []})
        user_data_useful = data.get("user_data_useful", {
            "useful_photo": [], "useful_text": [], "useful_video": []
        })
        group_buffer_useful = data.get("group_buffer_useful", {})
        group_buffer = data.get("group_buffer", {})
        product_photos = data.get("product_photos", [])
        product_videos = data.get("product_videos", [])
        product_texts = data.get("product_texts", [])

        def parse_dates(records):
            for r in records:
                d = r.get("saved_date")
                if isinstance(d, str):
                    try:
                        r["saved_date"] = datetime.datetime.fromisoformat(d)
                    except:
                        pass

        parse_dates(user_data.get("questions", []))
        for key in ("useful_photo", "useful_text", "useful_video"):
            parse_dates(user_data_useful.get(key, []))
        parse_dates(product_photos)
        parse_dates(product_videos)
        parse_dates(product_texts)
    else:
        print(
            f"⚠️ Файл {STORAGE_FILE} не найден. Используются значения по умолчанию.")


def save_storage_data():
    data = {
        "user_data": user_data,
        "user_data_useful": user_data_useful,
        "group_buffer_useful": group_buffer_useful,
        "group_buffer": group_buffer,
        "product_photos": product_photos,
        "product_videos": product_videos,
        "product_texts": product_texts,
    }
    try:
        with open(STORAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, default=default_serializer,
                      ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"⚠️ Ошибка при сохранении {STORAGE_FILE}: {e}")


def filter_old_records(records, days=30):
    now = datetime.datetime.now()
    filtered = []
    for r in records:
        d = r.get("saved_date")
        if isinstance(d, str):
            try:
                d = datetime.datetime.fromisoformat(d)
            except:
                continue
        if isinstance(d, datetime.datetime) and (now - d).days <= days:
            filtered.append(r)
    if len(filtered) != len(records):
        records[:] = filtered
        save_storage_data()


def save_user_message(user_id, item, tag):
    """
    Сохраняет сообщение с заданным тегом и добавляет уникальный uuid для каждой записи.
    Если item содержит ключ "caption", сохраняем его в ту же запись.
    Никогда не сохраняем в качестве текста сам тег @товары или @интересное.
    Для tag='useful' поддерживаются фото, текст и видео.
    Для tag='product' поддерживаются фото и видео.
    """
    load_storage_data()
    now = datetime.datetime.now()
    record_uuid = str(uuid.uuid4())

    # Функция проверки, является ли строка только тегом
    def is_only_tag(s: str) -> bool:
        text = s.strip().lower()
        return text in ("@товары", "@интересное")

    if tag == "useful":
        # Определяем тип полезного контента
        if "photo" in item:
            key = "useful_photo"
            value = item.get("photo")
        elif "text" in item:
            # Пропускаем, если это только тег
            if is_only_tag(item.get("text")):  # noqa
                print(
                    f"⚠️ Текст содержит только тег, пропускаем: {item.get('text')}")
                return
            key = "useful_text"
            value = item.get("text")
        elif "video" in item:
            key = "useful_video"
            value = item.get("video")
        else:
            print("⚠️ Неопределён тип полезного контента")
            return
        entry = {
            key.split('_')[1]: value,
            "saved_date": now,
            "uuid": record_uuid
        }
        # Если есть caption — проверяем, не является ли caption только тегом
        if "caption" in item and not is_only_tag(item.get("caption")):
            entry["caption"] = item["caption"]
        user_data_useful[key].append(entry)
        print(f"✅ Сохранён полезный контент: {entry}")

    elif tag == "product":
        # Фото
        if "photo" in item:
            entry = {"photo": item["photo"],
                     "saved_date": now, "uuid": record_uuid}
            if "caption" in item and not is_only_tag(item.get("caption")):
                entry["caption"] = item["caption"]
            product_photos.append(entry)
            print(f"✅ Сохранена фотография продукта: {entry}")
        # Видео
        elif "video" in item:
            entry = {"video": item["video"],
                     "saved_date": now, "uuid": record_uuid}
            if "caption" in item and not is_only_tag(item.get("caption")):
                entry["caption"] = item["caption"]
            product_videos.append(entry)
            print(f"✅ Сохранено видео продукта: {entry}")
        # Текст (с текстовыми товарами)
        elif "text" in item:
            # Пропускаем, если это только тег
            if is_only_tag(item.get("text")):
                print(
                    f"⚠️ Текст содержит только тег, пропускаем: {item.get('text')}")
                return
            entry = {"text": item["text"], "message_id": item.get("message_id"),
                     "saved_date": now, "uuid": record_uuid}
            product_texts.append(entry)
            print(f"✅ Сохранён текст продукта: {entry}")
        else:
            print("⚠️ Неизвестный формат продукта")
            return

    elif tag == "question" and isinstance(item, dict) and "text" in item:
        question_text = item["text"].strip()
        if question_text and "?" in question_text and question_text != "?":
            entry = {"user_id": user_id, "text": question_text,
                     "message_id": item.get("message_id"), "saved_date": now,
                     "uuid": record_uuid}
            user_data["questions"].append(entry)
            print(f"✅ Сохранён вопрос: {entry}")

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

        # Возвращаем сразу «сырые» записи,
        # чтобы далее в приложении можно было достать и media, и saved_date, и caption, и uuid.
        return {
            "useful_photo": user_data_useful["useful_photo"],
            "useful_text":  user_data_useful["useful_text"],
            "useful_video": user_data_useful.get("useful_video", [])
        }

    elif tag == "product":
        filter_old_records(product_photos)
        filter_old_records(product_videos)
        filter_old_records(product_texts)
        save_storage_data()

        # Возвращаем словари, чтобы сохранить caption там, где он есть
        products = []
        for p in product_photos:
            entry = {
                "type":       "photo",
                "media":      p["photo"],
                "saved_date": p["saved_date"],
                "uuid":       p["uuid"],
            }
            if "caption" in p:
                entry["caption"] = p["caption"]
            products.append(entry)

        for v in product_videos:
            entry = {
                "type":       "video",
                "media":      v["video"],
                "saved_date": v["saved_date"],
                "uuid":       v["uuid"],
            }
            if "caption" in v:
                entry["caption"] = v["caption"]
            products.append(entry)

        for t in product_texts:
            products.append({
                "type":       "text",
                "media":      t["text"],
                "message_id": t.get("message_id"),
                "saved_date": t["saved_date"],
                "uuid":       t["uuid"]
            })

        return products

    return []
