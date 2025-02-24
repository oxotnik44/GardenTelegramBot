import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, LabeledPrice
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Замените TOKEN на ваш токен, а PROVIDER_TOKEN на ваш платежный токен (если есть)
TOKEN = "8016064069:AAGfeHuBipDF_8xvwtTfqNvErSVy-bPeqFs"
PROVIDER_TOKEN = "YOUR_PROVIDER_TOKEN"  # Если не настроено — оставить как есть

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Привет! Используйте команду /shop для просмотра товаров.")

async def shop_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # URL веб-приложения с магазином (страница должна быть доступна по HTTPS, например через GitHub Pages)
    web_app_url = "https://oxotnik44.github.io/GardenTelegramBot/"
    keyboard = [
        [InlineKeyboardButton("Открыть магазин", web_app=WebAppInfo(url=web_app_url))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите товар для покупки:", reply_markup=reply_markup)

async def web_app_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Обработка данных, полученных из веб-приложения
    if update.message.web_app_data:
        data = update.message.web_app_data.data
        try:
            product = json.loads(data)
            name = product.get("name")
            price = product.get("price")
            # Если у вас настроена система оплаты, можно отправить счёт (инвойс):
            # await context.bot.send_invoice(
            #     chat_id=update.effective_chat.id,
            #     title=name,
            #     description=f"Покупка товара: {name}",
            #     payload="Custom-Payload",
            #     provider_token=PROVIDER_TOKEN,
            #     currency="RUB",
            #     prices=[LabeledPrice(name, int(price) * 100)],  # цена в копейках
            #     start_parameter="test-payment"
            # )
            # Если оплата не настроена, просто выводим информацию:
            await update.message.reply_text(
                f"Вы выбрали товар:\nНазвание: {name}\nЦена: {price} RUB\nОплата в разработке."
            )
        except Exception as e:
            await update.message.reply_text("Ошибка обработки данных из веб-приложения.")

def main() -> None:
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("shop", shop_command))
    # Обработчик для данных, полученных из Web App
    app.add_handler(MessageHandler(filters.StatusUpdate.WEB_APP_DATA, web_app_data_handler))

    app.run_polling()

if __name__ == '__main__':
    main()
