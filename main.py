from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from config import TOKEN
from handlers import question, handle_text, handle_photo, button_callback, products


def main() -> None:
    app = Application.builder().token(TOKEN).build()

    # Регистрируем обработчики команд и сообщений
    # Вызываем question, который будет сразу показывать вопросы
    app.add_handler(CommandHandler("question", question))
    app.add_handler(CommandHandler("products", products))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(button_callback))

    app.run_polling()


if __name__ == '__main__':
    main()
