"""
Скрипт для ручного прохождения Cloudflare и сохранения cookies.

ИНСТРУКЦИЯ:
1. Запустить этот скрипт
2. В открывшемся браузере ВРУЧНУЮ пройти капчу Cloudflare
3. После прохождения нажать Enter в терминале
4. Cookies будут сохранены и использованы в будущих запросах
"""
from DrissionPage import ChromiumPage
import pickle
import os

COOKIES_FILE = "cf_cookies.pkl"
URL = "https://www.automobile-catalog.com/"

def save_cookies():
    print("=" * 60)
    print("РУЧНОЙ ОБХОД CLOUDFLARE")
    print("=" * 60)
    print()
    print("1. Сейчас откроется браузер")
    print("2. ВРУЧНУЮ пройдите капчу Cloudflare")
    print("3. Дождитесь загрузки сайта automobile-catalog.com")
    print("4. Вернитесь сюда и нажмите Enter")
    print()


    # Use local folder to avoid permission errors in Temp
    from DrissionPage import ChromiumOptions
    co = ChromiumOptions()
    co.set_user_data_path("drission_profile")

    page = ChromiumPage(addr_or_opts=co)
    page.get(URL)

    input(">>> Пройдите капчу в браузере, затем нажмите Enter здесь... ")

    # Проверяем, прошли ли CF
    title = page.title
    print(f"Текущий заголовок: {title}")

    if "Cloudflare" in title or "Just a moment" in title or "Один момент" in title:
        print("❌ Похоже, капча не пройдена. Попробуйте еще раз.")
        page.quit()
        return False

    # Сохраняем cookies
    cookies = page.cookies()
    with open(COOKIES_FILE, 'wb') as f:
        pickle.dump(cookies, f)

    print(f"✅ Cookies сохранены в {COOKIES_FILE}")
    print(f"   Теперь парсер будет использовать эти cookies автоматически!")

    page.quit()
    return True

def load_cookies(page):
    """Загрузить cookies из файла в браузер."""
    if not os.path.exists(COOKIES_FILE):
        return False

    try:
        with open(COOKIES_FILE, 'rb') as f:
            cookies = pickle.load(f)

        for cookie in cookies:
            page.set.cookies(cookie)

        print(f"✅ Загружены cookies из {COOKIES_FILE}")
        return True
    except Exception as e:
        print(f"⚠️ Ошибка загрузки cookies: {e}")
        return False

if __name__ == "__main__":
    save_cookies()
