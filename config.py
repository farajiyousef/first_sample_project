DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "y13791029f",
    "database": "game_center_bot",
}

token = "8204768526:AAFoUlfWEGAaGz5HT15qr9menwd54RKxwSE"


class BotConfig:
    """کلاس مدیریت تنظیمات ربات"""

    def __init__(self):
        self.BOT_TOKEN = "8204768526:AAFoUlfWEGAaGz5HT15qr9menwd54RKxwSE"
        self.ADMIN_IDS = [895714097, 7480147617]  # آی‌دی ادمین‌ها
        self.MAX_PRODUCTS_PER_PAGE = 8
        self.CART_MAX_ITEMS = 20
        self.SESSION_TIMEOUT = 3600  # 1 hour
        self.SUPPORT_CHAT_ID = "@youseff79"

    def validate_config(self) -> bool:
        """اعتبارسنجی تنظیمات"""
        if not self.BOT_TOKEN:
            return False
        return True
