import json
import urllib.parse
import logging
import requests
import os
import sys

from anticaptchaofficial.turnstileproxyless import turnstileProxyless
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# ==================== НАЛАШТУВАННЯ ====================

ANTICAPTCHA_API_KEY = os.getenv("ANTICAPTCHA_API_KEY", "YOUR_API_KEY_FROM_ANTICAPTCHA")
TURNSTILE_KEY = "0x4AAAAAAAAzi9ITzSN9xKMi"
TARGET_URL = "https://ahrefs.com/ru/traffic-checker"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


# ==================== СПОВІЩЕННЯ В TELEGRAM ====================

def send_telegram(msg: str) -> None:
    """Надсилає повідомлення у Telegram чат."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("Telegram токен або chat_id не задано")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    try:
        r = requests.post(url, data=payload, timeout=10)
        r.raise_for_status()
    except Exception as e:
        logging.error(f"Помилка надсилання в Telegram: {e}")


# ==================== РІШЕННЯ CAPTCHA ====================

def solve_captcha() -> str:
    """Отримує токен Turnstile через AntiCaptcha."""
    solver = turnstileProxyless()
    solver.set_verbose(1)
    solver.set_key(ANTICAPTCHA_API_KEY)
    solver.set_website_url(TARGET_URL)
    solver.set_website_key(TURNSTILE_KEY)

    token = solver.solve_and_return_solution()
    if token and token != 0:
        msg = "✅ Токен Turnstile успішно отримано."
        logging.info(msg)
        send_telegram(msg)
        return token
    else:
        msg = f"❌ Помилка AntiCaptcha: {solver.error_code}"
        logging.error(msg)
        send_telegram(msg)
        return ""


# ==================== ЗАПИТ ЧЕРЕЗ SELENIUM ====================

def load_url(token: str, url_to_load: str) -> str:
    """Запитує дані про органічний трафік для конкретного домену."""
    if not token:
        return "❌ Токен відсутній, запит не виконано."

    params = {
        'input': json.dumps({
            'captcha': token,
            "country": None,
            "mode": "subdomains",
            "protocol": None,
            "url": url_to_load
        })
    }
    encoded_params = urllib.parse.urlencode(params)
    url = f'https://ahrefs.com/v4/ftTrafficChecker?{encoded_params}'

    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/114.0.0.0 Safari/537.36"
    )

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        driver.get(url)

        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        page_data = driver.find_element(By.TAG_NAME, "body").text

        if not page_data:
            msg = "⚠️ Порожня відповідь від сервера."
            logging.warning(msg)
            send_telegram(msg)
            return msg

        data = json.loads(page_data)

        traffic_monthly_avg = None
        if isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and "traffic" in item:
                    traffic_monthly_avg = item["traffic"].get("trafficMonthlyAvg")
                    break
        elif isinstance(data, dict) and "traffic" in data:
            traffic_monthly_avg = data["traffic"].get("trafficMonthlyAvg")

        if traffic_monthly_avg is None:
            msg = f"⚠️ Не знайдено поле trafficMonthlyAvg у відповіді: {data}"
            logging.warning(msg)
            send_telegram(msg)
            return msg

        result = f"📊 Органічний трафік ({url_to_load}): {traffic_monthly_avg}"
        logging.info(result)
        send_telegram(result)
        return result

    except Exception as e:
        msg = f"❌ Помилка парсингу: {e}"
        logging.error(msg)
        send_telegram(msg)
        return msg
    finally:
        driver.quit()


# ==================== ТОЧКА ВХОДУ ====================

if __name__ == "__main__":
    # беремо домен з аргументів командного рядка
    if len(sys.argv) > 1:
        domain = sys.argv[1]
    else:
        domain = "dou.ua"  # дефолтне значення

    token = solve_captcha()
    if token:
        print(load_url(token, domain))
    else:
        print("❌ Капчу не розв'язано, завершення.")
