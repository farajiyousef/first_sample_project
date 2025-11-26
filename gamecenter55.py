import telebot
from telebot.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
import mysql.connector
from mysql.connector import Error
import json
import logging
import datetime
import time
import re
import os
from typing import Dict, List, Optional, Union
import threading
from enum import Enum
from config import *
# ==============================================
# پیکربندی و تنظیمات پیشرفته
# ==============================================


# class BotConfig:
#     """کلاس مدیریت تنظیمات ربات"""

#     def __init__(self):
#         self.BOT_TOKEN = "8204768526:AAFoUlfWEGAaGz5HT15qr9menwd54RKxwSE"
#         self.ADMIN_IDS = [895714097, 7480147617]
#         self.MAX_PRODUCTS_PER_PAGE = 8
#         self.CART_MAX_ITEMS = 20
#         self.SESSION_TIMEOUT = 3600  # 1 hour
#         self.SUPPORT_CHAT_ID = "@youseff79"

#     def validate_config(self) -> bool:
#         """اعتبارسنجی تنظیمات"""
#         if not self.BOT_TOKEN:
#             return False
#         return True


class ProductCategory(Enum):
    """انواع دسته‌بندی محصولات"""

    GAMES = "games"
    LAPTOPS = "laptops"
    CONSOLES = "consoles"
    ACCESSORIES = "accessories"
    DIGITAL = "digital"


class OrderStatus(Enum):
    """وضعیت‌های سفارش"""

    PENDING = "pending"
    PAID = "paid"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


# ==============================================
# مدیریت خطا و لاگ پیشرفته
# ==============================================


class AdvancedLogger:
    """سیستم لاگ پیشرفته"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.setup_logging()

    def setup_logging(self):
        """تنظیمات لاگ"""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.FileHandler("bot.log", encoding="utf-8"),
                logging.StreamHandler(),
            ],
        )

    def log_user_action(self, user_id: int, action: str, details: str = ""):
        """لاگ اقدامات کاربر"""
        self.logger.info(
            f"USER_ACTION - User:{user_id} - Action:{action} - Details:{details}"
        )

    def log_error(self, error: Exception, context: str = ""):
        """لاگ خطاها"""
        self.logger.error(f"ERROR - Context:{context} - Error:{str(error)}")

    def log_admin_action(self, admin_id: int, action: str, target: str = ""):
        """لاگ اقدامات ادمین"""
        self.logger.info(
            f"ADMIN_ACTION - Admin:{admin_id} - Action:{action} - Target:{target}"
        )


# ==============================================
# مدیریت دیتابیس پیشرفته
# ==============================================

# DB_CONFIG = {
#     "host": "localhost",
#     "user": "root",
#     "password": "y13791029f",
#     "database": "game_center_bot",
# }


class AdvancedDatabaseManager:
    """مدیریت پیشرفته دیتابیس"""

    def __init__(self):
        self.config = DB_CONFIG
        self.connection_pool = None
        self.setup_connection_pool()
        self.logger = AdvancedLogger()

    def setup_connection_pool(self):
        """تنظیم connection pool"""
        try:
            self.connection_pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="bot_pool", pool_size=5, **self.config
            )
        except Error as e:
            self.logger.log_error(e, "Setup connection pool")

    def get_connection(self):
        """دریافت connection از pool"""
        try:
            return self.connection_pool.get_connection()
        except Error as e:
            self.logger.log_error(e, "Get connection from pool")
            return None

    def execute_query(self, query: str, params: tuple = None, fetch: bool = False):
        """اجرای کوئری عمومی"""
        conn = self.get_connection()
        if not conn:
            return None

        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params or ())

            if fetch:
                result = cursor.fetchall()
            else:
                conn.commit()
                result = None

            return result
        except Error as e:
            self.logger.log_error(e, f"Execute query: {query}")
            return None
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def add_inventory_log(
        self,
        product_type: str,
        product_id: int,
        change_type: str,
        quantity_change: int,
        new_stock: int,
        reason: str = "",
        admin_id: int = None,
    ):
        """افزودن لاگ موجودی"""
        query = """
            INSERT INTO inventory_logs 
            (product_type, product_id, change_type, quantity_change, new_stock_level, reason, admin_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        self.execute_query(
            query,
            (
                product_type,
                product_id,
                change_type,
                quantity_change,
                new_stock,
                reason,
                admin_id,
            ),
        )

    def add_activity_log(
        self,
        user_id: int,
        action_type: str,
        description: str = "",
        ip_address: str = "",
        user_agent: str = "",
    ):
        """افزودن لاگ فعالیت"""
        query = """
            INSERT INTO activity_logs 
            (user_id, action_type, description, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s)
        """
        self.execute_query(
            query, (user_id, action_type, description, ip_address, user_agent)
        )


# ==============================================
# سیستم مدیریت کاربران پیشرفته
# ==============================================


class AdvancedUserManager:
    """مدیریت پیشرفته کاربران"""

    def __init__(self):
        self.db = AdvancedDatabaseManager()
        self.logger = AdvancedLogger()
        self.user_sessions = {}  # کش session کاربران

    def register_user(self, message) -> bool:
        """ثبت نام پیشرفته کاربر"""
        user_id = message.from_user.id
        username = message.from_user.username
        first_name = message.from_user.first_name
        last_name = message.from_user.last_name
        language_code = message.from_user.language_code

        # بررسی وجود کاربر
        existing_user = self.db.execute_query(
            "SELECT user_id FROM tg_users WHERE user_id = %s", (user_id,), fetch=True
        )

        if existing_user:
            return True  # کاربر از قبل وجود دارد

        try:
            # ثبت کاربر جدید
            query = """
                INSERT INTO tg_users 
                (user_id, username, first_name, last_name, language_code, total_orders, total_spent)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            self.db.execute_query(
                query, (user_id, username, first_name,
                        last_name, language_code, 0, 0.0)
            )

            # ایجاد وضعیت کاربر
            query_state = """
                INSERT INTO user_states 
                (user_id, current_state, temp_data, cart_total, session_data)
                VALUES (%s, %s, %s, %s, %s)
            """
            self.db.execute_query(
                query_state, (user_id, "main_menu", "{}", 0.0, "{}"))

            # لاگ فعالیت
            self.db.add_activity_log(
                user_id, "user_registered", "User registered via /start command"
            )

            self.logger.log_user_action(
                user_id, "registration", "New user registered")
            return True

        except Exception as e:
            self.logger.log_error(e, "User registration")
            return False

    def update_user_state(
        self,
        user_id: int,
        state: str,
        temp_data: dict = None,
        session_data: dict = None,
    ):
        """آپدیت وضعیت کاربر"""
        try:
            temp_data_json = json.dumps(temp_data) if temp_data else "{}"
            session_data_json = json.dumps(
                session_data) if session_data else "{}"

            query = """
                UPDATE user_states 
                SET current_state = %s, temp_data = %s, session_data = %s, updated_at = NOW()
                WHERE user_id = %s
            """
            self.db.execute_query(
                query, (state, temp_data_json, session_data_json, user_id)
            )

        except Exception as e:
            self.logger.log_error(e, "Update user state")

    def get_user_state(self, user_id: int) -> dict:
        """دریافت وضعیت کاربر"""
        try:
            result = self.db.execute_query(
                "SELECT current_state, temp_data, session_data, cart_total FROM user_states WHERE user_id = %s",
                (user_id,),
                fetch=True,
            )

            if result:
                state_data = result[0]
                return {
                    "state": state_data["current_state"],
                    "temp_data": (
                        json.loads(state_data["temp_data"])
                        if state_data["temp_data"]
                        else {}
                    ),
                    "session_data": (
                        json.loads(state_data["session_data"])
                        if state_data["session_data"]
                        else {}
                    ),
                    "cart_total": state_data["cart_total"],
                }
            return {
                "state": "main_menu",
                "temp_data": {},
                "session_data": {},
                "cart_total": 0.0,
            }

        except Exception as e:
            self.logger.log_error(e, "Get user state")
            return {
                "state": "main_menu",
                "temp_data": {},
                "session_data": {},
                "cart_total": 0.0,
            }

    def get_user_stats(self, user_id: int) -> dict:
        """دریافت آمار کاربر"""
        try:
            # آمار سفارشات
            orders_stats = self.db.execute_query(
                """
                SELECT 
                    COUNT(*) as total_orders,
                    SUM(total_amount) as total_spent,
                    MAX(order_date) as last_order_date
                FROM orders 
                WHERE user_id = %s AND status != 'cancelled'
            """,
                (user_id,),
                fetch=True,
            )

            # آمار سبد خرید
            cart_stats = self.db.execute_query(
                """
                SELECT 
                    COUNT(*) as cart_items,
                    SUM(quantity * item_price) as cart_total
                FROM cart 
                WHERE user_id = %s
            """,
                (user_id,),
                fetch=True,
            )

            return {
                "total_orders": orders_stats[0]["total_orders"] if orders_stats else 0,
                "total_spent": (
                    float(orders_stats[0]["total_spent"])
                    if orders_stats and orders_stats[0]["total_spent"]
                    else 0.0
                ),
                "last_order_date": (
                    orders_stats[0]["last_order_date"] if orders_stats else None
                ),
                "cart_items": cart_stats[0]["cart_items"] if cart_stats else 0,
                "cart_total": (
                    float(cart_stats[0]["cart_total"])
                    if cart_stats and cart_stats[0]["cart_total"]
                    else 0.0
                ),
            }

        except Exception as e:
            self.logger.log_error(e, "Get user stats")
            return {}


# ==============================================
# سیستم مدیریت محصولات پیشرفته
# ==============================================


class ProductManager:
    """مدیریت پیشرفته محصولات"""

    def __init__(self):
        self.db = AdvancedDatabaseManager()
        self.logger = AdvancedLogger()

    def get_products_by_category(
        self, category: str, page: int = 1, limit: int = 8
    ) -> dict:
        """دریافت محصولات بر اساس دسته‌بندی با صفحه‌بندی"""
        try:
            offset = (page - 1) * limit

            if category == ProductCategory.GAMES.value:
                table = "games"
                name_field = "game_name"
                id_field = "game_id"
            elif category == ProductCategory.LAPTOPS.value:
                table = "gaming_laptops"
                name_field = "laptop_name"
                id_field = "laptop_id"
            elif category == ProductCategory.CONSOLES.value:
                table = "consoles"
                name_field = "console_name"
                id_field = "console_id"
            else:
                return {"products": [], "total_pages": 0, "current_page": page}

            # دریافت محصولات
            products = self.db.execute_query(
                f"""
                SELECT *, {name_field} as product_name, {id_field} as product_id
                FROM {table}
                WHERE is_available = TRUE
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
            """,
                (limit, offset),
                fetch=True,
            )

            # تعداد کل محصولات
            total_result = self.db.execute_query(
                f"""
                SELECT COUNT(*) as total
                FROM {table}
                WHERE is_available = TRUE
            """,
                fetch=True,
            )

            total_products = total_result[0]["total"] if total_result else 0
            total_pages = (total_products + limit - 1) // limit

            return {
                "products": products or [],
                "total_pages": total_pages,
                "current_page": page,
                "total_products": total_products,
            }

        except Exception as e:
            self.logger.log_error(e, "Get products by category")
            return {"products": [], "total_pages": 0, "current_page": page}

    def get_product_details(self, product_type: str, product_id: int) -> dict:
        """دریافت جزئیات کامل محصول"""
        try:
            if product_type == ProductCategory.GAMES.value:
                table = "games"
                name_field = "game_name"
                id_field = "game_id"
            elif product_type == ProductCategory.LAPTOPS.value:
                table = "gaming_laptops"
                name_field = "laptop_name"
                id_field = "laptop_id"
            elif product_type == ProductCategory.CONSOLES.value:
                table = "consoles"
                name_field = "console_name"
                id_field = "console_id"
            else:
                return {}

            product = self.db.execute_query(
                f"""
                SELECT *, {name_field} as product_name, {id_field} as product_id
                FROM {table}
                WHERE {id_field} = %s
            """,
                (product_id,),
                fetch=True,
            )

            return product[0] if product else {}

        except Exception as e:
            self.logger.log_error(e, "Get product details")
            return {}

    def search_products(self, query: str, category: str = None) -> list:
        """جستجوی پیشرفته در محصولات"""
        try:
            search_pattern = f"%{query}%"
            results = []

            # جستجو در بازی‌ها
            if not category or category == ProductCategory.GAMES.value:
                games = self.db.execute_query(
                    """
                    SELECT 'game' as product_type, game_id as product_id, game_name as product_name, 
                           price, platform, genre, image_url
                    FROM games 
                    WHERE (game_name LIKE %s OR genre LIKE %s) AND is_available = TRUE
                    LIMIT 5
                """,
                    (search_pattern, search_pattern),
                    fetch=True,
                )
                results.extend(games or [])

            # جستجو در لپتاپ‌ها
            if not category or category == ProductCategory.LAPTOPS.value:
                laptops = self.db.execute_query(
                    """
                    SELECT 'laptop' as product_type, laptop_id as product_id, laptop_name as product_name,
                           price, brand, processor, image_url
                    FROM gaming_laptops 
                    WHERE (laptop_name LIKE %s OR brand LIKE %s OR processor LIKE %s) AND is_available = TRUE
                    LIMIT 5
                """,
                    (search_pattern, search_pattern, search_pattern),
                    fetch=True,
                )
                results.extend(laptops or [])

            # جستجو در کنسول‌ها
            if not category or category == ProductCategory.CONSOLES.value:
                consoles = self.db.execute_query(
                    """
                    SELECT 'console' as product_type, console_id as product_id, console_name as product_name,
                           price, brand, model, image_url
                    FROM consoles 
                    WHERE (console_name LIKE %s OR brand LIKE %s OR model LIKE %s) AND is_available = TRUE
                    LIMIT 5
                """,
                    (search_pattern, search_pattern, search_pattern),
                    fetch=True,
                )
                results.extend(consoles or [])

            return results

        except Exception as e:
            self.logger.log_error(e, "Search products")
            return []


# ==============================================
# سیستم سبد خرید پیشرفته
# ==============================================


class AdvancedCartManager:
    """مدیریت پیشرفته سبد خرید"""

    def __init__(self):
        self.db = AdvancedDatabaseManager()
        self.logger = AdvancedLogger()
        self.config = BotConfig()

    def add_to_cart(
        self, user_id: int, product_type: str, product_id: int, quantity: int = 1
    ) -> dict:
        """افزودن محصول به سبد خرید"""
        try:
            # دریافت اطلاعات محصول
            product_manager = ProductManager()
            product = product_manager.get_product_details(
                product_type, product_id)

            if not product:
                return {"success": False, "message": "محصول یافت نشد"}

            if product["stock_quantity"] < quantity:
                return {"success": False, "message": "موجودی محصول کافی نیست"}

            # بررسی وجود محصول در سبد خرید
            existing_item = self.db.execute_query(
                """
                SELECT cart_id, quantity FROM cart 
                WHERE user_id = %s AND item_type = %s AND item_id = %s
            """,
                (user_id, product_type, product_id),
                fetch=True,
            )

            if existing_item:
                # آپدیت تعداد
                new_quantity = existing_item[0]["quantity"] + quantity
                if new_quantity > self.config.CART_MAX_ITEMS:
                    return {
                        "success": False,
                        "message": f"حداکثر {self.config.CART_MAX_ITEMS} عدد از هر محصول مجاز است",
                    }

                self.db.execute_query(
                    """
                    UPDATE cart SET quantity = %s, added_at = NOW()
                    WHERE cart_id = %s
                """,
                    (new_quantity, existing_item[0]["cart_id"]),
                )
            else:
                # افزودن آیتم جدید
                self.db.execute_query(
                    """
                    INSERT INTO cart (user_id, item_type, item_id, quantity, item_price, item_name)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """,
                    (
                        user_id,
                        product_type,
                        product_id,
                        quantity,
                        product["price"],
                        product["product_name"],
                    ),
                )

            # آپدیت جمع سبد خرید
            self.update_cart_total(user_id)

            # لاگ فعالیت
            self.db.add_activity_log(
                user_id,
                "add_to_cart",
                f"Added {quantity} of {product['product_name']} to cart",
            )

            return {"success": True, "message": "محصول به سبد خرید اضافه شد"}

        except Exception as e:
            self.logger.log_error(e, "Add to cart")
            return {"success": False, "message": "خطا در افزودن به سبد خرید"}

    def remove_from_cart(self, user_id: int, cart_id: int) -> bool:
        """حذف محصول از سبد خرید"""
        try:
            self.db.execute_query(
                "DELETE FROM cart WHERE cart_id = %s AND user_id = %s",
                (cart_id, user_id),
            )
            self.update_cart_total(user_id)

            self.db.add_activity_log(
                user_id, "remove_from_cart", f"Removed item {cart_id} from cart"
            )
            return True

        except Exception as e:
            self.logger.log_error(e, "Remove from cart")
            return False

    def update_cart_total(self, user_id: int):
        """آپدیت جمع کل سبد خرید"""
        try:
            cart_total = self.db.execute_query(
                """
                SELECT SUM(quantity * item_price) as total
                FROM cart 
                WHERE user_id = %s
            """,
                (user_id,),
                fetch=True,
            )

            total = (
                cart_total[0]["total"] if cart_total and cart_total[0]["total"] else 0.0
            )

            self.db.execute_query(
                """
                UPDATE user_states SET cart_total = %s WHERE user_id = %s
            """,
                (total, user_id),
            )

        except Exception as e:
            self.logger.log_error(e, "Update cart total")

    def get_cart_items(self, user_id: int) -> list:
        """دریافت آیتم‌های سبد خرید"""
        try:
            items = self.db.execute_query(
                """
                SELECT c.*,
                       CASE 
                           WHEN c.item_type = 'game' THEN g.stock_quantity
                           WHEN c.item_type = 'laptop' THEN l.stock_quantity
                           WHEN c.item_type = 'console' THEN co.stock_quantity
                       END as product_stock
                FROM cart c
                LEFT JOIN games g ON c.item_type = 'game' AND c.item_id = g.game_id
                LEFT JOIN gaming_laptops l ON c.item_type = 'laptop' AND c.item_id = l.laptop_id
                LEFT JOIN consoles co ON c.item_type = 'console' AND c.item_id = co.console_id
                WHERE c.user_id = %s
                ORDER BY c.added_at DESC
            """,
                (user_id,),
                fetch=True,
            )

            return items or []

        except Exception as e:
            self.logger.log_error(e, "Get cart items")
            return []

    def clear_cart(self, user_id: int) -> bool:
        """پاک کردن کامل سبد خرید"""
        try:
            self.db.execute_query(
                "DELETE FROM cart WHERE user_id = %s", (user_id,))
            self.update_cart_total(user_id)

            self.db.add_activity_log(
                user_id, "clear_cart", "Cleared entire cart")
            return True

        except Exception as e:
            self.logger.log_error(e, "Clear cart")
            return False


# ==============================================
# سیستم سفارشات پیشرفته
# ==============================================


class OrderManager:
    """مدیریت پیشرفته سفارشات"""

    def __init__(self):
        self.db = AdvancedDatabaseManager()
        self.logger = AdvancedLogger()
        self.cart_manager = AdvancedCartManager()

    def create_order(
        self,
        user_id: int,
        shipping_address: str,
        phone_number: str,
        payment_method: str,
    ) -> dict:
        """ایجاد سفارش جدید"""
        try:
            # دریافت آیتم‌های سبد خرید
            cart_items = self.cart_manager.get_cart_items(user_id)

            if not cart_items:
                return {"success": False, "message": "سبد خرید خالی است"}

            # محاسبه جمع کل
            total_amount = sum(
                item["quantity"] * item["item_price"] for item in cart_items
            )

            # بررسی موجودی محصولات
            for item in cart_items:
                if item["product_stock"] < item["quantity"]:
                    product_name = item["item_name"]
                    return {
                        "success": False,
                        "message": f"موجودی {product_name} کافی نیست",
                    }

            # ایجاد سفارش
            order_result = self.db.execute_query(
                """
                INSERT INTO orders 
                (user_id, total_amount, shipping_address, phone_number, payment_method, items_count)
                VALUES (%s, %s, %s, %s, %s, %s)
            """,
                (
                    user_id,
                    total_amount,
                    shipping_address,
                    phone_number,
                    payment_method,
                    len(cart_items),
                ),
            )

            if not order_result:
                return {"success": False, "message": "خطا در ایجاد سفارش"}

            # دریافت order_id
            order_id_result = self.db.execute_query(
                "SELECT LAST_INSERT_ID() as order_id", fetch=True
            )
            order_id = order_id_result[0]["order_id"] if order_id_result else None

            if not order_id:
                return {"success": False, "message": "خطا در دریافت شماره سفارش"}

            # افزودن آیتم‌های سفارش
            for item in cart_items:
                self.db.execute_query(
                    """
                    INSERT INTO order_items 
                    (order_id, item_type, item_id, quantity, unit_price, item_name)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """,
                    (
                        order_id,
                        item["item_type"],
                        item["item_id"],
                        item["quantity"],
                        item["item_price"],
                        item["item_name"],
                    ),
                )

                # به‌روزرسانی موجودی
                self.update_product_stock(
                    item["item_type"], item["item_id"], -item["quantity"]
                )

            # پاک کردن سبد خرید
            self.cart_manager.clear_cart(user_id)

            # آپدیت آمار کاربر
            self.update_user_stats(user_id, total_amount)

            # لاگ فعالیت
            self.db.add_activity_log(
                user_id, "order_created", f"Created order #{order_id}"
            )

            return {"success": True, "order_id": order_id, "total_amount": total_amount}

        except Exception as e:
            self.logger.log_error(e, "Create order")
            return {"success": False, "message": "خطا در ایجاد سفارش"}

    def update_product_stock(
        self, product_type: str, product_id: int, quantity_change: int
    ):
        """به‌روزرسانی موجودی محصول"""
        try:
            if product_type == ProductCategory.GAMES.value:
                table = "games"
                id_field = "game_id"
            elif product_type == ProductCategory.LAPTOPS.value:
                table = "gaming_laptops"
                id_field = "laptop_id"
            elif product_type == ProductCategory.CONSOLES.value:
                table = "consoles"
                id_field = "console_id"
            else:
                return

            # دریافت موجودی فعلی
            current_stock = self.db.execute_query(
                f"""
                SELECT stock_quantity FROM {table} WHERE {id_field} = %s
            """,
                (product_id,),
                fetch=True,
            )

            if current_stock:
                new_stock = current_stock[0]["stock_quantity"] + \
                    quantity_change

                # آپدیت موجودی
                self.db.execute_query(
                    f"""
                    UPDATE {table} 
                    SET stock_quantity = %s, 
                        low_stock_alert = CASE WHEN %s <= min_stock_level THEN TRUE ELSE FALSE END
                    WHERE {id_field} = %s
                """,
                    (new_stock, new_stock, product_id),
                )

                # افزودن لاگ موجودی
                change_type = "sale" if quantity_change < 0 else "restock"
                self.db.add_inventory_log(
                    product_type,
                    product_id,
                    change_type,
                    abs(quantity_change),
                    new_stock,
                    "Order processing",
                )

        except Exception as e:
            self.logger.log_error(e, "Update product stock")

    def update_user_stats(self, user_id: int, order_amount: float):
        """آپدیت آمار کاربر"""
        try:
            self.db.execute_query(
                """
                UPDATE tg_users 
                SET total_orders = total_orders + 1,
                    total_spent = total_spent + %s
                WHERE user_id = %s
            """,
                (order_amount, user_id),
            )

        except Exception as e:
            self.logger.log_error(e, "Update user stats")

    def get_order_history(self, user_id: int, limit: int = 10) -> list:
        """دریافت تاریخچه سفارشات"""
        try:
            orders = self.db.execute_query(
                """
                SELECT o.*,
                       (SELECT COUNT(*) FROM order_items oi WHERE oi.order_id = o.order_id) as items_count
                FROM orders o
                WHERE o.user_id = %s
                ORDER BY o.order_date DESC
                LIMIT %s
            """,
                (user_id, limit),
                fetch=True,
            )

            return orders or []

        except Exception as e:
            self.logger.log_error(e, "Get order history")
            return []

    def get_order_details(self, order_id: int, user_id: int = None) -> dict:
        """دریافت جزئیات سفارش"""
        try:
            query = """
                SELECT o.*, 
                       (SELECT COUNT(*) FROM order_items oi WHERE oi.order_id = o.order_id) as items_count
                FROM orders o
                WHERE o.order_id = %s
            """
            params = [order_id]

            if user_id:
                query += " AND o.user_id = %s"
                params.append(user_id)

            order = self.db.execute_query(query, tuple(params), fetch=True)

            if not order:
                return {}

            # دریافت آیتم‌های سفارش
            items = self.db.execute_query(
                """
                SELECT * FROM order_items 
                WHERE order_id = %s
                ORDER BY order_item_id
            """,
                (order_id,),
                fetch=True,
            )

            return {"order_info": order[0], "order_items": items or []}

        except Exception as e:
            self.logger.log_error(e, "Get order details")
            return {}


# ==============================================
# ادامه کد در پاسخ بعدی...
# ==============================================


# ==============================================
# سیستم مدیریت ادمین پیشرفته
# ==============================================


class AdminManager:
    """مدیریت پیشرفته ادمین"""

    def __init__(self):
        self.db = AdvancedDatabaseManager()
        self.logger = AdvancedLogger()
        self.config = BotConfig()

    def is_admin(self, user_id: int) -> bool:
        """بررسی ادمین بودن کاربر"""
        return user_id in self.config.ADMIN_IDS

    def get_system_stats(self) -> dict:
        """دریافت آمار سیستم"""
        try:
            # آمار کاربران
            users_stats = self.db.execute_query(
                """
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(CASE WHEN DATE(joined_at) = CURDATE() THEN 1 END) as new_users_today,
                    COUNT(CASE WHEN last_active >= DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 1 END) as active_users_week
                FROM tg_users
            """,
                fetch=True,
            )

            # آمار سفارشات
            orders_stats = self.db.execute_query(
                """
                SELECT 
                    COUNT(*) as total_orders,
                    SUM(total_amount) as total_revenue,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_orders,
                    COUNT(CASE WHEN status = 'paid' THEN 1 END) as paid_orders,
                    COUNT(CASE WHEN DATE(order_date) = CURDATE() THEN 1 END) as today_orders
                FROM orders
            """,
                fetch=True,
            )

            # آمار محصولات
            products_stats = self.db.execute_query(
                """
                SELECT 
                    (SELECT COUNT(*) FROM games WHERE is_available = TRUE) as total_games,
                    (SELECT COUNT(*) FROM gaming_laptops WHERE is_available = TRUE) as total_laptops,
                    (SELECT COUNT(*) FROM consoles WHERE is_available = TRUE) as total_consoles,
                    (SELECT COUNT(*) FROM games WHERE low_stock_alert = TRUE) as low_stock_games,
                    (SELECT COUNT(*) FROM gaming_laptops WHERE low_stock_alert = TRUE) as low_stock_laptops,
                    (SELECT COUNT(*) FROM consoles WHERE low_stock_alert = TRUE) as low_stock_consoles
            """,
                fetch=True,
            )

            return {
                "users": users_stats[0] if users_stats else {},
                "orders": orders_stats[0] if orders_stats else {},
                "products": products_stats[0] if products_stats else {},
            }

        except Exception as e:
            self.logger.log_error(e, "Get system stats")
            return {}

    def get_recent_orders(self, limit: int = 10) -> list:
        """دریافت سفارشات اخیر"""
        try:
            orders = self.db.execute_query(
                """
                SELECT o.*, u.username, u.first_name, u.last_name
                FROM orders o
                LEFT JOIN tg_users u ON o.user_id = u.user_id
                ORDER BY o.order_date DESC
                LIMIT %s
            """,
                (limit,),
                fetch=True,
            )

            return orders or []

        except Exception as e:
            self.logger.log_error(e, "Get recent orders")
            return []

    def update_order_status(
        self, order_id: int, new_status: str, admin_id: int
    ) -> bool:
        """آپدیت وضعیت سفارش"""
        try:
            result = self.db.execute_query(
                """
                UPDATE orders 
                SET status = %s 
                WHERE order_id = %s
            """,
                (new_status, order_id),
            )

            if result:
                self.db.add_activity_log(
                    admin_id,
                    "update_order_status",
                    f"Updated order #{order_id} to {new_status}",
                )
                return True
            return False

        except Exception as e:
            self.logger.log_error(e, "Update order status")
            return False

    def add_new_product(self, product_data: dict, admin_id: int) -> bool:
        """افزودن محصول جدید"""
        try:
            product_type = product_data.get("type")

            if product_type == ProductCategory.GAMES.value:
                query = """
                    INSERT INTO games 
                    (game_name, price, platform, genre, description, image_url, stock_quantity, min_stock_level)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    product_data["name"],
                    product_data["price"],
                    product_data["platform"],
                    product_data.get("genre"),
                    product_data.get("description"),
                    product_data.get("image_url"),
                    product_data.get("stock_quantity", 0),
                    product_data.get("min_stock_level", 3),
                )

            elif product_type == ProductCategory.LAPTOPS.value:
                query = """
                    INSERT INTO gaming_laptops 
                    (laptop_name, price, brand, processor, ram, gpu, storage, description, image_url, stock_quantity, min_stock_level)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    product_data["name"],
                    product_data["price"],
                    product_data["brand"],
                    product_data.get("processor"),
                    product_data.get("ram"),
                    product_data.get("gpu"),
                    product_data.get("storage"),
                    product_data.get("description"),
                    product_data.get("image_url"),
                    product_data.get("stock_quantity", 0),
                    product_data.get("min_stock_level", 2),
                )

            elif product_type == ProductCategory.CONSOLES.value:
                query = """
                    INSERT INTO consoles 
                    (console_name, price, brand, model, storage, included_items, description, image_url, stock_quantity, min_stock_level)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                params = (
                    product_data["name"],
                    product_data["price"],
                    product_data["brand"],
                    product_data.get("model"),
                    product_data.get("storage"),
                    product_data.get("included_items"),
                    product_data.get("description"),
                    product_data.get("image_url"),
                    product_data.get("stock_quantity", 0),
                    product_data.get("min_stock_level", 2),
                )
            else:
                return False

            result = self.db.execute_query(query, params)

            if result:
                self.db.add_activity_log(
                    admin_id,
                    "add_product",
                    f"Added new {product_type}: {product_data['name']}",
                )
                return True
            return False

        except Exception as e:
            self.logger.log_error(e, "Add new product")
            return False


# ==============================================
# سیستم تخفیف و کوپن
# ==============================================


class DiscountManager:
    """مدیریت سیستم تخفیف"""

    def __init__(self):
        self.db = AdvancedDatabaseManager()
        self.logger = AdvancedLogger()

    def create_discount_code(
        self,
        code: str,
        discount_type: str,
        value: float,
        min_order: float = None,
        max_uses: int = None,
        valid_until: datetime = None,
    ) -> bool:
        """ایجاد کد تخفیف جدید"""
        try:
            query = """
                INSERT INTO discounts 
                (discount_code, discount_type, discount_value, min_order_amount, 
                 max_uses, uses_count, valid_until, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            params = (
                code,
                discount_type,
                value,
                min_order,
                max_uses,
                0,
                valid_until,
                True,
            )

            result = self.db.execute_query(query, params)
            return result is not None

        except Exception as e:
            self.logger.log_error(e, "Create discount code")
            return False

    def validate_discount_code(self, code: str, order_amount: float = 0) -> dict:
        """اعتبارسنجی کد تخفیف"""
        try:
            discount = self.db.execute_query(
                """
                SELECT * FROM discounts 
                WHERE discount_code = %s AND is_active = TRUE 
                AND (valid_until IS NULL OR valid_until >= NOW())
            """,
                (code,),
                fetch=True,
            )

            if not discount:
                return {"valid": False, "message": "کد تخفیف معتبر نیست"}

            discount = discount[0]

            # بررسی تعداد استفاده
            if discount["max_uses"] and discount["uses_count"] >= discount["max_uses"]:
                return {"valid": False, "message": "کد تخفیف منقضی شده است"}

            # بررسی حداقل سفارش
            if (
                discount["min_order_amount"]
                and order_amount < discount["min_order_amount"]
            ):
                return {
                    "valid": False,
                    "message": f'حداقل سفارش برای این کد {discount["min_order_amount"]:,} تومان است',
                }

            # محاسبه مقدار تخفیف
            if discount["discount_type"] == "percentage":
                discount_amount = order_amount * \
                    (discount["discount_value"] / 100)
            else:  # fixed
                discount_amount = min(discount["discount_value"], order_amount)

            return {
                "valid": True,
                "discount_amount": discount_amount,
                "final_amount": order_amount - discount_amount,
                "discount_info": discount,
            }

        except Exception as e:
            self.logger.log_error(e, "Validate discount code")
            return {"valid": False, "message": "خطا در اعتبارسنجی کد تخفیف"}

    def apply_discount_code(self, code: str, order_id: int = None) -> bool:
        """اعمال کد تخفیف و افزایش تعداد استفاده"""
        try:
            result = self.db.execute_query(
                """
                UPDATE discounts 
                SET uses_count = uses_count + 1,
                    last_used = NOW()
                WHERE discount_code = %s
            """,
                (code,),
            )

            if result and order_id:
                self.db.execute_query(
                    """
                    UPDATE orders 
                    SET discount_code = %s
                    WHERE order_id = %s
                """,
                    (code, order_id),
                )

            return result is not None

        except Exception as e:
            self.logger.log_error(e, "Apply discount code")
            return False


# ==============================================
# سیستم اطلاع‌رسانی و نوتیفیکیشن
# ==============================================


class NotificationManager:
    """مدیریت سیستم اطلاع‌رسانی"""

    def __init__(self, bot):
        self.bot = bot
        self.db = AdvancedDatabaseManager()
        self.logger = AdvancedLogger()

    def send_order_notification(self, order_id: int, order_data: dict):
        """ارسال نوتیفیکیشن سفارش جدید"""
        try:
            message = f"""
🆕 سفارش جدید ثبت شد!

📦 شماره سفارش: #{order_id}
👤 کاربر: {order_data.get('first_name', '')} {order_data.get('last_name', '')}
💰 مبلغ: {order_data.get('total_amount', 0):,} تومان
📞 تلفن: {order_data.get('phone_number', 'ندارد')}

برای مشاهده جزئیات کامل به پنل ادمین مراجعه کنید.
            """

            # ارسال به ادمین‌ها
            for admin_id in BotConfig().ADMIN_IDS:
                try:
                    self.bot.send_message(admin_id, message)
                except Exception as e:
                    self.logger.log_error(
                        e, f"Send notification to admin {admin_id}")

        except Exception as e:
            self.logger.log_error(e, "Send order notification")

    def send_stock_alert(
        self, product_type: str, product_id: int, product_name: str, current_stock: int
    ):
        """ارسال هشدار کمبود موجودی"""
        try:
            message = f"""
⚠ هشدار کمبود موجودی!

📦 محصول: {product_name}
🏷 نوع: {product_type}
📊 موجودی فعلی: {current_stock} عدد

لطفاً نسبت به تکمیل موجودی اقدام کنید.
            """

            # ارسال به ادمین‌ها
            for admin_id in BotConfig().ADMIN_IDS:
                try:
                    self.bot.send_message(admin_id, message)
                except Exception as e:
                    self.logger.log_error(
                        e, f"Send stock alert to admin {admin_id}")

        except Exception as e:
            self.logger.log_error(e, "Send stock alert")

    def send_user_notification(
        self, user_id: int, message: str, notification_type: str = "info"
    ):
        """ارسال نوتیفیکیشن به کاربر"""
        try:
            emoji = {"info": "ℹ", "success": "✅", "warning": "⚠", "error": "❌"}.get(
                notification_type, "📢"
            )

            formatted_message = f"{emoji} {message}"
            self.bot.send_message(user_id, formatted_message)

            self.db.add_activity_log(
                user_id, "user_notification", f"Sent {notification_type} notification"
            )

        except Exception as e:
            self.logger.log_error(e, f"Send user notification to {user_id}")


# ==============================================
# utilities و helper functions
# ==============================================


class TextUtils:
    """ابزارهای متنی و فرمت‌بندی"""

    @staticmethod
    def format_price(price: float) -> str:
        """فرمت‌بندی قیمت"""
        return f"{price:,.0f} تومان"

    @staticmethod
    def format_product_description(product: dict) -> str:
        """فرمت‌بندی توضیحات محصول"""
        description = f"🎯 *{product['product_name']}*\n\n"
        description += f"💰 قیمت: {TextUtils.format_price(product['price'])}\n"

        if product.get("platform"):
            description += f"🎮 پلتفرم: {product['platform']}\n"
        if product.get("genre"):
            description += f"📁 ژانر: {product['genre']}\n"
        if product.get("brand"):
            description += f"🏷 برند: {product['brand']}\n"
        if product.get("processor"):
            description += f"⚡ پردازنده: {product['processor']}\n"
        if product.get("ram"):
            description += f"💾 رم: {product['ram']}\n"
        if product.get("gpu"):
            description += f"🎥 کارت گرافیک: {product['gpu']}\n"
        if product.get("storage"):
            description += f"💿 حافظه: {product['storage']}\n"
        if product.get("model"):
            description += f"📋 مدل: {product['model']}\n"

        description += f"📦 موجودی: {product.get('stock_quantity', 0)} عدد\n"

        if product.get("description"):
            description += f"\n📝 توضیحات:\n{product['description']}\n"

        return description

    @staticmethod
    def truncate_text(text: str, max_length: int = 100) -> str:
        """کوتاه کردن متن"""
        if len(text) <= max_length:
            return text
        return text[: max_length - 3] + "..."


class ValidationUtils:
    """ابزارهای اعتبارسنجی"""

    @staticmethod
    def validate_phone_number(phone: str) -> bool:
        """اعتبارسنجی شماره تلفن"""
        pattern = r"^09[0-9]{9}$"
        return bool(re.match(pattern, phone))

    @staticmethod
    def validate_email(email: str) -> bool:
        """اعتبارسنجی ایمیل"""
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_price(price: str) -> tuple[bool, float]:
        """اعتبارسنجی قیمت"""
        try:
            price_value = float(price)
            return price_value > 0, price_value
        except:
            return False, 0


class KeyboardGenerator:
    """تولید کننده کیبوردهای پیشرفته"""

    @staticmethod
    def generate_main_menu() -> InlineKeyboardMarkup:
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
    def generate_product_pagination(
        category: str, current_page: int, total_pages: int, has_products: bool = True
    ) -> InlineKeyboardMarkup:
        """کیبورد صفحه‌بندی محصولات"""
        keyboard = InlineKeyboardMarkup()

        if not has_products:
            keyboard.add(
                InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_main")
            )
            return keyboard

        row = []
        if current_page > 1:
            row.append(
                InlineKeyboardButton(
                    "⬅ قبلی", callback_data=f"page_{category}_{current_page-1}"
                )
            )

        row.append(
            InlineKeyboardButton(
                f"{current_page}/{total_pages}", callback_data="current_page"
            )
        )

        if current_page < total_pages:
            row.append(
                InlineKeyboardButton(
                    "بعدی ➡", callback_data=f"page_{category}_{current_page+1}"
                )
            )

        if row:
            keyboard.row(*row)

        keyboard.add(
            InlineKeyboardButton(
                "🔙 بازگشت به منو", callback_data="back_to_main")
        )
        return keyboard

    @staticmethod
    def generate_admin_menu() -> InlineKeyboardMarkup:
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


# ==============================================
# main bot handlers - ادامه هندلرهای اصلی
# ==============================================

# ایجاد نمونه‌های global
config = BotConfig()
bot = telebot.TeleBot(config.BOT_TOKEN)
logger = AdvancedLogger()
user_manager = AdvancedUserManager()
product_manager = ProductManager()
cart_manager = AdvancedCartManager()
order_manager = OrderManager()
admin_manager = AdminManager()
notification_manager = NotificationManager(bot)


@bot.message_handler(commands=["start", "help"])
def handle_start_help(message):
    """هندلر دستورات start و help"""
    try:
        user_id = message.from_user.id

        if not user_manager.register_user(message):
            bot.reply_to(
                message, "❌ خطا در ثبت اطلاعات. لطفاً مجدداً تلاش کنید.")
            return

        if message.text == "/start":
            welcome_text = """
🎮 به گیم سنتر خوش آمدید!

✨ *امکانات ربات:*
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

        elif message.text == "/help":
            help_text = """
📖 *راهنمای استفاده از ربات:*

🔍 *جستجو و خرید:*
1. از منوی اصلی دسته‌بندی مورد نظر را انتخاب کنید
2. محصولات را مشاهده و بررسی کنید
3. با کلیک روی محصول به سبد خرید اضافه شود
4. از بخش سبد خرید سفارش خود را نهایی کنید

🛒 *سبد خرید:*
• امکان افزودن چندین محصول
• مشاهده جمع کل
• ویرایش تعداد و حذف محصولات

📋 *سفارشات:*
• تاریخچه کامل سفارشات
• وضعیت هر سفارش
• جزئیات پرداخت و ارسال

📞 *پشتیبانی:*
برای مشکلات فنی و سوالات با پشتیبانی در ارتباط باشید.

برای شروع از منوی زیر اقدام کنید:
"""
            bot.send_message(
                message.chat.id,
                help_text,
                reply_markup=KeyboardGenerator.generate_main_menu(),
                parse_mode="Markdown",
            )

        user_manager.db.add_activity_log(
            user_id, "command_used", f"Used {message.text} command"
        )

    except Exception as e:
        logger.log_error(e, "Handle start/help")
        bot.reply_to(message, "❌ خطا در پردازش درخواست.")


@bot.message_handler(commands=["admin"])
def handle_admin_command(message):
    """هندلر دستور ادمین"""
    try:
        user_id = message.from_user.id

        if not admin_manager.is_admin(user_id):
            bot.reply_to(message, "❌ دسترسی نداری با ی خداحافظی خوشحالم کن.")
            return

        admin_text = """
👨‍💼 *پنل مدیریت گیم سنتر*

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

        admin_manager.db.add_activity_log(
            user_id, "admin_access", "Accessed admin panel"
        )

    except Exception as e:
        logger.log_error(e, "Handle admin command")
        bot.reply_to(message, "❌ خطا در دسترسی به پنل مدیریت.")


@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """هندلر کلیه پیام‌های متنی"""
    try:
        user_id = message.from_user.id
        user_state = user_manager.get_user_state(user_id)

        # بررسی وضعیت کاربر و پاسخ مناسب
        if user_state["state"].startswith("waiting_"):
            handle_user_input_state(message, user_state)
        else:
            # پاسخ به پیام‌های معمولی
            bot.send_message(
                message.chat.id,
                "🤔 برای استفاده از ربات از منوی زیر یا دستورات استفاده کنید:",
                reply_markup=KeyboardGenerator.generate_main_menu(),
            )

        user_manager.db.add_activity_log(
            user_id,
            "text_message",
            f"Received text: {TextUtils.truncate_text(message.text, 50)}",
        )

    except Exception as e:
        logger.log_error(e, "Handle all messages")


def handle_user_input_state(message, user_state):
    """مدیریت وضعیت‌های ورودی کاربر"""
    user_id = message.from_user.id
    state = user_state["state"]

    try:
        if state == "waiting_shipping_address":
            # پردازش آدرس ارسال
            process_shipping_address(message, user_state)

        elif state == "waiting_phone_number":
            # پردازش شماره تلفن
            process_phone_number(message, user_state)

        elif state == "waiting_search_query":
            # پردازش جستجو
            process_search_query(message, user_state)

        else:
            user_manager.update_user_state(user_id, "main_menu")
            bot.send_message(
                message.chat.id,
                "✅ وضعیت بازنشانی شد. از منوی اصلی استفاده کنید.",
                reply_markup=KeyboardGenerator.generate_main_menu(),
            )

    except Exception as e:
        logger.log_error(e, f"Handle user input state: {state}")
        bot.send_message(
            message.chat.id, "❌ خطا در پردازش اطلاعات. لطفاً مجدداً تلاش کنید."
        )


def process_shipping_address(message, user_state):
    """پردازش آدرس ارسال"""
    user_id = message.from_user.id
    address = message.text.strip()

    if len(address) < 10:
        bot.send_message(
            message.chat.id, "❌ آدرس بسیار کوتاه است. لطفاً آدرس کامل وارد کنید."
        )
        return

    user_state["temp_data"]["shipping_address"] = address
    user_manager.update_user_state(
        user_id, "waiting_phone_number", user_state["temp_data"]
    )

    bot.send_message(
        message.chat.id,
        "✅ آدرس ذخیره شد.\n\n📞 لطفاً شماره تلفن همراه خود را وارد کنید:",
        reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_checkout")
        ),
    )


def process_phone_number(message, user_state):
    """پردازش شماره تلفن"""
    user_id = message.from_user.id
    phone = message.text.strip()

    if not ValidationUtils.validate_phone_number(phone):
        bot.send_message(
            message.chat.id,
            "❌ شماره تلفن معتبر نیست. لطفاً شماره به فرمت 09123456789 وارد کنید.",
        )
        return

    user_state["temp_data"]["phone_number"] = phone
    user_manager.update_user_state(user_id, "main_menu")

    # ایجاد سفارش
    order_result = order_manager.create_order(
        user_id=user_id,
        shipping_address=user_state["temp_data"]["shipping_address"],
        phone_number=phone,
        payment_method="online",  # می‌تواند از temp_data خوانده شود
    )

    if order_result["success"]:
        success_text = f"""
✅ سفارش شما با موفقیت ثبت شد!

📦 شماره سفارش: #{order_result['order_id']}
💰 مبلغ قابل پرداخت: {order_result['total_amount']:,} تومان
📞 شماره پیگیری: {phone}

لطفاً برای تکمیل فرآیند خرید، مبلغ فوق را پرداخت کنید.
"""
        bot.send_message(message.chat.id, success_text)

        # ارسال نوتیفیکیشن به ادمین
        user_info = user_manager.db.execute_query(
            "SELECT first_name, last_name FROM tg_users WHERE user_id = %s",
            (user_id,),
            fetch=True,
        )

        if user_info:
            order_data = {
                "first_name": user_info[0]["first_name"],
                "last_name": user_info[0]["last_name"],
                "total_amount": order_result["total_amount"],
                "phone_number": phone,
            }
            notification_manager.send_order_notification(
                order_result["order_id"], order_data
            )
    else:
        bot.send_message(message.chat.id, f"❌ {order_result['message']}")


def process_search_query(message, user_state):
    """پردازش جستجوی کاربر"""
    user_id = message.from_user.id
    query = message.text.strip()

    if len(query) < 2:
        bot.send_message(message.chat.id, "❌ عبارت جستجو بسیار کوتاه است.")
        return

    results = product_manager.search_products(query)

    if not results:
        bot.send_message(
            message.chat.id,
            f"🔍 هیچ محصولی برای '{query}' یافت نشد.",
            reply_markup=KeyboardGenerator.generate_main_menu(),
        )
        return

    response_text = f"🔍 نتایج جستجو برای '{query}':\n\n"
    keyboard = InlineKeyboardMarkup()

    for i, product in enumerate(results[:5], 1):
        response_text += f"{i}. {product['product_name']} - {TextUtils.format_price(product['price'])}\n"

        callback_data = f"product_{product['product_type']}_{product['product_id']}"
        keyboard.add(
            InlineKeyboardButton(
                f"{i}. {product['product_name']}", callback_data=callback_data
            )
        )

    keyboard.add(InlineKeyboardButton(
        "🔙 بازگشت", callback_data="back_to_main"))

    bot.send_message(message.chat.id, response_text, reply_markup=keyboard)
    user_manager.update_user_state(user_id, "main_menu")


# ==============================================
# callback query handlers - ادامه هندلرهای callback
# ==============================================


@bot.callback_query_handler(func=lambda call: True)
def handle_all_callbacks(call):
    """هندلر کلیه callback‌ها"""
    try:
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
        else:
            bot.answer_callback_query(call.id, "⚠ دستور شناسایی نشد")

    except Exception as e:
        logger.log_error(e, f"Handle callback: {call.data}")
        bot.answer_callback_query(call.id, "❌ خطا در پردازش")


def handle_back_to_main(call):
    """بازگشت به منوی اصلی"""
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
        welcome_text = """
🎮 منوی اصلی گیم سنتر

لطفاً گزینه مورد نظر را انتخاب کنید:
"""
        bot.send_message(
            call.message.chat.id,
            welcome_text,
            reply_markup=KeyboardGenerator.generate_main_menu(),
        )

    except Exception as e:
        logger.log_error(e, "Handle back to main")
        bot.answer_callback_query(call.id, "❌ خطا در بازگشت به منوی اصلی")


def handle_category_selection(call):
    """انتخاب دسته‌بندی"""
    try:
        category = call.data.replace("category_", "")
        user_id = call.from_user.id

        # دریافت محصولات صفحه اول
        products_data = product_manager.get_products_by_category(
            category, page=1)

        if not products_data["products"]:
            bot.answer_callback_query(
                call.id, "⚠ محصولی در این دسته‌بندی موجود نیست")
            return

        # ایجاد پیام محصولات
        category_names = {
            "games": "بازی‌ها",
            "laptops": "لپتاپ‌های گیمینگ",
            "consoles": "کنسول‌های بازی",
        }

        message_text = f"🎮 {category_names.get(category, 'محصولات')}\n\n"
        message_text += f"📄 صفحه 1 از {products_data['total_pages']}\n"
        message_text += f"📊 تعداد محصولات: {products_data['total_products']}\n\n"

        keyboard = InlineKeyboardMarkup()

        # افزودن محصولات
        for product in products_data["products"]:
            btn_text = f"{product['product_name']} - {TextUtils.format_price(product['price'])}"
            callback_data = f"product_{category}_{product['product_id']}"
            keyboard.add(InlineKeyboardButton(
                btn_text, callback_data=callback_data))

        # افزودن صفحه‌بندی
        pagination_keyboard = KeyboardGenerator.generate_product_pagination(
            category, 1, products_data["total_pages"], True
        )

        # ترکیب کیبوردها
        for row in pagination_keyboard.keyboard:
            keyboard.row(*row)

        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, message_text,
                         reply_markup=keyboard)

        user_manager.db.add_activity_log(
            user_id, "view_category", f"Viewed {category} category"
        )

    except Exception as e:
        logger.log_error(e, f"Handle category selection: {call.data}")
        bot.answer_callback_query(call.id, "❌ خطا در نمایش محصولات")


# ادامه هندلرها در پاسخ بعدی...


def handle_pagination(call):
    """مدیریت صفحه‌بندی محصولات"""
    try:
        parts = call.data.split("_")
        if len(parts) != 3:
            bot.answer_callback_query(call.id, "❌ خطا در صفحه‌بندی")
            return

        category = parts[1]
        page = int(parts[2])
        user_id = call.from_user.id

        # دریافت محصولات صفحه مورد نظر
        products_data = product_manager.get_products_by_category(
            category, page=page)

        if not products_data["products"]:
            bot.answer_callback_query(
                call.id, "⚠ محصولی در این صفحه موجود نیست")
            return

        # ایجاد پیام محصولات
        category_names = {
            "games": "بازی‌ها",
            "laptops": "لپتاپ‌های گیمینگ",
            "consoles": "کنسول‌های بازی",
        }

        message_text = f"🎮 {category_names.get(category, 'محصولات')}\n\n"
        message_text += f"📄 صفحه {page} از {products_data['total_pages']}\n"
        message_text += f"📊 تعداد محصولات: {products_data['total_products']}\n\n"

        keyboard = InlineKeyboardMarkup()

        # افزودن محصولات
        for product in products_data["products"]:
            btn_text = f"{product['product_name']} - {TextUtils.format_price(product['price'])}"
            callback_data = f"product_{category}_{product['product_id']}"
            keyboard.add(InlineKeyboardButton(
                btn_text, callback_data=callback_data))

        # افزودن صفحه‌بندی
        pagination_keyboard = KeyboardGenerator.generate_product_pagination(
            category, page, products_data["total_pages"], True
        )

        # ترکیب کیبوردها
        for row in pagination_keyboard.keyboard:
            keyboard.row(*row)

        bot.edit_message_text(
            message_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
        )

        user_manager.db.add_activity_log(
            user_id, "pagination", f"Page {page} of {category}"
        )

    except Exception as e:
        logger.log_error(e, f"Handle pagination: {call.data}")
        bot.answer_callback_query(call.id, "❌ خطا در تغییر صفحه")


def handle_product_selection(call):
    """انتخاب محصول خاص"""
    try:
        parts = call.data.split("_")
        if len(parts) != 3:
            bot.answer_callback_query(call.id, "❌ خطا در انتخاب محصول")
            return

        product_type = parts[1]
        product_id = int(parts[2])
        user_id = call.from_user.id

        # دریافت اطلاعات محصول
        product = product_manager.get_product_details(product_type, product_id)

        if not product:
            bot.answer_callback_query(call.id, "❌ محصول یافت نشد")
            return

        # ایجاد پیام محصول
        message_text = TextUtils.format_product_description(product)

        keyboard = InlineKeyboardMarkup()

        # دکمه افزودن به سبد خرید
        if product.get("stock_quantity", 0) > 0:
            keyboard.add(
                InlineKeyboardButton(
                    "🛒 افزودن به سبد خرید",
                    callback_data=f"add_to_cart_{product_type}_{product_id}",
                ),
                InlineKeyboardButton(
                    "📦 افزودن (۲ عدد)",
                    callback_data=f"add_to_cart_{product_type}_{product_id}_2",
                ),
            )
        else:
            keyboard.add(
                InlineKeyboardButton("❌ ناموجود", callback_data="out_of_stock")
            )

        # دکمه‌های بازگشت
        keyboard.add(
            InlineKeyboardButton(
                "🔙 بازگشت به محصولات", callback_data=f"category_{product_type}"
            ),
            InlineKeyboardButton("🏠 منوی اصلی", callback_data="back_to_main"),
        )

        # ارسال عکس محصول اگر موجود باشد
        if product.get("image_url"):
            try:
                bot.send_photo(
                    call.message.chat.id,
                    product["image_url"],
                    caption=message_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
                bot.delete_message(call.message.chat.id,
                                   call.message.message_id)
            except:
                # اگر ارسال عکس شکست خورد، فقط متن ارسال شود
                bot.delete_message(call.message.chat.id,
                                   call.message.message_id)
                bot.send_message(
                    call.message.chat.id,
                    message_text,
                    reply_markup=keyboard,
                    parse_mode="Markdown",
                )
        else:
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(
                call.message.chat.id,
                message_text,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )

        user_manager.db.add_activity_log(
            user_id, "view_product", f"Viewed {product_type} ID {product_id}"
        )

    except Exception as e:
        logger.log_error(e, f"Handle product selection: {call.data}")
        bot.answer_callback_query(call.id, "❌ خطا در نمایش محصول")


@bot.callback_query_handler(func=lambda call: call.data.startswith("add_to_cart_"))
def handle_add_to_cart(call):
    """افزودن محصول به سبد خرید"""
    try:
        parts = call.data.split("_")
        if len(parts) < 4:
            bot.answer_callback_query(call.id, "❌ خطا در افزودن به سبد خرید")
            return

        product_type = parts[3]
        product_id = int(parts[4])
        quantity = int(parts[5]) if len(parts) > 5 else 1
        user_id = call.from_user.id

        # افزودن به سبد خرید
        result = cart_manager.add_to_cart(
            user_id, product_type, product_id, quantity)

        if result["success"]:
            bot.answer_callback_query(call.id, f"✅ {result['message']}")

            # آپدیت سبد خرید در صورت نیاز
            user_state = user_manager.get_user_state(user_id)
            if user_state.get("cart_total", 0) > 0:
                pass  # می‌توان سبد خرید را آپدیت کرد

        else:
            bot.answer_callback_query(call.id, f"❌ {result['message']}")

    except Exception as e:
        logger.log_error(e, f"Handle add to cart: {call.data}")
        bot.answer_callback_query(call.id, "❌ خطا در افزودن به سبد خرید")


def handle_view_cart(call):
    """مشاهده سبد خرید"""
    try:
        user_id = call.from_user.id

        # دریافت آیتم‌های سبد خرید
        cart_items = cart_manager.get_cart_items(user_id)

        if not cart_items:
            message_text = "🛒 سبد خرید شما خالی است\n\n"
            message_text += "برای افزودن محصول به سبد خرید، از منوی اصلی دسته‌بندی مورد نظر را انتخاب کنید."

            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("🔍 مشاهده محصولات",
                                     callback_data="back_to_main")
            )
            keyboard.add(
                InlineKeyboardButton(
                    "🏠 منوی اصلی", callback_data="back_to_main")
            )
        else:
            message_text = "🛒 سبد خرید شما:\n\n"
            total_amount = 0

            for item in cart_items:
                item_total = item["quantity"] * item["item_price"]
                message_text += f"• {item['item_name']}\n"
                message_text += f"  تعداد: {item['quantity']} × {TextUtils.format_price(item['item_price'])}\n"
                message_text += f"  جمع: {TextUtils.format_price(item_total)}\n\n"
                total_amount += item_total

            message_text += f"💰 *جمع کل: {TextUtils.format_price(total_amount)}*"

            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("➖ ویرایش سبد خرید",
                                     callback_data="edit_cart"),
                InlineKeyboardButton("✅ ثبت سفارش", callback_data="checkout"),
            )
            keyboard.add(
                InlineKeyboardButton(
                    "🗑 پاک کردن سبد", callback_data="clear_cart"),
                InlineKeyboardButton(
                    "🔍 ادامه خرید", callback_data="back_to_main"),
            )

        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(
            call.message.chat.id,
            message_text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

        user_manager.db.add_activity_log(
            user_id, "view_cart", "Viewed cart contents")

    except Exception as e:
        logger.log_error(e, "Handle view cart")
        bot.answer_callback_query(call.id, "❌ خطا در نمایش سبد خرید")


@bot.callback_query_handler(func=lambda call: call.data == "checkout")
def handle_checkout(call):
    """شروع فرآیند تسویه حساب"""
    try:
        user_id = call.from_user.id

        # بررسی سبد خرید
        cart_items = cart_manager.get_cart_items(user_id)

        if not cart_items:
            bot.answer_callback_query(call.id, "❌ سبد خرید شما خالی است")
            return

        # بررسی موجودی محصولات
        for item in cart_items:
            if item["product_stock"] < item["quantity"]:
                bot.answer_callback_query(
                    call.id, f"❌ موجودی {item['item_name']} کافی نیست"
                )
                return

        # تغییر وضعیت کاربر به انتظار آدرس
        user_manager.update_user_state(user_id, "waiting_shipping_address")

        checkout_text = """
✅ سبد خرید شما تأیید شد!

📦 *مراحل تکمیل سفارش:*

1. 🏠 آدرس دقیق خود را وارد کنید
2. 📞 شماره تلفن همراه را وارد کنید  
3. 💳 روش پرداخت را انتخاب کنید
4. ✅ تأیید نهایی سفارش

لطفاً آدرس دقیق خود را وارد کنید:
"""

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("🔙 بازگشت به سبد خرید",
                                 callback_data="view_cart")
        )

        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(
            call.message.chat.id,
            checkout_text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

        user_manager.db.add_activity_log(
            user_id, "start_checkout", "Started checkout process"
        )

    except Exception as e:
        logger.log_error(e, "Handle checkout")
        bot.answer_callback_query(call.id, "❌ خطا در شروع فرآیند خرید")


@bot.callback_query_handler(func=lambda call: call.data == "clear_cart")
def handle_clear_cart(call):
    """پاک کردن سبد خرید"""
    try:
        user_id = call.from_user.id

        if cart_manager.clear_cart(user_id):
            bot.answer_callback_query(call.id, "✅ سبد خرید پاک شد")

            # بازگشت به منوی اصلی
            bot.delete_message(call.message.chat.id, call.message.message_id)
            bot.send_message(
                call.message.chat.id,
                "🛒 سبد خرید شما با موفقیت پاک شد.",
                reply_markup=KeyboardGenerator.generate_main_menu(),
            )
        else:
            bot.answer_callback_query(call.id, "❌ خطا در پاک کردن سبد خرید")

    except Exception as e:
        logger.log_error(e, "Handle clear cart")
        bot.answer_callback_query(call.id, "❌ خطا در پاک کردن سبد خرید")


def handle_my_orders(call):
    """مشاهده سفارشات کاربر"""
    try:
        user_id = call.from_user.id

        # دریافت سفارشات کاربر
        orders = order_manager.get_order_history(user_id, limit=10)

        if not orders:
            message_text = "📋 شما هیچ سفارشی ندارید\n\n"
            message_text += (
                "پس از ثبت اولین سفارش، تاریخچه سفارشات شما در اینجا نمایش داده می‌شود."
            )

            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton(
                    "🛒 شروع خرید", callback_data="back_to_main")
            )
        else:
            message_text = "📋 تاریخچه سفارشات شما:\n\n"

            for order in orders:
                status_icons = {
                    "pending": "⏳",
                    "paid": "✅",
                    "processing": "🔄",
                    "shipped": "🚚",
                    "delivered": "🎉",
                    "cancelled": "❌",
                    "refunded": "💸",
                }

                icon = status_icons.get(order["status"], "📦")
                order_date = order["order_date"].strftime("%Y/%m/%d %H:%M")

                message_text += f"{icon} *سفارش #{order['order_id']}*\n"
                message_text += (
                    f"💰 مبلغ: {TextUtils.format_price(order['total_amount'])}\n"
                )
                message_text += f"📅 تاریخ: {order_date}\n"
                message_text += f"📦 وضعیت: {order['status']}\n"
                message_text += f"🔢 تعداد آیتم: {order['items_count']}\n\n"

            message_text += "برای مشاهده جزئیات هر سفارش، روی آن کلیک کنید."

            keyboard = InlineKeyboardMarkup()
            for order in orders[:5]:  # حداکثر ۵ سفارش برای دکمه
                keyboard.add(
                    InlineKeyboardButton(
                        f"📦 سفارش #{order['order_id']}",
                        callback_data=f"order_details_{order['order_id']}",
                    )
                )

        keyboard.add(InlineKeyboardButton(
            "🔙 بازگشت", callback_data="back_to_main"))

        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(
            call.message.chat.id,
            message_text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

        user_manager.db.add_activity_log(
            user_id, "view_orders", "Viewed order history")

    except Exception as e:
        logger.log_error(e, "Handle my orders")
        bot.answer_callback_query(call.id, "❌ خطا در دریافت سفارشات")


@bot.callback_query_handler(func=lambda call: call.data.startswith("order_details_"))
def handle_order_details(call):
    """مشاهده جزئیات سفارش"""
    try:
        order_id = int(call.data.split("_")[2])
        user_id = call.from_user.id

        # دریافت جزئیات سفارش
        order_data = order_manager.get_order_details(order_id, user_id)

        if not order_data:
            bot.answer_callback_query(call.id, "❌ سفارش یافت نشد")
            return

        order_info = order_data["order_info"]
        order_items = order_data["order_items"]

        # ایجاد پیام جزئیات سفارش
        message_text = f"📦 *جزئیات سفارش #{order_id}*\n\n"

        message_text += (
            f"💰 مبلغ کل: {TextUtils.format_price(order_info['total_amount'])}\n"
        )
        message_text += (
            f"📅 تاریخ سفارش: {order_info['order_date'].strftime('%Y/%m/%d %H:%M')}\n"
        )
        message_text += f"📞 تلفن: {order_info.get('phone_number', 'ندارد')}\n"
        message_text += f"🏠 آدرس: {TextUtils.truncate_text(order_info.get('shipping_address', 'ندارد'), 50)}\n"
        message_text += f"💳 روش پرداخت: {order_info.get('payment_method', 'ندارد')}\n"
        message_text += f"📊 وضعیت: {order_info['status']}\n\n"

        message_text += "*محصولات:*\n"
        for item in order_items:
            item_total = item["quantity"] * item["unit_price"]
            message_text += f"• {item['item_name']}\n"
            message_text += f"  تعداد: {item['quantity']} × {TextUtils.format_price(item['unit_price'])}\n"
            message_text += f"  جمع: {TextUtils.format_price(item_total)}\n\n"

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("🔙 بازگشت به سفارشات",
                                 callback_data="my_orders")
        )
        keyboard.add(InlineKeyboardButton(
            "🏠 منوی اصلی", callback_data="back_to_main"))

        # اگر سفارش در وضعیت pending باشد، امکان لغو وجود دارد
        if order_info["status"] == "pending":
            keyboard.add(
                InlineKeyboardButton(
                    "❌ لغو سفارش", callback_data=f"cancel_order_{order_id}"
                )
            )

        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(
            call.message.chat.id,
            message_text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

        user_manager.db.add_activity_log(
            user_id, "view_order_details", f"Viewed order #{order_id}"
        )

    except Exception as e:
        logger.log_error(e, f"Handle order details: {call.data}")
        bot.answer_callback_query(call.id, "❌ خطا در دریافت جزئیات سفارش")


def handle_search_products(call):
    """شروع جستجوی محصولات"""
    try:
        user_id = call.from_user.id

        # تغییر وضعیت کاربر به انتظار عبارت جستجو
        user_manager.update_user_state(user_id, "waiting_search_query")

        search_text = """
🔍 *جستجوی محصولات*

لطفاً عبارت جستجوی خود را وارد کنید:

• نام محصول
• برند
• مدل
• ژانر (برای بازی‌ها)
• مشخصات (برای لپتاپ)

مثال:
GTA
PlayStation 5 
ASUS ROG
Intel Core i7
"""

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(
            "🔙 بازگشت", callback_data="back_to_main"))

        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(
            call.message.chat.id,
            search_text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

        user_manager.db.add_activity_log(
            user_id, "start_search", "Started product search"
        )

    except Exception as e:
        logger.log_error(e, "Handle search products")
        bot.answer_callback_query(call.id, "❌ خطا در شروع جستجو")


def handle_help(call):
    """نمایش راهنما"""
    try:
        help_text = """
📖 *راهنمای کامل گیم سنتر*

🎮 *خرید محصولات:*
1. از منوی اصلی دسته‌بندی مورد نظر را انتخاب کنید
2. محصولات را بررسی و مقایسه کنید
3. روی محصول مورد نظر کلیک کنید
4. با دکمه 🛒 به سبد خرید اضافه کنید

🛒 *مدیریت سبد خرید:*
• مشاهده جمع کل سفارش
• ویرایش تعداد محصولات
• حذف محصولات از سبد
• ثبت نهایی سفارش

📋 *پیگیری سفارشات:*
• مشاهده تاریخچه کامل
• بررسی وضعیت هر سفارش
• جزئیات پرداخت و ارسال

🔍 *جستجوی پیشرفته:*
• جستجو در تمام محصولات
• فیلتر بر اساس برند و مدل
• جستجوی هوشمند

📞 *پشتیبانی:*
برای سوالات فنی، مشکلات خرید و پیشنهادات با ما در ارتباط باشید.

*دستورات سریع:*
/start - شروع کار با ربات
/help - نمایش این راهنما
/admin - پنل مدیریت (فقط ادمین)
"""

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(
            "🔙 بازگشت", callback_data="back_to_main"))
        keyboard.add(InlineKeyboardButton(
            "📞 پشتیبانی", callback_data="support"))

        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(
            call.message.chat.id,
            help_text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.log_error(e, "Handle help")
        bot.answer_callback_query(call.id, "❌ خطا در نمایش راهنما")


def handle_support(call):
    """ارتباط با پشتیبانی"""
    try:
        support_text = f"""
📞 *پشتیبانی گیم سنتر*

برای ارتباط با پشتیبانی:

💬 *چت آنلاین:* {config.SUPPORT_CHAT_ID}
📧 *ایمیل:* support@gamecenter.com
🕒 *ساعات کاری:* ۹ صبح تا ۱۲ شب

*خدمات پشتیبانی:*
• راهنمایی در فرآیند خرید
• حل مشکلات فنی
• پیگیری سفارشات
• پیشنهادات و انتقادات

ما ۲۴ ساعته آماده پاسخگویی به شما هستیم!
"""

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton(
            "🔙 بازگشت", callback_data="back_to_main"))
        keyboard.add(
            InlineKeyboardButton(
                "💬 چت با پشتیبانی", url=f"https://t.me/{config.SUPPORT_CHAT_ID}"
            )
        )

        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(
            call.message.chat.id,
            support_text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

    except Exception as e:
        logger.log_error(e, "Handle support")
        bot.answer_callback_query(call.id, "❌ خطا در ارتباط با پشتیبانی")


# ==============================================
# admin callback handlers
# ==============================================


def handle_admin_add_product(call):
    """مدیریت افزودن محصول جدید توسط ادمین"""
    try:
        user_id = call.from_user.id

        if not admin_manager.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ دسترسی denied")
            return

        add_product_text = """
➕ افزودن محصول جدید

لطفاً نوع محصول را انتخاب کنید:
"""

        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton("🎮 بازی", callback_data="admin_add_game"),
            InlineKeyboardButton("💻 لپتاپ", callback_data="admin_add_laptop"),
        )
        keyboard.row(
            InlineKeyboardButton("🕹 کنسول", callback_data="admin_add_console"),
            InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"),
        )

        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(
            call.message.chat.id,
            add_product_text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

        admin_manager.db.add_activity_log(
            user_id, "add_product_menu", "Accessed add product menu"
        )

    except Exception as e:
        logger.log_error(e, "Handle admin add product")
        bot.answer_callback_query(call.id, "❌ خطا در نمایش منوی افزودن محصول")


def handle_admin_inventory(call):
    """مدیریت موجودی انبار توسط ادمین"""
    try:
        user_id = call.from_user.id

        if not admin_manager.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ دسترسی denied")
            return

        inventory_text = """
📦 مدیریت موجودی انبار

لطفاً دسته‌بندی مورد نظر را انتخاب کنید:
"""

        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton(
                "🎮 بازی‌ها", callback_data="admin_inventory_games"),
            InlineKeyboardButton(
                "💻 لپتاپ‌ها", callback_data="admin_inventory_laptops"),
        )
        keyboard.row(
            InlineKeyboardButton(
                "🕹 کنسول‌ها", callback_data="admin_inventory_consoles"),
            InlineKeyboardButton(
                "⚠ کمبود موجودی", callback_data="admin_low_stock"),
        )
        keyboard.add(InlineKeyboardButton(
            "🔙 بازگشت", callback_data="admin_back"))

        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(
            call.message.chat.id,
            inventory_text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

        admin_manager.db.add_activity_log(
            user_id, "inventory_menu", "Accessed inventory management"
        )

    except Exception as e:
        logger.log_error(e, "Handle admin inventory")
        bot.answer_callback_query(call.id, "❌ خطا در نمایش مدیریت موجودی")


@bot.callback_query_handler(func=lambda call: call.data.startswith('admin_inventory_'))
def handle_admin_inventory_category(call):
    """نمایش موجودی بر اساس دسته‌بندی"""
    try:
        user_id = call.from_user.id
        if not admin_manager.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ دسترسی denied")
            return

        category = call.data.replace('admin_inventory_', '')

        if category == 'games':
            table = 'games'
            name_field = 'game_name'
            id_field = 'game_id'
            title = '🎮 بازی‌ها'
        elif category == 'laptops':
            table = 'gaming_laptops'
            name_field = 'laptop_name'
            id_field = 'laptop_id'
            title = '💻 لپتاپ‌ها'
        elif category == 'consoles':
            table = 'consoles'
            name_field = 'console_name'
            id_field = 'console_id'
            title = '🕹 کنسول‌ها'
        else:
            return

        # دریافت محصولات
        products = admin_manager.db.execute_query(
            f"SELECT {id_field}, {name_field}, stock_quantity, price FROM {table} WHERE is_available = TRUE ORDER BY {name_field}",
            fetch=True
        )

        message_text = f"{title} - مدیریت موجودی\n\n"
        keyboard = InlineKeyboardMarkup()

        for product in products[:10]:  # حداکثر ۱۰ محصول
            stock_status = "✅" if product['stock_quantity'] > 5 else "⚠" if product['stock_quantity'] > 0 else "❌"
            btn_text = f"{stock_status} {product[name_field]} - {product['stock_quantity']} عدد"
            callback_data = f"admin_edit_stock_{category}_{product[id_field]}"
            keyboard.add(InlineKeyboardButton(
                btn_text, callback_data=callback_data))

        keyboard.add(InlineKeyboardButton(
            "🔙 بازگشت", callback_data="admin_inventory"))

        bot.edit_message_text(
            message_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard
        )

    except Exception as e:
        logger.log_error(e, "Handle admin inventory category")
        bot.answer_callback_query(call.id, "❌ خطا در نمایش موجودی")


@bot.callback_query_handler(func=lambda call: call.data == 'admin_low_stock')
def handle_admin_low_stock(call):
    """نمایش محصولات با کمبود موجودی"""
    try:
        user_id = call.from_user.id
        if not admin_manager.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ دسترسی denied")
            return

        # دریافت محصولات با کمبود موجودی از همه دسته‌بندی‌ها
        low_stock_products = []

        # بازی‌ها
        games = admin_manager.db.execute_query(
            "SELECT 'game' as type, game_id as id, game_name as name, stock_quantity FROM games WHERE stock_quantity <= min_stock_level AND is_available = TRUE",
            fetch=True
        )
        if games:
            low_stock_products.extend(games)

        # لپتاپ‌ها
        laptops = admin_manager.db.execute_query(
            "SELECT 'laptop' as type, laptop_id as id, laptop_name as name, stock_quantity FROM gaming_laptops WHERE stock_quantity <= min_stock_level AND is_available = TRUE",
            fetch=True
        )
        if laptops:
            low_stock_products.extend(laptops)

        # کنسول‌ها
        consoles = admin_manager.db.execute_query(
            "SELECT 'console' as type, console_id as id, console_name as name, stock_quantity FROM consoles WHERE stock_quantity <= min_stock_level AND is_available = TRUE",
            fetch=True
        )
        if consoles:
            low_stock_products.extend(consoles)

        message_text = "⚠ محصولات با کمبود موجودی\n\n"
        keyboard = InlineKeyboardMarkup()

        if not low_stock_products:
            message_text += "✅ هیچ محصولی با کمبود موجودی وجود ندارد"
        else:
            for product in low_stock_products:
                type_emoji = "🎮" if product['type'] == 'game' else "💻" if product['type'] == 'laptop' else "🕹"
                btn_text = f"{type_emoji} {product['name']} - {product['stock_quantity']} عدد"
                callback_data = f"admin_edit_stock_{product['type']}_{product['id']}"
                keyboard.add(InlineKeyboardButton(
                    btn_text, callback_data=callback_data))

        keyboard.add(InlineKeyboardButton(
            "🔙 بازگشت", callback_data="admin_inventory"))

        bot.edit_message_text(
            message_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard
        )

    except Exception as e:
        logger.log_error(e, "Handle admin low stock")
        bot.answer_callback_query(call.id, "❌ خطا در نمایش کمبود موجودی")


def handle_admin_discounts(call):
    """مدیریت تخفیف‌ها توسط ادمین"""
    try:
        user_id = call.from_user.id

        if not admin_manager.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ دسترسی denied")
            return

        discounts_text = """
🎫 مدیریت سیستم تخفیف

امکانات در دسترس:
"""

        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton(
                "➕ ایجاد کد تخفیف", callback_data="admin_create_discount"
            ),
            InlineKeyboardButton(
                "📋 لیست کدها", callback_data="admin_list_discounts"),
        )
        keyboard.row(
            InlineKeyboardButton(
                "📊 آمار استفاده", callback_data="admin_discount_stats"
            ),
            InlineKeyboardButton("🔙 بازگشت", callback_data="admin_back"),
        )

        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(
            call.message.chat.id,
            discounts_text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

        admin_manager.db.add_activity_log(
            user_id, "discounts_menu", "Accessed discount management"
        )

    except Exception as e:
        logger.log_error(e, "Handle admin discounts")
        bot.answer_callback_query(call.id, "❌ خطا در نمایش مدیریت تخفیف")


def handle_admin_broadcast(call):
    """ارسال پیام همگانی توسط ادمین"""
    try:
        user_id = call.from_user.id

        if not admin_manager.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ دسترسی denied")
            return

        broadcast_text = """
📢 ارسال پیام همگانی

با این قابلیت می‌توانید پیامی را برای تمام کاربران ربات ارسال کنید.

⚠ توجه: این عمل قابل بازگشت نیست و برای همه کاربران ارسال می‌شود.

لطفاً گزینه مورد نظر را انتخاب کنید:
"""

        keyboard = InlineKeyboardMarkup()
        keyboard.row(
            InlineKeyboardButton(
                "✍ نوشتن پیام", callback_data="admin_compose_broadcast"
            ),
            InlineKeyboardButton(
                "📊 آمار کاربران", callback_data="admin_broadcast_stats"
            ),
        )
        keyboard.add(InlineKeyboardButton(
            "🔙 بازگشت", callback_data="admin_back"))

        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(
            call.message.chat.id,
            broadcast_text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

        admin_manager.db.add_activity_log(
            user_id, "broadcast_menu", "Accessed broadcast menu"
        )

    except Exception as e:
        logger.log_error(e, "Handle admin broadcast")
        bot.answer_callback_query(call.id, "❌ خطا در نمایش ارسال اطلاعیه")


# همچنین نیاز به تابع بازگشت برای ادمین داریم
@bot.callback_query_handler(func=lambda call: call.data == "admin_back")
def handle_admin_back(call):
    """بازگشت به منوی اصلی ادمین"""
    try:
        user_id = call.from_user.id

        if not admin_manager.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ دسترسی denied")
            return

        admin_text = """
👨‍💼 پنل مدیریت گیم سنتر

امکانات مدیریتی در دسترس:
"""

        bot.edit_message_text(
            admin_text,
            call.message.chat.id,
            call.message.message_id,
            reply_markup=KeyboardGenerator.generate_admin_menu(),
            parse_mode="Markdown",
        )

        admin_manager.db.add_activity_log(
            user_id, "admin_back", "Returned to admin main menu"
        )

    except Exception as e:
        logger.log_error(e, "Handle admin back")
        bot.answer_callback_query(call.id, "❌ خطا در بازگشت به منوی ادمین")


@bot.callback_query_handler(func=lambda call: call.data == "back_to_admin")
def handle_back_to_admin(call):
    """بازگشت به منوی ادمین از بخش‌های مختلف"""
    handle_admin_back(call)


def handle_admin_callbacks(call):
    """مدیریت callback‌های ادمین"""
    try:
        user_id = call.from_user.id

        if not admin_manager.is_admin(user_id):
            bot.answer_callback_query(call.id, "❌ دسترسی denied")
            return

        action = call.data

        if action == "admin_stats":
            handle_admin_stats(call)
        elif action == "admin_orders":
            handle_admin_orders(call)
        elif action == "admin_add_product":
            handle_admin_add_product(call)
        elif action == "admin_inventory":
            handle_admin_inventory(call)
        elif action == "admin_discounts":
            handle_admin_discounts(call)
        elif action == "admin_broadcast":
            handle_admin_broadcast(call)
        elif action.startswith("admin_inventory_"):
            handle_admin_inventory_category(call)
        elif action == "admin_low_stock":
            handle_admin_low_stock(call)

        else:
            bot.answer_callback_query(call.id, "⚠ دستور ادمین شناسایی نشد")

    except Exception as e:
        logger.log_error(e, f"Handle admin callback: {call.data}")
        bot.answer_callback_query(call.id, "❌ خطا در پردازش دستور ادمین")


def handle_admin_stats(call):
    """نمایش آمار سیستم برای ادمین"""
    try:
        stats = admin_manager.get_system_stats()

        if not stats:
            bot.answer_callback_query(call.id, "❌ خطا در دریافت آمار")
            return

        users = stats.get("users", {})
        orders = stats.get("orders", {})
        products = stats.get("products", {})

        stats_text = """
📊 *آمار سیستم گیم سنتر*

👥 *کاربران:*
• کل کاربران: {total_users:,}
• کاربران جدید امروز: {new_users_today:,}
• کاربران فعال (هفته): {active_users_week:,}

📦 *سفارشات:*
• کل سفارشات: {total_orders:,}
• درآمد کل: {total_revenue:,} تومان
• سفارشات امروز: {today_orders:,}
• سفارشات در انتظار: {pending_orders:,}
• سفارشات پرداخت شده: {paid_orders:,}

🎮 *محصولات:*
• بازی‌ها: {total_games:,}
• لپتاپ‌ها: {total_laptops:,}
• کنسول‌ها: {total_consoles:,}
• کمبود موجودی بازی: {low_stock_games:,}
• کمبود موجودی لپتاپ: {low_stock_laptops:,}
• کمبود موجودی کنسول: {low_stock_consoles:,}
""".format(
            total_users=users.get("total_users", 0),
            new_users_today=users.get("new_users_today", 0),
            active_users_week=users.get("active_users_week", 0),
            total_orders=orders.get("total_orders", 0),
            total_revenue=orders.get("total_revenue", 0),
            today_orders=orders.get("today_orders", 0),
            pending_orders=orders.get("pending_orders", 0),
            paid_orders=orders.get("paid_orders", 0),
            total_games=products.get("total_games", 0),
            total_laptops=products.get("total_laptops", 0),
            total_consoles=products.get("total_consoles", 0),
            low_stock_games=products.get("low_stock_games", 0),
            low_stock_laptops=products.get("low_stock_laptops", 0),
            low_stock_consoles=products.get("low_stock_consoles", 0),
        )

        keyboard = InlineKeyboardMarkup()
        keyboard.add(
            InlineKeyboardButton("🔄 بروزرسانی آمار",
                                 callback_data="admin_stats")
        )
        keyboard.add(InlineKeyboardButton(
            "🔙 بازگشت", callback_data="admin_back"))

        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(
            call.message.chat.id,
            stats_text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

        admin_manager.db.add_activity_log(
            call.from_user.id, "view_stats", "Viewed system statistics"
        )

    except Exception as e:
        logger.log_error(e, "Handle admin stats")
        bot.answer_callback_query(call.id, "❌ خطا در دریافت آمار")


def handle_admin_orders(call):
    """مدیریت سفارشات برای ادمین"""
    try:
        orders = admin_manager.get_recent_orders(10)

        if not orders:
            orders_text = "📦 *هیچ سفارشی برای نمایش وجود ندارد*"
        else:
            orders_text = "📦 *آخرین سفارشات:*\n\n"

            for order in orders:
                user_name = f"{order.get('first_name', '')} {order.get('last_name', '')}".strip(
                )
                if not user_name:
                    user_name = order.get("username", "کاربر")

                order_date = order["order_date"].strftime("%Y/%m/%d %H:%M")

                orders_text += f"🆔 #{order['order_id']} - {user_name}\n"
                orders_text += f"💰 {TextUtils.format_price(order['total_amount'])} - {order['status']}\n"
                orders_text += f"📅 {order_date}\n"
                orders_text += f"📞 {order.get('phone_number', 'ندارد')}\n"

                # دکمه‌های مدیریت برای هر سفارش
                orders_text += f"🔧 [تغییر وضعیت](tg://btn?{order['order_id']})\n\n"

        keyboard = InlineKeyboardMarkup()

        # دکمه‌های فیلتر سفارشات
        keyboard.row(
            InlineKeyboardButton(
                "⏳ در انتظار", callback_data="admin_orders_pending"),
            InlineKeyboardButton(
                "✅ پرداخت شده", callback_data="admin_orders_paid"),
        )
        keyboard.row(
            InlineKeyboardButton(
                "🚚 ارسال شده", callback_data="admin_orders_shipped"),
            InlineKeyboardButton(
                "🎉 تحویل شده", callback_data="admin_orders_delivered"
            ),
        )
        keyboard.add(InlineKeyboardButton(
            "🔙 بازگشت", callback_data="admin_back"))

        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(
            call.message.chat.id,
            orders_text,
            reply_markup=keyboard,
            parse_mode="Markdown",
            disable_web_page_preview=True,
        )

        admin_manager.db.add_activity_log(
            call.from_user.id, "view_orders", "Viewed admin orders"
        )

    except Exception as e:
        logger.log_error(e, "Handle admin orders")
        bot.answer_callback_query(call.id, "❌ خطا در دریافت سفارشات")


# ==============================================
# برنامه اصلی و اجرا
# ==============================================


def setup_bot_commands():
    """تنظیم دستورات بات"""
    try:
        commands = [
            telebot.types.BotCommand("start", "شروع کار با ربات"),
            telebot.types.BotCommand("help", "راهنمای استفاده"),
            telebot.types.BotCommand("admin", "پنل مدیریت (ادمین)"),
        ]
        bot.set_my_commands(commands)
        logger.logger.info("Bot commands setup completed")
    except Exception as e:
        logger.log_error(e, "Setup bot commands")


def check_database_connection():
    """بررسی اتصال به دیتابیس"""
    try:
        db = AdvancedDatabaseManager()
        conn = db.get_connection()
        if conn and conn.is_connected():
            logger.logger.info("✅ Database connection successful")
            return True
        else:
            logger.logger.error("❌ Database connection failed")
            return False
    except Exception as e:
        logger.log_error(e, "Check database connection")
        return False


def schedule_maintenance_tasks():
    """برنامه‌ریزی کارهای نگهداری"""

    def maintenance():
        while True:
            try:
                # کارهای دوره‌ای مانند پاک کردن session های منقضی
                time.sleep(3600)  # هر 1 ساعت

                # پاک کردن session های قدیمی
                db = AdvancedDatabaseManager()
                db.execute_query(
                    """
                    DELETE FROM user_states 
                    WHERE updated_at < DATE_SUB(NOW(), INTERVAL 24 HOUR)
                """
                )

                logger.logger.info("🛠 Maintenance tasks completed")

            except Exception as e:
                logger.log_error(e, "Scheduled maintenance")

    # اجرای maintenance در thread جداگانه
    maintenance_thread = threading.Thread(target=maintenance, daemon=True)
    maintenance_thread.start()


def main():
    """تابع اصلی اجرای ربات"""
    try:
        print("🎮 Starting Game Center Telegram Bot...")

        # بررسی تنظیمات
        if not config.validate_config():
            print("❌ Invalid bot configuration. Please check BOT_TOKEN.")
            return

        # بررسی دیتابیس
        if not check_database_connection():
            print("❌ Database connection failed. Please check database configuration.")
            return

        # تنظیم دستورات بات
        setup_bot_commands()

        # راه‌اندازی کارهای نگهداری
        schedule_maintenance_tasks()

        print("✅ Bot is running...")
        print("🤖 Bot username: @{}".format(bot.get_me().username))
        print("📊 Use /admin for admin panel")
        print("🛑 Press Ctrl+C to stop")

        # شروع polling
        bot.infinity_polling(timeout=60, long_polling_timeout=60)

    except KeyboardInterrupt:
        print("\n🛑 Bot stopped by user")
    except Exception as e:
        logger.log_error(e, "Main function")
        print(f"❌ Bot crashed: {e}")


if __name__ == "__main__":
    main()
