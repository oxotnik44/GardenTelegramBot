from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import TOKEN
from handlers import handle_text,  button_callback, products, useful
from modules.question_handler import question
from modules.useful_handler import handle_photo_useful
from modules.photo_handler import handle_photo


async def handle_photo_dispatcher(update, context):
    """Обрабатывает фото в зависимости от caption."""
    caption = (update.message.caption or "").strip().lower()

    # Если в caption есть тег "@интересная информация", отправляем в обработчик useful
    if "@интересная информация" in caption:
        await handle_photo_useful(update, context)
    else:
        # В противном случае отправляем в основной обработчик
        await handle_photo(update, context)


def main() -> None:
    app = Application.builder().token(TOKEN).build()

    # Регистрируем обработчики команд и сообщений
    # Вызываем question, который будет сразу показывать вопросы
    app.add_handler(CommandHandler("question", question))
    app.add_handler(CommandHandler("products", products))
    app.add_handler(CommandHandler("useful", useful))

    # Один обработчик для всех фото
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo_dispatcher))

    # Обработка текста и кнопок
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(button_callback))

    # Запуск приложения
    app.run_polling()


if __name__ == '__main__':
    main()
