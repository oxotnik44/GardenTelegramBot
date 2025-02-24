import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Замените на ваш токен бота
TOKEN = "8016064069:AAGfeHuBipDF_8xvwtTfqNvErSVy-bPeqFs"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Привет! Используйте команду /register для регистрации.")

async def register_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # URL веб-приложения с регистрационной формой (укажите ваш домен с HTTPS)
    web_app_url = "https://your-domain.com/register"
    keyboard = [
        [InlineKeyboardButton("Открыть форму регистрации", web_app=WebAppInfo(url=web_app_url))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Пожалуйста, заполните форму регистрации:", reply_markup=reply_markup)

async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message.web_app_data:
        data = update.message.web_app_data.data
        try:
            reg_data = json.loads(data)
            login = reg_data.get("login")
            password = reg_data.get("password")
            await update.message.reply_text(
                f"Зарегистрирован:\nЛогин: {login}\nПароль: {password}"
            )
        except Exception as e:
            await update.message.reply_text("Ошибка обработки данных из веб-приложения.")

def main() -> None:
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("register", register_command))
    # Обработчик для данных, полученных из web app
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))

    app.run_polling()

if __name__ == '__main__':
    main()
