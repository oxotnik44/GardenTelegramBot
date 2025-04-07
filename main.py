import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import TOKEN
from handlers import handle_text, button_callback, products, useful, question, start
from modules.photo_handler import handle_photo
from modules.useful_handler import handle_photo_useful

# Глобальные переменные для состояния
first_photo_has_tag = None
reset_task = None  # Задача сброса first_photo_has_tag

pending_tag = False
pending_interesting = False
pending_reset_task = None  # Таймер сброса pending_*


async def reset_pending_flags():
    """Сбрасывает флаги pending_tag и pending_interesting через 10 секунд без новых фото."""
    try:
        await asyncio.sleep(10)
    except asyncio.CancelledError:
        # Если таймер отменен — просто выходим
        return
    global pending_tag, pending_interesting, pending_reset_task
    print("Таймер ожидания фото истек. Флаги сброшены.")
    pending_tag = False
    pending_interesting = False
    pending_reset_task = None  # Очистка задачи


async def reset_first_photo_flag():
    """Сбрасывает флаг first_photo_has_tag через 10 секунд."""
    global first_photo_has_tag, reset_task
    await asyncio.sleep(10)
    first_photo_has_tag = None
    reset_task = None  # Очистка задачи


async def text_message_handler(update, context):
    """
    Обработчик текстовых сообщений.
    Если сообщение содержит теги "@товары" или "@интересное", устанавливает флаги.
    """
    global pending_tag, pending_interesting, pending_reset_task, first_photo_has_tag
    text = update.message.text.lower()

    # Сбрасываем first_photo_has_tag, чтобы использовать новый тег
    first_photo_has_tag = None

    if "@товары" in text:
        print("Найдено сообщение @товары")
        pending_tag = True
        pending_interesting = False  # Дополнительно можно сбрасывать другой флаг, если нужно
    if "@интересное" in text:
        print("Найдено сообщение @интересное")
        pending_interesting = True
        pending_tag = False

    # Отменяем предыдущий таймер и запускаем новый
    if pending_reset_task:
        pending_reset_task.cancel()
    pending_reset_task = asyncio.create_task(reset_pending_flags())

    await handle_text(update, context)


async def handle_photo_with_tag(update, context):
    """
    Обрабатывает фото и проверяет наличие тегов @товары или @интересное.
    Теперь при каждом новом фото, если в подписи присутствует явный тег,
    значение first_photo_has_tag обновляется, а таймер его сброса перезапускается.
    """
    global first_photo_has_tag, pending_tag, pending_interesting, pending_reset_task, reset_task

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
        # Если в новом фото явно указан тег, обновляем first_photo_has_tag
        if "@товары" in message_text:
            first_photo_has_tag = True
        elif "@интересное" in message_text:
            first_photo_has_tag = False

        # Если тег так и не был определён, можно задать значение по умолчанию (например, False)
        if first_photo_has_tag is None:
            first_photo_has_tag = False

        # Перезапускаем таймер сброса first_photo_has_tag
        if reset_task:
            reset_task.cancel()
        reset_task = asyncio.create_task(reset_first_photo_flag())

        if first_photo_has_tag:
            print(
                f"Тег @товары найден. Фото в handle_photo. ID: {update.message.photo[-1].file_id}")
            await handle_photo(update, context)
        else:
            print(
                f"Тег @товары не найден. Фото в handle_photo_useful. ID: {update.message.photo[-1].file_id}")
            await handle_photo_useful(update, context)

    # Перезапускаем таймер сброса pending_* на 10 секунд
    if pending_reset_task:
        pending_reset_task.cancel()
    pending_reset_task = asyncio.create_task(reset_pending_flags())


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

    print("Бот запущен!")
    app.run_polling()


if __name__ == '__main__':
    main()
