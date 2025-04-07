import datetime
import uuid
import json
import os

STORAGE_FILE = "storageData.json"

# Глобальные переменные по умолчанию
user_data = {"photos": [], "questions": []}
user_data_useful = {"useful_photo": [], "useful_text": []}
group_buffer_useful = {}
group_buffer = {}
product_photos = []  # Глобальный список для хранения фотографий продуктов


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
        print(f"🗑 Удалены полезные данные с uuid {record_uuid} (если были)")

    elif tag == "product":
        global product_photos
        product_photos = remove_by_uuid(product_photos)
        print(f"🗑 Удалена фотография продукта с uuid {record_uuid}")

    else:
        print(f"⚠️ Неизвестный тег {tag}")
        return

    save_storage_data()


def load_storage_data():
    """
    Загружает данные из файла STORAGE_FILE и обновляет глобальные переменные.
    Если файл не найден, остаются значения по умолчанию.
    """
    global user_data, user_data_useful, group_buffer_useful, group_buffer, product_photos
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            user_data = data.get("user_data", {"photos": [], "questions": []})
            user_data_useful = data.get(
                "user_data_useful", {"useful_photo": [], "useful_text": []})
            group_buffer_useful = data.get("group_buffer_useful", {})
            group_buffer = data.get("group_buffer", {})
            product_photos = data.get("product_photos", [])
            # Преобразуем строки дат обратно в datetime, если требуется для фильтрации
            for q in user_data.get("questions", []):
                if isinstance(q.get("saved_date"), str):
                    try:
                        q["saved_date"] = datetime.datetime.fromisoformat(
                            q["saved_date"])
                    except Exception:
                        pass
            for key in ("useful_photo", "useful_text"):
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
    records[:] = filtered


def save_user_message(user_id, item, tag):
    """
    Сохраняет сообщение с заданным тегом и добавляет уникальный uuid для каждой записи.
    Данные обновляются из файла и сохраняются обратно после внесения изменений.
    """
    load_storage_data()  # Получаем актуальные данные из файла
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
        key = "useful_photo" if "photo" in item else "useful_text"
        value = item.get(
            "photo") if key == "useful_photo" else item.get("text")
        user_data_useful[key].append({
            ("photo" if key == "useful_photo" else "text"): value,
            "saved_date": now,
            "uuid": record_uuid
        })
        print(
            f"✅ Сохранён {'фото' if key == 'useful_photo' else 'текст'}: {value}")

    elif tag == "product":
        product_photos.append({
            "photo": item,
            "saved_date": now,
            "uuid": record_uuid
        })
        print("✅ Сохранена фотография продукта")

    else:
        print(f"⚠️ Неизвестный тег {tag}")
        return

    save_storage_data()  # Сохраняем обновлённые данные в файл


def get_user_message(tag, filter_tag=None):
    """
    Загружает данные из файла STORAGE_FILE, обновляет глобальные переменные,
    фильтрует устаревшие записи и возвращает список элементов по тегу.
    """
    load_storage_data()  # Обновляем данные из файла

    if tag == "question":
        filter_old_records(user_data["questions"])
        save_storage_data()
        return user_data["questions"]

    elif tag == "useful":
        filter_old_records(user_data_useful["useful_photo"])
        filter_old_records(user_data_useful["useful_text"])
        save_storage_data()
        valid_photos = [r["photo"] for r in user_data_useful["useful_photo"]]
        valid_texts = [r["text"] for r in user_data_useful["useful_text"]]
        if filter_tag == "photo":
            return valid_photos
        elif filter_tag == "text":
            return valid_texts
        else:
            return {"useful_photo": valid_photos, "useful_text": valid_texts}

    elif tag == "product":
        filter_old_records(product_photos)
        save_storage_data()
        return [p["photo"] for p in product_photos]

    return []
