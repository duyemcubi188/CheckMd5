import csv
import datetime
import random
import re
import statistics
import binascii
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes

BOT_TOKEN = "7287917776:AAFKd8x1WY1JfnmG0POE4gm-iFAL28ir9FY"

def escape_markdown(text):
    special_chars = "_*[]()~`>#+-=|{}.!"
    for c in special_chars:
        text = text.replace(c, f"\\{c}")
    return text

def is_valid_md5(text):
    return re.match(r"^[0-9a-fA-F]{32}$", text) is not None

def analyze_md5_pro(md5):
    bytes_array = [int(md5[i:i+2], 16) for i in range(0, 32, 2)]

    avg = statistics.mean(bytes_array)
    std_dev = statistics.stdev(bytes_array)
    high_nibble_count = sum(1 for c in md5.lower() if c in "89abcdef")
    entropy = high_nibble_count / 32
    fluctuation = sum(abs(bytes_array[i+1] - bytes_array[i]) for i in range(len(bytes_array)-1))
    crc = crc16(bytes(bytes_array))

    bias_small = sum(1 for c in md5 if c in "01234567")
    bias_large = sum(1 for c in md5.lower() if c in "89abcdef")
    bias = abs(bias_small - bias_large) / 32
    repetition = max(md5.lower().count(c) for c in set(md5.lower()))

    smart_score = 0
    if entropy > 0.58:
        smart_score += 2
    if std_dev > 55:
        smart_score += 1
    if bias < 0.2:
        smart_score += 1
    if repetition < 5:
        smart_score += 1
    if crc % 2 == 0:
        smart_score += 1
    if fluctuation > 700:
        smart_score += 1

    if smart_score >= 7:
        prob = 0.95
    elif smart_score == 6:
        prob = 0.9
    elif smart_score == 5:
        prob = 0.85
    elif smart_score == 4:
        prob = 0.8
    elif smart_score == 3:
        prob = 0.7
    elif smart_score == 2:
        prob = 0.6
    else:
        prob = 0.5

    result = "Tài" if prob >= 0.5 else "Xỉu"
    confidence = (
        "Very High 🔥" if prob >= 0.9 else
        "High 💪" if prob >= 0.8 else
        "Medium 🧠" if prob >= 0.7 else
        "Low 🫣"
    )

    method = f"Entropy={entropy:.3f} | StdDev={std_dev:.1f} | Bias={bias:.2f} | Fluct={fluctuation} | CRC16={crc}"

    return result, prob, confidence, method

def simulate_dice(result):
    min_total = 11 if result == "Tài" else 3
    max_total = 18 if result == "Tài" else 10

    while True:
        d1, d2, d3 = random.randint(1, 6), random.randint(1, 6), random.randint(1, 6)
        total = d1 + d2 + d3
        if min_total <= total <= max_total:
            return d1, d2, d3, total

def get_dice_emoji(num):
    emojis = ["", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"]
    return emojis[num]

def suggest_bet(prob):
    if prob >= 0.9:
        return "Cược mạnh 🔥"
    elif prob >= 0.8:
        return "Cược mạnh 💪"
    elif prob >= 0.7:
        return "Cược nhẹ 🧠"
    else:
        return "Không cược 🚫"

def crc16(data: bytes):
    crc = 0xFFFF
    for b in data:
        crc ^= b << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = (crc << 1) ^ 0x1021
            else:
                crc <<= 1
            crc &= 0xFFFF
    return crc

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    chat_id = update.message.chat_id

    if not is_valid_md5(text):
        await context.bot.send_message(
            chat_id=chat_id,
            text="⚠️ Lỗi: Chuỗi gửi không phải MD5 hợp lệ (32 ký tự hex).",
            parse_mode=ParseMode.HTML
        )
        return

    result, prob, confidence, method = analyze_md5_pro(text)
    d1, d2, d3, total = simulate_dice(result)

    message = f"""
🎯 <b>Dự đoán Tài/Xỉu từ MD5</b>

🔐 <b>MD5:</b> <code>{text}</code>

🎲 <b>Xúc xắc:</b> {d1}, {d2}, {d3} → <b>Tổng:</b> {total}
🎰 <b>Mô phỏng xúc xắc:</b> {get_dice_emoji(d1)} {get_dice_emoji(d2)} {get_dice_emoji(d3)}

📈 <b>Dự đoán:</b> {result.upper()}
🏷️ <b>Độ tin cậy:</b> {confidence} ({prob * 100:.1f}%)

⚙️ <b>Phân tích thêm:</b> {method}

💡 <b>Gợi ý:</b> {suggest_bet(prob)}

🕰️ <i>{datetime.datetime.utcnow().strftime('%H:%M:%S %d/%m/%Y')}</i>

👨‍💻 <b>Dev:</b> Ngô Đức Duy
📡 <b>Admin:</b> <a href="https://www.facebook.com/profile.php?id=100073200452769">Facebook</a>
💡 <b>Cre:</b> duyemcubi188
    """

    await context.bot.send_message(chat_id=chat_id, text=message, parse_mode=ParseMode.HTML)

    # Save to history
    save_history(text, result, prob, confidence, method)

def save_history(md5, result, prob, confidence, method):
    with open("history.csv", mode="a", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'), md5, result, f"{prob*100:.1f}%", confidence, method])

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Bot Telegram đã khởi động...")
    app.run_polling()

if __name__ == "__main__":
    main()
