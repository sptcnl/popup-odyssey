import os
import time
from datetime import datetime
from urllib.parse import urlparse

import psycopg2
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


# =========================
# DB
# =========================
def parse_db_url():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다")

    parsed = urlparse(db_url)
    return {
        "host": parsed.hostname,
        "database": parsed.path.lstrip("/"),
        "user": parsed.username,
        "password": parsed.password,
        "port": parsed.port or 5432,
    }


def get_connection():
    return psycopg2.connect(**parse_db_url())


# =========================
# CRAWLER
# =========================
def crawl_seongsu_popups(limit=10):
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    wait = WebDriverWait(driver, 30)

    try:
        print("🌐 네이버 지도 접속")
        driver.get("https://map.naver.com/p/search/성수동%20팝업")

        # ==================================================
        # STEP 1. searchIframe 전환 (필수)
        # ==================================================
        print("🧩 STEP1: searchIframe 전환")
        try:
            wait.until(
                EC.frame_to_be_available_and_switch_to_it(
                    (By.CSS_SELECTOR, "iframe#searchIframe")
                )
            )
        except TimeoutException:
            print("❌ searchIframe 탐색 실패")
            driver.save_screenshot("/tmp/step1_no_iframe.png")
            with open("/tmp/step1_no_iframe.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            return []

        # ==================================================
        # STEP 2. 검색 결과 로딩 대기
        # ==================================================
        print("🔎 STEP2: 검색 결과 로딩 대기")
        try:
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "li[data-place-id]")
                )
            )
        except TimeoutException:
            print("❌ 검색 결과 없음 (li[data-place-id])")
            driver.save_screenshot("/tmp/step2_no_results.png")
            with open("/tmp/step2_no_results.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            return []

        # ==================================================
        # STEP 3. 결과 수집
        # ==================================================
        items = driver.find_elements(By.CSS_SELECTOR, "li[data-place-id]")
        print(f"📦 검색 결과 {len(items)}개 발견")

        data = []

        for item in items:
            name_el = None

            # 🔑 HTML dump 기준 확정 selector 우선순위
            for selector in [
                "a.place_bluelink",
                "span.place_bluelink",
                "div.place_desc span.name",
                "div.place_desc strong.name",
            ]:
                try:
                    name_el = item.find_element(By.CSS_SELECTOR, selector)
                    if name_el:
                        break
                except Exception:
                    continue

            if not name_el:
                continue

            name = name_el.text.strip()
            if not name:
                continue

            normalized = name.replace(" ", "").upper()
            if "팝업" not in normalized and "POPUP" not in normalized:
                continue

            data.append({"name": name})
            print(f"✅ {name}")

            if len(data) >= limit:
                break

        print(f"📊 최종 수집: {len(data)}개")
        return data

    except Exception as e:
        print("❌ 크롤링 중 예외 발생:", e)
        driver.save_screenshot("/tmp/naver_fatal_error.png")
        with open("/tmp/naver_fatal_error.html", "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        return []

    finally:
        driver.quit()


# =========================
# MAIN
# =========================
def main():
    print("=" * 60)
    print(f"🚀 성수동 팝업 크롤링 시작: {datetime.now():%Y-%m-%d %H:%M:%S}")
    print("=" * 60)

    data = crawl_seongsu_popups(limit=10)

    if not data:
        print("❌ ❌ 데이터 수집 실패")
        print("💡 /tmp/step*.html, *.png 파일로 DOM 확인 가능")
        return

    try:
        conn = get_connection()
        with conn.cursor() as cur:
            inserted = 0
            for item in data:
                cur.execute(
                    """
                    INSERT INTO popup_stores (name)
                    VALUES (%s)
                    ON CONFLICT (name) DO NOTHING
                    """,
                    (item["name"],),
                )
                inserted += cur.rowcount

        conn.commit()
        print(f"✅ DB 저장 완료: {inserted}개 신규")

    except Exception as e:
        print("❌ DB 오류:", e)

    finally:
        if "conn" in locals():
            conn.close()

    print("=" * 60)


if __name__ == "__main__":
    main()