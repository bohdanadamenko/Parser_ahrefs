import json
import urllib.parse
import logging
import requests
import os
import sys
import argparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from anticaptchaofficial.turnstileproxyless import turnstileProxyless

# ==================== НАЛАШТУВАННЯ ====================

# Инициализация логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

ANTICAPTCHA_API_KEY = os.getenv("ANTICAPTCHA_API_KEY", "YOUR_API_KEY_FROM_ANTICAPTCHA")
TURNSTILE_KEY = "0x4AAAAAAAAzi9ITzSN9xKMi"
TARGET_URL = "https://ahrefs.com/ru/traffic-checker"

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


# ==================== СПОВІЩЕННЯ В TELEGRAM ====================

def create_session_with_retries() -> requests.Session:
    """Создает сессию с настройками ретраев."""
    session = requests.Session()
    retry_strategy = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session

def send_telegram(msg: str) -> None:
    """Надсилає повідомлення у Telegram чат."""
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        logging.warning("Telegram токен або chat_id не задано")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": msg}
    
    session = create_session_with_retries()
    try:
        r = session.post(url, data=payload, timeout=10)
        r.raise_for_status()
        logging.info("Повідомлення успішно надіслано в Telegram")
    except Exception as e:
        logging.error(f"Помилка надсилання в Telegram: {e}")
    finally:
        session.close()


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


# ==================== ЗАПИТ ЧЕРЕЗ REQUESTS ====================

def fetch_traffic(token: str, url_to_load: str) -> str:
    """Запитує дані про органічний трафік для конкретного домену через API."""
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

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                     "Chrome/114.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.8",
        "Referer": TARGET_URL,
        "Origin": "https://ahrefs.com",
    }

    session = create_session_with_retries()
    try:
        response = session.get(
            "https://ahrefs.com/v4/ftTrafficChecker",
            params=params,
            headers=headers,
            timeout=15
        )
        response.raise_for_status()

        # Проверяем Content-Type
        content_type = response.headers.get('content-type', '').lower()
        if 'application/json' not in content_type:
            msg = f"⚠️ Отримано не JSON відповідь. Content-Type: {content_type}"
            logging.warning(msg)
            send_telegram(msg)
            return msg

        data = response.json()

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

    except requests.exceptions.RequestException as e:
        msg = f"❌ Помилка мережі: {e}"
        logging.error(msg)
        send_telegram(msg)
        return msg
    except json.JSONDecodeError as e:
        msg = f"❌ Помилка парсингу JSON: {e}"
        logging.error(msg)
        send_telegram(msg)
        return msg
    except Exception as e:
        msg = f"❌ Неочікувана помилка: {e}"
        logging.error(msg)
        send_telegram(msg)
        return msg
    finally:
        session.close()


# ==================== ТОЧКА ВХОДУ ====================

def main():
    """Основна функція програми."""
    parser = argparse.ArgumentParser(
        description="Отримання статистики органічного трафіку з Ahrefs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Приклади використання:
  python ahrefs_parser.py --domain example.com
  python ahrefs_parser.py --domain google.com --verbose
        """
    )
    
    parser.add_argument(
        "--domain", 
        default="dou.ua",
        help="Домен для перевірки трафіку (за замовчуванням: dou.ua)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Детальне логування"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    logging.info(f"Початок перевірки домену: {args.domain}")
    
    token = solve_captcha()
    if token:
        result = fetch_traffic(token, args.domain)
        print(result)
    else:
        print("❌ Капчу не розв'язано, завершення.")
        sys.exit(1)

if __name__ == "__main__":
    main()
