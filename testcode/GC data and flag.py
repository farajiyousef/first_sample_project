import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import mysql.connector
from mysql.connector import Error
import json
import logging
import datetime
import time
import re
import threading


class BotConfig:
    def __init__(self):
        self.BOT_TOKEN = "8204768526:AAFoUlfWEGAaGz5HT15qr9menwd54RKxwSE"
        self.ADMIN_IDS = [895714097, 7480147617]
        self.MAX_PRODUCTS_PER_PAGE = 8
        self.CART_MAX_ITEMS = 20
        self.SESSION_TIMEOUT = 3600
        self.SUPPORT_CHAT_ID = "@Yousef_Farajii"


DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "y13791029f",
    "database": "game_center_bot",
}

config = BotConfig()
bot = telebot.TeleBot(config.BOT_TOKEN)


def handle_category_selection(call):
    """مدیریت انتخاب دسته‌بندی"""
    bot.answer_callback_query(call.id, "در حال بارگذاری محصولات...")
    pass


def handle_pagination(call):
    """مدیریت صفحه‌بندی"""
    bot.answer_callback_query(call.id, "در حال بارگذاری صفحه...")
    pass


def handle_product_selection(call):
    """مدیریت انتخاب محصول"""
    bot.answer_callback_query(call.id, "در حال بارگذاری محصول...")
    pass


def handle_view_cart(call):
    """مدیریت سبد خرید"""
    bot.answer_callback_query(call.id, "در حال بارگذاری سبد خرید...")
    pass


def handle_my_orders(call):
    """مدیریت سفارشات"""
    bot.answer_callback_query(call.id, "در حال بارگذاری سفارشات...")
    pass


def handle_search_products(call):
    """مدیریت جستجو"""
    bot.answer_callback_query(call.id, "لطفاً نام محصول را وارد کنید...")
    pass


def handle_admin_callbacks(call):
    """مدیریت callback های ادمین"""
    bot.answer_callback_query(call.id, "در حال بارگذاری پنل مدیریت...")
    pass


def handle_help(call):
    """مدیریت راهنما"""
    help_text = """
📖 راهنمای استفاده از ربات گیم سنتر:

• 🎮 برای مشاهده بازی‌ها: روی «بازی‌ها» کلیک کنید
• 💻 برای مشاهده لپتاپ‌ها: روی «لپتاپ گیمینگ» کلیک کنید  
• 🕹 برای مشاهده کنسول‌ها: روی «کنسول گیم» کلیک کنید
• 🔍 برای جستجو: روی «جستجو» کلیک کنید
• 🛒 برای مشاهده سبد خرید: روی «سبد خرید» کلیک کنید
• 📋 برای پیگیری سفارشات: روی «سفارشات من» کلیک کنید
"""
    bot.send_message(call.message.chat.id, help_text)


def handle_support(call):
    """مدیریت پشتیبانی"""
    support_text = f"""
📞 پشتیبانی گیم سنتر

برای ارتباط با پشتیبانی:
• 💬 چت: {config.SUPPORT_CHAT_ID}
• ⏰ ساعت پاسخگویی: ۹ صبح تا ۱۲ شب

یا پیام خود را مستقیماً ارسال کنید...
"""
    bot.send_message(call.message.chat.id, support_text)


@bot.message_handler(commands=["start", "help"])
def handle_start_help(message):
    """هندلر دستورات start و help"""
    welcome_text = """
🎮 به گیم سنتر خوش آمدید!

✨ امکانات ربات:
• 🎮 خرید بازی‌های جدید
• 💻 لپتاپ‌های گیمینگ اورجینال  
• 🕹 کنسول‌های بازی به روز
• 🛒 سبد خرید پیشرفته
• 📋 پیگیری سفارشات
• 🔍 جستجوی هوشمند

از منوی زیر انتخاب کنید:
"""
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=KeyboardGenerator.generate_main_menu(),
        parse_mode="Markdown",
    )


@bot.message_handler(commands=["admin"])
def handle_admin_command(message):
    """هندلر دستور ادمین"""
    # بررسی آیا کاربر ادمین است
    if message.from_user.id not in config.ADMIN_IDS:
        bot.send_message(message.chat.id, "⛔ دسترسی denied!")
        return

    admin_text = """
👨‍💼 پنل مدیریت گیم سنتر

امکانات مدیریتی در دسترس:

• 📊 مشاهده آمار سیستم
• 📦 مدیریت سفارشات
• ➕ افزودن محصول جدید
• 📦 مدیریت موجودی
• 🎫 کدهای تخفیف
• 📢 ارسال اطلاعیه

از منوی زیر انتخاب کنید:
"""
    bot.send_message(
        message.chat.id,
        admin_text,
        reply_markup=KeyboardGenerator.generate_admin_menu(),
        parse_mode="Markdown",
    )


class KeyboardGenerator:
    @staticmethod
    def generate_main_menu():
        """منوی اصلی"""
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("🎮 بازی‌ها", callback_data="category_games"),
            InlineKeyboardButton(
                "💻 لپتاپ گیمینگ", callback_data="category_laptops"),
            InlineKeyboardButton(
                "🕹 کنسول گیم", callback_data="category_consoles"),
            InlineKeyboardButton("🔍 جستجو", callback_data="search_products"),
            InlineKeyboardButton("🛒 سبد خرید", callback_data="view_cart"),
            InlineKeyboardButton("📋 سفارشات من", callback_data="my_orders"),
            InlineKeyboardButton("ℹ راهنما", callback_data="help"),
            InlineKeyboardButton("📞 پشتیبانی", callback_data="support"),
        )
        return keyboard

    @staticmethod
    def generate_admin_menu():
        """منوی ادمین"""
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("📊 آمار سیستم", callback_data="admin_stats"),
            InlineKeyboardButton(
                "📦 سفارشات جدید", callback_data="admin_orders"),
            InlineKeyboardButton(
                "➕ افزودن محصول", callback_data="admin_add_product"),
            InlineKeyboardButton(
                "📦 مدیریت موجودی", callback_data="admin_inventory"),
            InlineKeyboardButton(
                "🎫 مدیریت تخفیف", callback_data="admin_discounts"),
            InlineKeyboardButton(
                "📢 ارسال اطلاعیه", callback_data="admin_broadcast"),
            InlineKeyboardButton("🔙 منوی کاربر", callback_data="back_to_main"),
        )
        return keyboard

    @staticmethod
    def generate_product_pagination(category, current_page, total_pages, has_products=True):
        """کیبورد صفحه‌بندی محصولات"""
        keyboard = InlineKeyboardMarkup()

        if not has_products:
            keyboard.add(InlineKeyboardButton(
                "🔙 بازگشت", callback_data="back_to_main"))
            return keyboard

        row = []
        if current_page > 1:
            row.append(InlineKeyboardButton(
                "⬅ قبلی", callback_data=f"page_{category}_{current_page-1}"))

        row.append(InlineKeyboardButton(
            f"{current_page}/{total_pages}", callback_data="current_page"))

        if current_page < total_pages:
            row.append(InlineKeyboardButton(
                "بعدی ➡", callback_data=f"page_{category}_{current_page+1}"))

        if row:
            keyboard.row(*row)

        keyboard.add(InlineKeyboardButton(
            "🔙 بازگشت به منو", callback_data="back_to_main"))
        return keyboard


@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    """هندلر کلیه callback‌ها"""
    data = call.data

    if data == "back_to_main":
        handle_back_to_main(call)
    elif data.startswith("category_"):
        handle_category_selection(call)
    elif data.startswith("page_"):
        handle_pagination(call)
    elif data.startswith("product_"):
        handle_product_selection(call)
    elif data == "view_cart":
        handle_view_cart(call)
    elif data == "my_orders":
        handle_my_orders(call)
    elif data == "search_products":
        handle_search_products(call)
    elif data.startswith("admin_"):
        handle_admin_callbacks(call)
    elif data == "help":
        handle_help(call)
    elif data == "support":
        handle_support(call)


def handle_back_to_main(call):
    """بازگشت به منوی اصلی"""
    welcome_text = "🎮 منوی اصلی گیم سنتر\n\nلطفاً گزینه مورد نظر را انتخاب کنید:"
    try:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=welcome_text,
            reply_markup=KeyboardGenerator.generate_main_menu(),
        )
    except:
        bot.send_message(
            call.message.chat.id,
            welcome_text,
            reply_markup=KeyboardGenerator.generate_main_menu(),
        )


def main():
    """تابع اصلی اجرای ربات"""
    print("🎮 Starting Game Center Telegram Bot...")
    print("✅ Bot is running...")

    try:
        bot_info = bot.get_me()
        print("🤖 Bot username: @{}".format(bot_info.username))
    except Exception as e:
        print(f"⚠ Error getting bot info: {e}")

    print("📊 Use /admin for admin panel")
    print("🛑 Press Ctrl+C to stop")

    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=60)
    except Exception as e:
        print(f"❌ Bot stopped with error: {e}")


if __name__ == "__main__":
    main()
