# Ahrefs Traffic Checker Parser

This project demonstrates how to fetch **organic traffic statistics** from Ahrefs' traffic checker using Python, Selenium, and AntiCaptcha (Cloudflare Turnstile solver).  
It also includes **Telegram notifications** for success, warnings, and errors.

⚠️ **Disclaimer:** This script is provided for educational purposes only.  
Parsing or bypassing protections on websites without permission may violate their Terms of Service.  
Please use responsibly and only for domains you are authorized to check.

---

## Features
- Solves **Cloudflare Turnstile CAPTCHA** via [AntiCaptcha](https://anti-captcha.com/).
- Requests data from Ahrefs’ internal endpoint with Selenium.
- Parses JSON response for `trafficMonthlyAvg`.
- Sends notifications to **Telegram chat** (optional).
- Accepts domain name as **command-line argument**.

---

## Requirements
- Python 3.9+
- Google Chrome installed
- ChromeDriver (auto-installed by `webdriver-manager`)

---

## Installation
```bash
git clone https://github.com/yourusername/ahrefs-traffic-checker.git
cd ahrefs-traffic-checker
pip install -r requirements.txt
```
---

## Environment Variables
Set your API keys and tokens as environment variables:

```bash
export ANTICAPTCHA_API_KEY="your-anticaptcha-key"
export TELEGRAM_TOKEN="your-telegram-bot-token"
export TELEGRAM_CHAT_ID="your-telegram-chat-id"
```

---

## Usage
Run for a single domain:
```bash
python script.py ahrefs.com
```

## Example Output
``bash
📊 Organic traffic (ahrefs.com): 123456
```
