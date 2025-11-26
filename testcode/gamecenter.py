import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import mysql.connector
from mysql.connector import Error
import json
import logging

# تنظیمات
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# توکن ربات - اینجا باید توکن واقعی رو قرار بدی
BOT_TOKEN = "8204768526:AAFoUlfWEGAaGz5HT15qr9menwd54RKxwSE"

# تنظیمات دیتابیس
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "y13791029f",
    "database": "game_center_bot",
}

# ایجاد ربات
bot = telebot.TeleBot(BOT_TOKEN)


class DatabaseManager:
    def __init__(self):
        self.connection = None

    def connect(self):
        try:
            self.connection = mysql.connector.connect(**DB_CONFIG)
            return self.connection
        except Error as e:
            logger.error(f"Database connection error: {e}")
            return None

    def disconnect(self):
        if self.connection and self.connection.is_connected():
            self.connection.close()


# مدیریت کاربران - تصحیح شده
class UserManager:
    def __init__(self):
        self.db = DatabaseManager()

    def register_user(self, message):
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name

        conn = self.db.connect()
        if not conn:
            return False

        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT IGNORE INTO tg_users (user_id, username, first_name, last_name)
                VALUES (%s, %s, %s, %s)
            """,
                (user_id, username, first_name, last_name),
            )

            cursor.execute(
                """
                INSERT IGNORE INTO user_states (user_id, current_state)
                VALUES (%s, 'main_menu')
            """,
                (user_id,),
            )

            conn.commit()
            logger.info(f"User {user_id} registered successfully")
            return True
        except Error as e:
            logger.error(f"User registration error: {e}")
            return False
        finally:
            if cursor:
                cursor.close()
            self.db.disconnect()


# منوی اصلی
def main_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("🎮 بازی‌ها", callback_data="category_games"),
        InlineKeyboardButton(
            "💻 لپتاپ گیمینگ", callback_data="category_laptops"),
        InlineKeyboardButton("🕹 کنسول گیم", callback_data="category_consoles"),
        InlineKeyboardButton("🛒 سبد خرید", callback_data="view_cart"),
        InlineKeyboardButton("📋 سفارشات من", callback_data="my_orders"),
    )
    return keyboard


# دستور start
@bot.message_handler(commands=["start"])
def start_command(message):
    try:
        user_manager = UserManager()
        success = user_manager.register_user(message)

        welcome_text = """
🎮 به گیم سنتر خوش آمدید!

🔥 بهترین بازی‌ها و تجهیزات گیمینگ
💻 لپتاپ‌های گیمینگ قدرتمند
🕹 کنسول‌های بازی جدید

از منوی زیر انتخاب کنید:
"""

        if success:
            bot.send_message(message.chat.id, welcome_text,
                             reply_markup=main_menu())
        else:
            bot.send_message(
                message.chat.id, "❌ خطا در ثبت اطلاعات. لطفا مجددا تلاش کنید."
            )

    except Exception as e:
        logger.error(f"Start command error: {e}")
        bot.send_message(message.chat.id, "❌ خطا در پردازش درخواست.")


# هندلر دکمه‌های اینلاین - تصحیح شده
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    try:
        data = call.data

        if data.startswith("category_"):
            show_category_products(call)
        elif data == "view_cart":
            show_cart(call)
        elif data == "my_orders":
            show_orders(call)
        elif data == "back_to_main":
            # استفاده از send_message به جای edit_message_text
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(
                call.message.chat.id, "🎮 منوی اصلی گیم سنتر:", reply_markup=main_menu()
            )
        elif data == "checkout":
            bot.answer_callback_query(
                call.id, "🚧 بخش پرداخت به زودی فعال می‌شود")

    except Exception as e:
        logger.error(f"Callback error: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در پردازش")


# نمایش محصولات هر دسته - تصحیح شده
def show_category_products(call):
    try:
        category = call.data.replace("category_", "")

        db = DatabaseManager()
        conn = db.connect()

        cursor = conn.cursor(dictionary=True)

        if category == "games":
            cursor.execute(
                "SELECT * FROM games WHERE is_available = TRUE LIMIT 5")
            products = cursor.fetchall()
            title = "🎮 بازی‌های موجود:\n(برای مشاهده جزئیات کلیک کنید)"

        elif category == "laptops":
            cursor.execute(
                "SELECT * FROM gaming_laptops WHERE is_available = TRUE LIMIT 5"
            )
            products = cursor.fetchall()
            title = "💻 لپتاپ‌های گیمینگ:\n(برای مشاهده جزئیات کلیک کنید)"

        elif category == "consoles":
            cursor.execute(
                "SELECT * FROM consoles WHERE is_available = TRUE LIMIT 5")
            products = cursor.fetchall()
            title = "🕹 کنسول‌های بازی:\n(برای مشاهده جزئیات کلیک کنید)"
        else:
            title = "دسته‌بندی یافت نشد"
            products = []

        keyboard = InlineKeyboardMarkup(row_width=1)

        for product in products:
            if category == "games":
                name = product["game_name"]
                price = product["price"]
                item_id = product["game_id"]
            elif category == "laptops":
                name = product["laptop_name"]
                price = product["price"]
                item_id = product["laptop_id"]
            else:
                name = product["console_name"]
                price = product["price"]
                item_id = product["console_id"]

            button_text = f"{name} - {price:,} تومان"
            callback_data = f"product_{category}_{item_id}"
            keyboard.add(InlineKeyboardButton(
                button_text, callback_data=callback_data))

        keyboard.add(
            InlineKeyboardButton("🔙 بازگشت به منوی اصلی",
                                 callback_data="back_to_main")
        )

        # حذف پیام قبلی و ارسال پیام جدید
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, title, reply_markup=keyboard)

    except Error as e:
        logger.error(f"Error showing products: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در دریافت محصولات")
    finally:
        if "cursor" in locals():
            cursor.close()
        if "db" in locals():
            db.disconnect()


# نمایش سبد خرید - تصحیح شده
def show_cart(call):
    try:
        user_id = call.from_user.id
        db = DatabaseManager()
        conn = db.connect()

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM cart WHERE user_id = %s", (user_id,))

        cart_items = cursor.fetchall()

        if not cart_items:
            text = "🛒 سبد خرید شما خالی است\n\nبرای اضافه کردن محصول به سبد خرید، از منوی اصلی دسته‌بندی مورد نظر را انتخاب کنید."
        else:
            text = "🛒 سبد خرید شما:\n\n"
            total = 0

            for item in cart_items:
                item_total = item["quantity"] * item["item_price"]
                text += f"• {item['item_name']}\n"
                text += f"  تعداد: {item['quantity']} - قیمت: {item['item_price']:,} تومان\n"
                text += f"  جمع آیتم: {item_total:,} تومان\n\n"
                total += item_total

            text += f"💰 جمع کل سبد خرید: {total:,} تومان"

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("🔙 بازگشت به منوی اصلی",
                                 callback_data="back_to_main")
        )

        if cart_items:
            keyboard.add(
                InlineKeyboardButton("✅ ثبت سفارش نهایی",
                                     callback_data="checkout")
            )

        # حذف پیام قبلی و ارسال پیام جدید
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, text, reply_markup=keyboard)

    except Error as e:
        logger.error(f"Error showing cart: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در دریافت سبد خرید")
    finally:
        if "cursor" in locals():
            cursor.close()
        if "db" in locals():
            db.disconnect()


# نمایش سفارشات - تصحیح شده
def show_orders(call):
    try:
        user_id = call.from_user.id
        db = DatabaseManager()
        conn = db.connect()

        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT * FROM orders 
            WHERE user_id = %s 
            ORDER BY order_date DESC 
            LIMIT 5
        """,
            (user_id,),
        )

        orders = cursor.fetchall()

        if not orders:
            text = "📋 شما هیچ سفارشی ندارید\n\nپس از ثبت سفارش، تاریخچه سفارشات شما در اینجا نمایش داده می‌شود."
        else:
            text = "📋 آخرین سفارشات شما:\n\n"

            for order in orders:
                status_emoji = {
                    "pending": "⏳",
                    "paid": "✅",
                    "completed": "🎉",
                    "cancelled": "❌",
                }.get(order["status"], "📦")

                text += f"{status_emoji} سفارش #{order['order_id']}\n"
                text += f"💰 مبلغ: {order['total_amount']:,} تومان\n"
                text += f"📅 تاریخ: {order['order_date'].strftime('%Y-%m-%d %H:%M')}\n"
                text += f"📦 وضعیت: {order['status']}\n\n"

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("🔙 بازگشت به منوی اصلی",
                                 callback_data="back_to_main")
        )

        # حذف پیام قبلی و ارسال پیام جدید
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, text, reply_markup=keyboard)

    except Error as e:
        logger.error(f"Error showing orders: {e}")
        bot.answer_callback_query(call.id, "❌ خطا در دریافت سفارشات")
    finally:
        if "cursor" in locals():
            cursor.close()
        if "db" in locals():
            db.disconnect()


# راه‌اندازی ربات
if __name__ == "__main__":
    print("🤖 ربات گیم سنتر راه‌اندازی شد...")
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
