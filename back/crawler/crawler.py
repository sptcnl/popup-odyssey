from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import pandas as pd
import json
import psycopg2
from psycopg2.extras import execute_values
from sqlalchemy import create_engine
import os
from datetime import datetime
from urllib.parse import quote_plus

def create_driver():
    """안전한 ChromeDriver 생성"""
    chrome_options = Options()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    
    service = Service("/usr/local/bin/chromedriver")
    return webdriver.Chrome(service=service, options=chrome_options)

def get_db_connection():
    """PostgreSQL 연결 - DATABASE_URL 사용"""
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        # DATABASE_URL 파싱해서 연결
        from sqlalchemy import create_engine
        from sqlalchemy.engine.url import URL
        engine = create_engine(database_url)
        return engine.raw_connection()

def get_sqlalchemy_engine():
    """SQLAlchemy 엔진 반환 - DATABASE_URL 사용"""
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        return create_engine(database_url)

def create_table(conn):
    """팝업스토어 테이블 생성"""
    cursor = conn.cursor()
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS popga_popups (
        id SERIAL PRIMARY KEY,
        crawl_id VARCHAR(50) NOT NULL,
        title VARCHAR(500) NOT NULL,
        category VARCHAR(100),
        location VARCHAR(200),
        status VARCHAR(50),
        period VARCHAR(100),
        url TEXT,
        crawled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(crawl_id, title, url)
    );
    """
    cursor.execute(create_table_sql)
    conn.commit()
    cursor.close()
    print("✅ 테이블 생성/확인 완료")

def crawl_popga_popups():
    """팝가 팝업스토어 크롤링"""
    driver = None
    try:
        driver = create_driver()
        url = "https://popga.co.kr/list/popup?periodTypes%5B0%5D=IN_PROGRESS&periodTypes%5B1%5D=READY&size=12&sorts%5B0%5D.order=activated_at&areaCodes%5B0%5D=1120011400&areaCodes%5B1%5D=1120011500"
        
        print("🚀 페이지 접속 중...")
        driver.get(url)
        
        # 로딩 스피너 사라질 때까지 대기
        wait = WebDriverWait(driver, 20)
        wait.until_not(EC.presence_of_element_located((By.CSS_SELECTOR, ".spinner")))
        time.sleep(3)
        
        # 무한스크롤로 모든 데이터 로드
        print("📜 데이터 로딩 중...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_count = 0
        while scroll_count < 5:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            scroll_count += 1
        
        # 팝업 article들 수집
        articles = driver.find_elements(By.CSS_SELECTOR, "article.relative")
        print(f"✅ 총 {len(articles)}개 팝업 발견!")
        
        popup_data = []
        crawl_id = f"popga_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        for i, article in enumerate(articles, 1):
            try:
                link_elem = article.find_element(By.CSS_SELECTOR, "a")
                link = link_elem.get_attribute("href")
                
                title = article.find_element(By.CSS_SELECTOR, "p.line-clamp-1").text.strip()
                category = article.find_element(By.CSS_SELECTOR, "span.rounded.bg-black-200").text.strip()
                location = article.find_element(By.CSS_SELECTOR, "p.text-black-600").text.strip()
                status = article.find_element(By.CSS_SELECTOR, "p.text-black-500").text.strip()
                period = article.find_element(By.CSS_SELECTOR, "p.text-xs.text-black-500").text.strip()
                
                popup_data.append({
                    "crawl_id": crawl_id,
                    "title": title,
                    "category": category,
                    "location": location,
                    "status": status,
                    "period": period,
                    "url": f"https://popga.co.kr{link}"
                })
                print(f"  📌 {i}. {title} ({category})")
                
            except Exception as e:
                print(f"  ⚠️  {i}번 항목 스킵: {str(e)[:50]}")
                continue
        
        return popup_data
        
    except Exception as e:
        print(f"❌ 크롤링 에러: {e}")
        return []
    
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

def save_to_postgres(popups):
    """PostgreSQL에 데이터 저장 - DATABASE_URL 우선 지원"""
    if not popups:
        print("😞 저장할 데이터 없음")
        return
    
    conn = None
    try:
        engine = get_sqlalchemy_engine()
        conn = get_db_connection()
        create_table(conn)
        
        # 데이터프레임 생성 후 저장
        df = pd.DataFrame(popups)
        df.to_sql('popga_popups', engine, if_exists='append', index=False, method='multi')
        
        # 삽입된 건수 확인
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM popga_popups 
            WHERE crawl_id = %s
        """, (popups[0]['crawl_id'],))
        count = cursor.fetchone()[0]
        cursor.close()
        
        print(f"✅ PostgreSQL에 {count}개 데이터 저장 완료!")
        print(f"📊 크롤링 배치 ID: {popups[0]['crawl_id']}")
        print(f"🔗 DATABASE_URL 사용: {'Yes' if os.getenv('DATABASE_URL') else 'No (LOCAL_DB vars)'}")
        
    except Exception as e:
        print(f"❌ DB 저장 에러: {e}")
    finally:
        if conn:
            conn.close()

# 🚀 실행
if __name__ == "__main__":
    print("🎪 팝가 팝업스토어 크롤링 + PostgreSQL 저장 시작!")
    print(f"🔍 DATABASE_URL: {'설정됨' if os.getenv('DATABASE_URL') else '없음 (LOCAL_DB 사용)'}")
    
    # 크롤링 실행
    popups = crawl_popga_popups()
    
    if popups:
        # 1. CSV 저장
        df = pd.DataFrame(popups)
        df.to_csv("popga_popups.csv", index=False, encoding='utf-8-sig')
        print(f"💾 {len(popups)}개 팝업을 popga_popups.csv에 저장!")
        
        # 2. JSON 저장
        with open("popga_popups.json", "w", encoding="utf-8") as f:
            json.dump(popups, f, ensure_ascii=False, indent=2)
        print("💾 JSON 파일도 저장 완료!")
        
        # 3. PostgreSQL 저장
        save_to_postgres(popups)
        
        # 결과 출력
        print("\n📋 최종 결과 미리보기:")
        print(df.head().to_string(index=False))
    else:
        print("😞 데이터 수집 실패. 네트워크나 사이트 변경 확인하세요.")