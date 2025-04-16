import datetime
import asyncio
from modules.storage import save_user_message

# Хранилище для групп видео (если его нет в modules.storage, можно объявить здесь)
group_video_buffer = {}


async def handle_video(update, context, force_tag: bool = False, single_tag: str = None):
    """
    Обрабатывает входящие видео.
    Если видео отправлено в одиночку – сохраняет сразу;
    если это часть альбома (media_group) – группирует и ждёт завершения группы.
    Можно передать конкретный тег single_tag (@товары или @интересное), чтобы не искать его в caption.
    """
    user_id = update.message.from_user.id
    video_file_id = update.message.video.file_id
    caption = update.message.caption or ""
    media_group_id = update.message.media_group_id

    # Приводим caption к нижнему регистру и убираем лишние пробелы
    caption = caption.strip().lower()

    # Определяем тег: либо передан явно, либо ищем в caption
    tag = None
    if single_tag in ["@товары", "@интересное"]:
        tag = single_tag
    elif force_tag:
        # Если force_tag включён, но конкретный тег не передан, можно взять из caption
        if "@товары" in caption:
            tag = "@товары"
        elif "@интересное" in caption:
            tag = "@интересное"
    else:
        # Если нет force_tag и нет single_tag — ищем по caption
        if "@товары" in caption:
            tag = "@товары"
        elif "@интересное" in caption:
            tag = "@интересное"

    if media_group_id is None:
        # Одиночное видео
        if tag == "@товары":
            save_user_message(
                user_id, {"video": video_file_id, "tags": [tag]}, "product")
        elif tag == "@интересное":
            save_user_message(
                user_id, {"video": video_file_id, "tags": [tag]}, "useful")
        else:
            # Если тег явно не указан – сохраняем как товары по умолчанию
            save_user_message(
                user_id, {"video": video_file_id, "tags": []}, "product")
    else:
        # Если видео является частью альбома
        key = (user_id, media_group_id)
        if key not in group_video_buffer:
            group_video_buffer[key] = {
                "videos": [],
                "has_product": False,
                "has_useful": False,
                "task": None,
                "created_at": datetime.datetime.now()
            }

        group_info = group_video_buffer[key]
        group_info["videos"].append(video_file_id)

        if force_tag or tag == "@товары":
            group_info["has_product"] = True
        if force_tag or tag == "@интересное":
            group_info["has_useful"] = True

        if group_info["task"] is not None:
            group_info["task"].cancel()
        group_info["task"] = context.application.create_task(
            group_flush_delayed_video(user_id, media_group_id)
        )


async def group_flush_delayed_video(user_id, media_group_id):
    """
    Завершает группировку и сохраняет видео из альбома по завершении задержки.
    Задержка даёт время собрать все видео из альбома.
    """
    await asyncio.sleep(2)
    key = (user_id, media_group_id)
    group_info = group_video_buffer.get(key)
    if group_info:
        # Если группа содержит тег @товары, сохраняем все видео в категорию "product"
        if group_info["has_product"]:
            for video in group_info["videos"]:
                item = {"video": video, "tags": ["@товары"]}
                save_user_message(user_id, item, "product")
        # Если группа содержит тег @интересное, сохраняем все видео в категорию "useful"
        if group_info["has_useful"]:
            for video in group_info["videos"]:
                item = {"video": video, "tags": ["@интересное"]}
                save_user_message(user_id, item, "useful")
        # Удаляем группу из буфера после обработки
        if key in group_video_buffer:
            del group_video_buffer[key]
