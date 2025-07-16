from telegram.ext import Application, CommandHandler, MessageHandler, filters
import requests
import json
import time
import os

# Cấu hình
TELEGRAM_TOKEN = '7121962149:AAHpzCYy-4KrWILDXQoV9woV3J5oI77wELE'
OCR_API_KEY = 'K88631585888957'
CV_IMAGE_PATH = os.path.join(os.path.dirname(__file__), 'cv.jpg')
USER_DATA_FILE = "user_data.json"

# Load dữ liệu người dùng từ file
def load_user_data():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    return {}

# Lưu dữ liệu người dùng vào file
def save_user_data(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f)

# Hàm khởi động bot
async def start(update, context):
    await update.message.reply_text(
        "🎉 Chào mừng bạn đến với bot OCR!\nGửi ảnh để tách chữ.\nDùng /info để xem số lượt còn lại."
    )
    if os.path.exists(CV_IMAGE_PATH):
        await update.message.reply_photo(photo=open(CV_IMAGE_PATH, 'rb'), caption="🪪 Đây là ảnh CV!")

# Hàm kiểm tra lượt còn lại
async def info(update, context):
    user_id = str(update.message.from_user.id)
    user_data = load_user_data()
    current_time = time.time()

    if user_id in user_data:
        count, timestamp = user_data[user_id]
        if current_time - timestamp < 600:
            remaining = 30 - int(count)
            await update.message.reply_text(f"Bạn còn {remaining} lượt trong 10 phút.")
            return

    await update.message.reply_text("Bạn có 30 lượt mới trong 10 phút!")

# Xử lý ảnh
async def handle_image(update, context):
    user_id = str(update.message.from_user.id)
    user_data = load_user_data()
    current_time = time.time()

    count, timestamp = user_data.get(user_id, (0, current_time))

    if current_time - timestamp < 600:
        if count >= 30:
            time_left = int(600 - (current_time - timestamp))
            await update.message.reply_text(f"🚫 Bạn đã dùng hết 30 lượt. Vui lòng chờ {time_left} giây.")
            return
        count += 1
    else:
        count = 1
        timestamp = current_time

    user_data[user_id] = (count, timestamp)
    save_user_data(user_data)

    await update.message.reply_text("⏳ Đang xử lý ảnh...")

    try:
        file = await context.bot.get_file(update.message.photo[-1].file_id)
        image_data = await file.download_as_bytearray()

        ocr_response = requests.post(
            'https://api.ocr.space/parse/image',
            files={'image': ('image.jpg', image_data)},
            data={'apikey': OCR_API_KEY}
        )
        result = ocr_response.json()

        if result.get('IsErroredOnProcessing'):
            await update.message.reply_text("❌ Lỗi khi xử lý ảnh!")
            return

        text = result.get('ParsedResults', [{}])[0].get('ParsedText', '')
        if not text:
            await update.message.reply_text("🧐 Ảnh không chứa văn bản.")
            return

        await update.message.reply_text("📄 Kết quả OCR:\n" + text)

    except Exception as e:
        await update.message.reply_text(f"Lỗi: {e}")

# Chạy bot
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(MessageHandler(filters.PHOTO, handle_image))
    app.run_polling()

if __name__ == '__main__':
    main()
