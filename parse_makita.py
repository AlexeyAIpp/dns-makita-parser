import csv
import re
from pathlib import Path
from urllib.parse import urldefrag

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait


URL = "https://www.vseinstrumenti.ru/category/shurupoverty-1774/makita-1/"
OUTPUT = Path(__file__).resolve().parent / "makita_spb.csv"

CARD_SELECTOR = '[data-qa="products-tile-horizontal"]'

FIELDS = [
    "Модель",
    "Цена, руб.",
    "Ссылка на товар",
    "Оценка",
    "Количество отзывов",
]


def get_text(element, selector):
    found = element.find_elements(By.CSS_SELECTOR, selector)
    return found[0].text.strip() if found else ""


def has_stock(availability):
    """Принимаем только явно указанное положительное количество."""
    lines = availability.lower().splitlines()

    for line in lines:
        match = re.search(
            r"([0-9][0-9\s\u00a0\u202f]*)\s*шт\.\s*"
            r"(?:в магазинах сегодня|есть на складе)",
            line,
        )

        if match:
            quantity = int(re.sub(r"\D", "", match.group(1)))
            if quantity > 0:
                return True

    return False


def collect_products(browser):
    rows = []
    seen = set()
    skipped_stock = 0
    skipped_price = 0

    cards = browser.find_elements(By.CSS_SELECTOR, CARD_SELECTOR)
    print(f"Найдено карточек: {len(cards)}")

    for card in cards:
        name_elements = card.find_elements(
            By.CSS_SELECTOR,
            '[data-qa="product-name"]',
        )

        if not name_elements:
            continue

        name_element = name_elements[0]
        model = name_element.text.strip()

        if (
            "makita" not in model.lower()
            or "шурупов" not in model.lower()
        ):
            continue

        availability = get_text(
            card,
            '[data-qa="product-availability"]',
        )

        if not has_stock(availability):
            skipped_stock += 1
            continue

        href = name_element.get_attribute("href")
        if not href:
            continue

        url = urldefrag(href)[0]

        if url in seen:
            continue

        price_text = get_text(
            card,
            '[data-qa="product-price-current"]',
        )

        price_match = re.search(
            r"(\d[\d\s\u00a0\u202f]*)\s*₽",
            price_text,
        )

        if not price_match:
            skipped_price += 1
            continue

        price = int(
            re.sub(r"\D", "", price_match.group(1))
        )

        rating_text = get_text(
            card,
            '[data-qa="product-rating"]',
        )

        rating_match = re.match(
            r"\s*(\d+(?:[.,]\d+)?)",
            rating_text,
        )

        reviews_match = re.search(
            r"\(\s*([\d\s\u00a0\u202f]+)\s*\)",
            rating_text,
        )

        rating = (
            rating_match.group(1)
            if rating_match
            else "Не указана"
        )

        reviews = (
            re.sub(r"\D", "", reviews_match.group(1))
            if reviews_match
            else "Не указано"
        )

        rows.append({
            "Модель": model,
            "Цена, руб.": price,
            "Ссылка на товар": url,
            "Оценка": rating,
            "Количество отзывов": reviews,
        })

        seen.add(url)

    print(f"Без подтверждённого наличия: {skipped_stock}")
    print(f"Без читаемой цены: {skipped_price}")

    return rows


def main():
    with webdriver.Firefox() as browser:
        browser.set_page_load_timeout(60)
        browser.maximize_window()
        browser.get(URL)

        print("В открывшемся Firefox выберите Санкт-Петербург.")
        print("Проверьте, что показаны шуруповёрты Makita.")
        print("Прокрутите текущую страницу до конца.")
        print("Дождитесь загрузки карточек и цен.")

        confirmation = input(
            "\nЕсли город выбран верно, введите: Санкт-Петербург\n> "
        ).strip()

        if confirmation.casefold() != "санкт-петербург":
            print("Город не подтверждён. Сбор отменён.")
            return

        WebDriverWait(browser, 20).until(
            lambda driver: driver.find_elements(
                By.CSS_SELECTOR,
                CARD_SELECTOR,
            )
        )

        rows = collect_products(browser)

        if not rows:
            print("Подходящих товаров нет. CSV не изменён.")
            return

        with OUTPUT.open(
            "w",
            newline="",
            encoding="utf-8-sig",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=FIELDS,
                delimiter=";",
            )
            writer.writeheader()
            writer.writerows(rows)

        print(f"\nСохранено товаров: {len(rows)}")
        print(f"Результат: {OUTPUT}")


if __name__ == "__main__":
    main()