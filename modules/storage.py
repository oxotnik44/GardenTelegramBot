import datetime

user_data = {}
user_data_useful = {}
group_buffer_useful = {}
group_buffer = {}


def save_user_message(user_id, item, tag, tags=None):
    """Сохраняет сообщение пользователя, фото или полезную информацию в зависимости от переданного тега."""
    if tag == "question":
        # Проверяем, что item — это словарь, содержащий текст и знак вопроса
        if isinstance(item, dict) and "text" in item and "?" in item["text"]:
            user_data.setdefault(user_id, {"photos": [], "questions": []})[
                "questions"].append(item)
            print(
                f"Сохранён вопрос для пользователя {user_id}: {item['text']}")
        else:
            print(
                f"Некорректный формат вопроса для пользователя {user_id}: {item}")

    elif tag == "useful":
        # Сохраняем полезную информацию
        user_data_useful.setdefault(user_id, {"items": []})[
            "items"].append(item)
        print(f"Сохранён полезный элемент для пользователя {user_id}: {item}")

    elif tag == "product":
        # Сохраняем фото с дополнительными тегами, если они есть
        tags = tags or []  # Используем пустой список, если тегов нет
        user_data.setdefault(user_id, {"photos": [], "questions": []})["photos"].append(
            (datetime.datetime.now(), item, tags)
        )
        print(
            f"Сохранено фото для пользователя {user_id} с item {item} и тегами {tags}")

    else:
        print(f"Неизвестный тег {tag} для пользователя {user_id}")


def get_user_message(user_id, tag, filter_tag=None):
    """
    Возвращает список элементов пользователя в зависимости от тега ('useful', 'question', 'photo'),
    и фильтрует фотографии по тегу и дате, если передан filter_tag.
    """
    # Проверяем, если тег "useful" или "question", то возвращаем соответствующие данные
    if tag == "useful":
        return user_data_useful.get(user_id, {}).get("items", [])
    elif tag == "question":
        return user_data.get(user_id, {}).get("questions", [])

    # Если тег "product", фильтруем фотографии по тегу и дате, если передан filter_tag
    if tag == "product":
        photos = user_data.get(user_id, {}).get("photos", [])

        if filter_tag:
            now = datetime.datetime.now()
            return [
                file_id
                for (time, file_id, tags) in photos
                if (now - time) <= datetime.timedelta(days=45) and filter_tag in tags
            ]

        return photos  # Возвращаем все фото, если filter_tag не передан

    # Если тег неизвестен, возвращаем пустой список
    print(f"Неправильный тег: {tag}")
    return []
