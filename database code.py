import mysql.connector


def create_game_center_database():
    try:
        connection = mysql.connector.connect(
            host="localhost", user="root", password="y13791029f"
        )
        cursor = connection.cursor()

        cursor.execute("CREATE DATABASE IF NOT EXISTS game_center_bot")
        cursor.execute("USE game_center_bot")

        cursor.execute(
            """
            CREATE TABLE tg_users (
                user_id BIGINT PRIMARY KEY,
                username VARCHAR(255),
                first_name VARCHAR(255),
                last_name VARCHAR(255),
                language_code VARCHAR(10),
                total_orders INT DEFAULT 0,
                total_spent DECIMAL(15,2) DEFAULT 0.00,
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_states (
                user_id BIGINT PRIMARY KEY,
                current_state VARCHAR(100),
                temp_data TEXT,
                cart_total DECIMAL(15,2) DEFAULT 0.00,
                session_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS categories (
                category_id INT UNSIGNED PRIMARY KEY AUTO_INCREMENT,
                category_name VARCHAR(50) NOT NULL,
                emoji VARCHAR(10) NULL
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS games (
                game_id INT AUTO_INCREMENT PRIMARY KEY,
                game_name VARCHAR(255) NOT NULL,
                price DECIMAL(15,2) NOT NULL,
                platform VARCHAR(100),
                genre VARCHAR(100),
                description TEXT,
                image_url VARCHAR(500),
                stock_quantity INT DEFAULT 0,
                min_stock_level INT DEFAULT 3,
                low_stock_alert BOOLEAN DEFAULT FALSE,
                is_available BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS gaming_laptops (
                laptop_id INT AUTO_INCREMENT PRIMARY KEY,
                laptop_name VARCHAR(255) NOT NULL,
                price DECIMAL(15,2) NOT NULL,
                brand VARCHAR(100),
                processor VARCHAR(100),
                ram VARCHAR(50),
                gpu VARCHAR(100),
                storage VARCHAR(100),
                description TEXT,
                image_url VARCHAR(500),
                stock_quantity INT DEFAULT 0,
                min_stock_level INT DEFAULT 2,
                low_stock_alert BOOLEAN DEFAULT FALSE,
                is_available BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS consoles (
                console_id INT AUTO_INCREMENT PRIMARY KEY,
                console_name VARCHAR(255) NOT NULL,
                price DECIMAL(15,2) NOT NULL,
                brand VARCHAR(100),
                model VARCHAR(100),
                storage VARCHAR(100),
                included_items TEXT,
                description TEXT,
                image_url VARCHAR(500),
                stock_quantity INT DEFAULT 0,
                min_stock_level INT DEFAULT 2,
                low_stock_alert BOOLEAN DEFAULT FALSE,
                is_available BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cart (
                cart_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                item_type ENUM('game', 'laptop', 'console') NOT NULL,
                item_id INT NOT NULL,
                quantity INT NOT NULL,
                item_price DECIMAL(15,2) NOT NULL,
                item_name VARCHAR(255) NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES tg_users(user_id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS orders (
                order_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                total_amount DECIMAL(15,2) NOT NULL,
                shipping_address TEXT,
                phone_number VARCHAR(20),
                payment_method VARCHAR(50),
                status ENUM('pending', 'paid', 'processing', 'shipped', 'delivered', 'cancelled', 'refunded') DEFAULT 'pending',
                items_count INT DEFAULT 0,
                discount_code VARCHAR(100),
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES tg_users(user_id)
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS order_items (
                order_item_id INT AUTO_INCREMENT PRIMARY KEY,
                order_id INT NOT NULL,
                item_type ENUM('game', 'laptop', 'console') NOT NULL,
                item_id INT NOT NULL,
                quantity INT NOT NULL,
                unit_price DECIMAL(15,2) NOT NULL,
                item_name VARCHAR(255) NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS inventory_logs (
                log_id INT AUTO_INCREMENT PRIMARY KEY,
                product_type ENUM('game', 'laptop', 'console') NOT NULL,
                product_id INT NOT NULL,
                change_type VARCHAR(50) NOT NULL,
                quantity_change INT NOT NULL,
                new_stock_level INT NOT NULL,
                reason TEXT,
                admin_id BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS activity_logs (
                activity_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                action_type VARCHAR(100) NOT NULL,
                description TEXT,
                ip_address VARCHAR(45),
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )

        cursor.execute(
            """
            INSERT IGNORE INTO categories (category_id, category_name, emoji) VALUES
            (1, 'بازی‌ها', '🎮'),
            (2, 'لپتاپ گیمینگ', '💻'),
            (3, 'کنسول گیم', '🕹')
        """
        )

        connection.commit()
        print("✅ دیتابیس Game Center کامل ایجاد شد!")

    except mysql.connector.Error as error:
        print(f"❌ خطا در ایجاد دیتابیس: {error}")

    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


create_game_center_database()
