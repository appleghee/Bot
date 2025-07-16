from telegram.ext import Application, CommandHandler, MessageHandler, Filters
import requests
import redis
import time
import os

# Cấu hình
TELEGRAM_TOKEN = '7121962149:AAHpzCYy-4KrWILDXQoV9woV3J5oI77wELE'
OCR_API_KEY = 'K88631585888957'
CV_IMAGE_PATH = 'cv.jpg'  # Thay bằng đường dẫn file hoặc URL của cv.jpg
REDIS_CLIENT = redis.Redis(host='localhost', port=6379, db=0)

# Hàm khởi động bot
async def start(update, context):
    await update.message.reply_text(
        "Chào mừng bạn đến với bot OCR! Gửi ảnh để tách chữ. Dùng /info để xem số lượt còn lại."
    )
    # Gửi ảnh cv.jpg
    if os.path.exists(CV_IMAGE_PATH):
        await update.message.reply_photo(photo=open(CV_IMAGE_PATH, 'rb'), caption="Đây là ảnh CV!")
    else:
        await update.message.reply_text("Không tìm thấy ảnh CV. Vui lòng liên hệ admin!")

# Hàm kiểm tra số lượt còn lại
async def info(update, context):
    user_id = str(update.message.from_user.id)
    current_time = time.time()
    
    user_requests = REDIS_CLIENT.get(user_id)
    if user_requests:
        count, timestamp = map(float, user_requests.decode().split(':'))
        if current_time - timestamp < 600:  # 10 phút
            remaining = 30 - int(count)
            if remaining > 0:
                await update.message.reply_text(f"Bạn còn {remaining} lượt trong 10 phút.")
            else:
                time_left = int(600 - (current_time - timestamp))
                await update.message.reply_text(f"Bạn đã dùng hết 30 lượt. Vui lòng chờ {time_left} giây!")
        else:
            REDIS_CLIENT.set(user_id, f"0:{current_time}")
            await update.message.reply_text("Bạn có 30 lượt mới trong 10 phút!")
    else:
        await update.message.reply_text("Bạn có 30 lượt trong 10 phút!")

# Hàm xử lý ảnh
async def handle_image(update, context):
    user_id = str(update.message.from_user.id)
    current_time = time.time()
    
    # Kiểm tra giới hạn
    user_requests = REDIS_CLIENT.get(user_id)
    if user_requests:
        count, timestamp = map(float, user_requests.decode().split(':'))
        if current_time - timestamp < 600:  # 10 phút
            if count >= 30:
                time_left = int(600 - (current_time - timestamp))
                await update.message.reply_text(f"Bạn đã dùng hết 30 lượt. Vui lòng chờ {time_left} giây!")
                return
            else:
                REDIS_CLIENT.set(user_id, f"{count + 1}:{timestamp}")
                if 30 - (count + 1) <= 5:
                    await update.message.reply_text(f"Cảnh báo: Bạn còn {30 - (count + 1)} lượt!")
        else:
            REDIS_CLIENT.set(user_id, f"1:{current_time}")
    else:
        REDIS_CLIENT.set(user_id, f"1:{current_time}")

    # Thông báo đang xử lý
    await update.message.reply_text("Đang xử lý ảnh, vui lòng chờ...")
    
    # Tải ảnh
    file = await context.bot.get_file(update.message.photo[-1].file_id)
    image_data = await file.download_as_bytearray()
    
    # Gọi API OCR
    try:
        ocr_response = requests.post(
            'https://api.ocr.space/parse/image',
            files={'image': ('image.jpg', image_data)},
            data={'apikey': OCR_API_KEY}
        )
        result = ocr_response.json()
        
        if result.get('IsErroredOnProcessing'):
            await update.message.reply_text("Có lỗi khi xử lý ảnh, vui lòng thử lại!")
            return
        
        text = result.get('ParsedResults', [{}])[0].get('ParsedText', '')
        if not text:
            await update.message.reply_text("Ảnh không chứa văn bản, vui lòng thử lại!")
            return
        
        await update.message.reply_text(text)
    
    except Exception as e:
        await update.message.reply_text(f"Lỗi: {str(e)}. Vui lòng thử lại!")

# Khởi động bot
def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Đăng ký handlers
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('info', info))
    app.add_handler(MessageHandler(Filters.photo, handle_image))
    
    # Khởi động
    app.run_polling()

if __name__ == '__main__':
    main()
