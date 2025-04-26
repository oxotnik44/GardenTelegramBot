from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import ALLOWED_USER_IDS, TOKEN
from handlers import handle_text, button_callback, products, useful, question, start
from modules.photo_handler import handle_photo
from modules.useful_handler import handle_photo_useful
from modules.video_handler import handle_video

# Глобальные переменные для состояния фото
first_photo_has_tag = None
# Флаги, устанавливаемые текстовыми сообщениями
pending_tag = False
pending_interesting = False

# Глобальные переменные для состояния видео
first_video_has_tag = None

# Список разрешённых пользователей


async def handle_video_with_tag(update, context):
    global first_video_has_tag, pending_tag, pending_interesting

    # Проверка разрешения по user_id
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USER_IDS:
        print(f"Пользователь {user_id} не имеет права отправлять видео.")
        return

    message_text = update.message.caption.lower() if update.message.caption else ""

    tag = None

    if pending_tag:
        tag = "@товары"
        print(
            f"Видео после текста с @товары. Обработка с single_tag='@товары'. ID: {update.message.video.file_id}")
    elif pending_interesting:
        tag = "@интересное"
        print(
            f"Видео после текста с @интересное. Обработка с single_tag='@интересное'. ID: {update.message.video.file_id}")
    else:
        if "@товары" in message_text:
            tag = "@товары"
            first_video_has_tag = True
        elif "@интересное" in message_text:
            tag = "@интересное"
            first_video_has_tag = False
        else:
            first_video_has_tag = False
            print(
                f"⚠️ Видео не содержит тега — пропускаем. ID: {update.message.video.file_id}")
            return

    await handle_video(update, context, single_tag=tag)


async def text_message_handler(update, context):
    global pending_tag, pending_interesting, first_photo_has_tag
    text = update.message.text.lower()

    first_photo_has_tag = None

    if "@товары" in text:
        print("Найдено сообщение @товары")
        pending_tag = True
        pending_interesting = False
    elif "@интересное" in text:
        print("Найдено сообщение @интересное")
        pending_interesting = True
        pending_tag = False
    else:
        pending_tag = False
        pending_interesting = False
        print("Сообщение не содержит тегов, сброс флагов")

    await handle_text(update, context)


async def handle_photo_with_tag(update, context):
    global first_photo_has_tag, pending_tag, pending_interesting

    # Проверка разрешения по user_id
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USER_IDS:
        print(f"Пользователь {user_id} не имеет права отправлять фото.")
        return

    message_text = update.message.caption.lower() if update.message.caption else ""

    if pending_tag:
        print(
            f"Фото после @товары. Обработка в handle_photo. ID: {update.message.photo[-1].file_id}")
        await handle_photo(update, context, force_tag=True)
    elif pending_interesting:
        print(
            f"Фото после @интересное. Обработка в handle_photo_useful. ID: {update.message.photo[-1].file_id}")
        await handle_photo_useful(update, context, force_tag=True)
    else:
        if "@товары" in message_text:
            first_photo_has_tag = True
        elif "@интересное" in message_text:
            first_photo_has_tag = False

        if first_photo_has_tag is None:
            first_photo_has_tag = False

        if first_photo_has_tag:
            print(
                f"Тег @товары найден. Фото в handle_photo. ID: {update.message.photo[-1].file_id}")
            await handle_photo(update, context)
        else:
            print(
                f"Тег @товары не найден. Фото в handle_photo_useful. ID: {update.message.photo[-1].file_id}")
            await handle_photo_useful(update, context)


def main() -> None:
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("question", question))
    app.add_handler(CommandHandler("products", products))
    app.add_handler(CommandHandler("useful", useful))
    app.add_handler(CommandHandler("start", start))

    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_with_tag))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, text_message_handler))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video_with_tag))

    print("Бот запущен!")
    app.run_polling()


if __name__ == '__main__':
    main()
