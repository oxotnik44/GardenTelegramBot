from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import TOKEN
from handlers import handle_text, button_callback, products, useful, question
from modules.photo_handler import handle_photo


def main() -> None:
    app = Application.builder().token(TOKEN).build()

    # Регистрируем обработчики команд и сообщений
    app.add_handler(CommandHandler("question", question))
    app.add_handler(CommandHandler("products", products))
    app.add_handler(CommandHandler("useful", useful))

    # Обработчик всех фото сразу направляем в handle_photo
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Обработка текста и кнопок
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(button_callback))

    # Запуск приложения
    app.run_polling()


if __name__ == '__main__':
    main()
