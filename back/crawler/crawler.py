from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time, datetime
import pandas as pd
import json
from sqlalchemy import create_engine
import os
import re
from dotenv import load_dotenv
import requests
import urllib.request
from urllib.parse import urlparse, unquote
import hashlib


# 환경변수 로드
load_dotenv('/app/.env')


def download_popup_image(img_url, popup_name, base_path="/app/data/images"):
    """팝업 대표 이미지 다운로드"""
    if not img_url:
        return None
    
    try:
        # 디렉토리 생성
        os.makedirs(base_path, exist_ok=True)
        
        # 파일명 생성 (popup_name + 해시)
        name_hash = hashlib.md5(popup_name.encode()).hexdigest()[:8]
        safe_name = re.sub(r'[^\w\s-]', '', popup_name)[:30].strip()
        filename = f"{safe_name}_{name_hash}.webp"
        image_path = os.path.join(base_path, filename)
        
        # 이미지 다운로드
        print(f"    🖼️  이미지 다운로드: {filename}")
        urllib.request.urlretrieve(img_url, image_path)
        print(f"    ✅ 이미지 저장: {image_path}")
        
        return image_path
    except Exception as e:
        print(f"    ❌ 이미지 다운 실패: {str(e)[:30]}")
        return None


def validate_url(url):
    """URL 유효성 검사 및 정규화"""
    if not url or not isinstance(url, str):
        return False, ""
    
    url = url.strip()
    if url.count("https://popga.co.kr") > 1:
        url = re.sub(r'https://popga\.co\.krhttps://popga\.co\.kr', 'https://popga.co.kr', url)
    
    url_pattern = re.compile(r'^https?://', re.IGNORECASE)
    if not url_pattern.match(url):
        if url.startswith("/"):
            url = f"https://popga.co.kr{url}"
        else:
            url = f"https://popga.co.kr/{url}"
    
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            return True, url
        return False, ""
    except:
        return False, ""


def geocode_naver_map(address, client_id, client_secret):
    """네이버 지오코드 API → 좌표 튜플 반환 (Point 제거)"""
    if not all([address, client_id, client_secret]):
        print(f"  ❌ 지오코딩 실패: 환경변수 누락 ({address[:20]}...)")
        return None
    
    url = "https://maps.apigw.ntruss.com/map-geocode/v2/geocode"
    headers = {
        "X-NCP-APIGW-API-KEY-ID": client_id.strip(),
        "X-NCP-APIGW-API-KEY": client_secret.strip(),
        "Accept": "application/json"
    }
    params = {"query": address.strip()}
    
    try:
        print(f"  🗺️  지오코딩 요청: {address[:30]}...")
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        print(f"  📡 응답 상태: {data.get('status')}")
        
        if data.get('status') == 'OK' and data.get('addresses'):
            coords = data['addresses'][0]
            if coords.get('x') and coords.get('y'):
                return {
                    'geo_x': float(coords['x']),  # 경도
                    'geo_y': float(coords['y'])   # 위도
                }
        print(f"  ❌ API 실패: {data.get('status', 'Unknown')}")
        return None
        
    except Exception as e:
        print(f"  ❌ 지오코딩 에러: {str(e)[:50]}")
        return None

def create_driver():
    """Chrome 드라이버 생성 (Headless)"""
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
    """DB 연결"""
    database_url = os.getenv('DATABASE_URL')
    if database_url:
        engine = create_engine(database_url)
        return engine.raw_connection()
    return None


def scrape_detail_page(driver, detail_url):
    """상세 페이지 크롤링 - 이미지 정확히 수정 + 혜택 파싱 개선"""
    try:
        print(f"  🔍 {detail_url}")
        driver.get(detail_url)
        time.sleep(4)

        # ===== 대표 이미지 추출 (정확한 XPath) =====
        image_url = ''
        try:
            # 1순위: btn-magnify-popup-image 내부 img (가장 확실함)
            try:
                img_elem = driver.find_element(By.XPATH, "//button[@id='btn-magnify-popup-image']//img[1]")
                image_url = img_elem.get_attribute('src')
            except:
                # 2순위: aspect-[4/5] 클래스 내부 첫 번째 img
                img_elems = driver.find_elements(By.XPATH, "//div[contains(@class,'aspect-[4/5]')]//img")
                if img_elems:
                    image_url = img_elems[0].get_attribute('src')
            
            # 3순위: 메인 섹션 첫 번째 대표 이미지
            if not image_url:
                img_elems = driver.find_elements(By.XPATH, "//section//img[contains(@src,'thumbnail.webp')][1]")
                if img_elems:
                    image_url = img_elems[0].get_attribute('src')
            
            if image_url:
                print(f"    🖼️  대표 이미지: {image_url[-50:]}")
            else:
                print("    ⚠️  대표 이미지 없음")
                
        except Exception as e:
            print(f"    ⚠️  이미지 추출 에러: {str(e)[:30]}")

        # 주소
        address = ''
        try:
            address = driver.find_elements(By.XPATH, 
                "//h3[contains(text(),'위치')]/following::p[contains(@class,'text-black-800')]")[0].text.strip()
        except: pass
        
        # 기간
        detailed_period = ''
        try:
            detailed_period = driver.find_elements(By.XPATH, 
                "//h3[contains(text(),'일정')]/following::p[contains(@class,'font-bold')][1]")[0].text.strip()
        except: pass
        
        # 운영시간
        hours_elems = driver.find_elements(By.XPATH, 
            "//h3[contains(text(),'일정')]/following::p[not(contains(@class,'font-bold'))][position()<4]")
        opening_hours_list = []
        for elem in hours_elems:
            text = elem.text.strip()
            if (text.startswith('📢') or 
                re.search(r'\d{2}\.\s*\d{1,2}\.\s*\d{1,2}', text) or
                any(x in text for x in ['[브랜드', '[팝업', '[추천', '[실시간', '[주차']) or
                len(text) > 30):
                continue
            if (re.search(r'[0-2]?[0-9]:[0-5][0-9]\s*~', text) or 
                re.search(r'(월|화|수|목|금|토|일).*?[0-2]?[0-9]:[0-5][0-9]', text)):
                opening_hours_list.append(text)
        opening_hours = ' | '.join(opening_hours_list)
        
        # 공지사항
        notice = ''
        try:
            notice_elems = driver.find_elements(By.XPATH, 
                "//h3[contains(text(),'공지사항')]/following::div[contains(@class,'border')]"
                "//p[contains(text(),'📢')] | "
                "//h3[contains(text(),'공지사항')]/following::p[contains(text(),'📢')]"
            )
            if notice_elems:
                notice = ' | '.join([e.text.strip() for e in notice_elems[:3]])
        except: pass
        
        # ================================
        # 혜택 파싱 - 개선된 버전
        # ================================
        visit_events = on_site_events = purchase_events = other_events = ''
        
        try:
            print("  🎁 혜택 섹션 탐색 중...")
            
            # rounded-full 버튼들 우선 찾기 (가장 정확)
            benefit_buttons = driver.find_elements(By.XPATH, 
                "//h3[contains(text(),'혜택')]/following::button[contains(@class,'rounded-full')]"
            )
            
            # 더 넓은 범위에서 버튼 찾기
            if not benefit_buttons:
                benefit_buttons = driver.find_elements(By.XPATH, 
                    "//h3[contains(text(),'혜택')]/following::button[1][position()<=10]"
                )
            
            print(f"    📋 버튼: {len(benefit_buttons)}개 발견")
            
            # 각 버튼 처리
            for i, btn in enumerate(benefit_buttons):
                btn_text = btn.text.strip()
                if not btn_text or len(btn_text) < 2: 
                    continue
                
                print(f"    🔘 [{i+1}] '{btn_text}'")
                
                # 각 버튼 다음 설명 찾기
                desc_elems = driver.find_elements(By.XPATH, 
                    f"//button[contains(text(),'{btn_text}')]/following::div[contains(@class,'whitespace-pre-line')][1]"
                )
                desc_text = desc_elems[0].text.strip()[:150] if desc_elems else f"설명없음({i+1})"
                
                benefit_info = f"{btn_text}: {desc_text}"
                print(f"    📝 '{btn_text}' → '{desc_text[:30]}...'")
                
                # 4분류
                btn_lower = btn_text.lower()
                if any(x in btn_lower for x in ['방문']):
                    visit_events = benefit_info
                    print(f"    👤 방문 → ✅")
                elif any(x in btn_lower for x in ['현장', '체험', '포토', '이벤트', 'sns', '인증']):
                    on_site_events = benefit_info
                    print(f"    🎁 현장 → ✅")
                elif any(x in btn_lower for x in ['구매', '고객', '할인', '결제']):
                    purchase_events = benefit_info
                    print(f"    🛒 구매 → ✅")
                elif any(x in btn_lower for x in ['기타', '주차', '예약']):
                    other_events = benefit_info
                    print(f"    📦 기타 → ✅")
                else:
                    print(f"    ❓ 분류불가: {btn_lower}")
            
        except Exception as e:
            print(f"  ⚠️ 혜택 파싱 실패: {str(e)[:50]}")
        
        # 로그 출력
        print(f"    👤 방문: {visit_events[:30] or '없음'}...")
        print(f"    🎁 현장: {on_site_events[:30] or '없음'}...")
        print(f"    🛒 구매: {purchase_events[:30] or '없음'}...")
        print(f"    📦 기타: {other_events[:30] or '없음'}...")
        print("    ✅")
        
        return {
            'address': address,
            'detailed_period': detailed_period,
            'opening_hours': opening_hours,
            'notice': notice,
            'visit_events': visit_events,
            'on_site_events': on_site_events,
            'purchase_events': purchase_events,
            'other_events': other_events,
            'image_url': image_url,
            'image_path': ''
        }
        
    except Exception as e:
        print(f"    ❌ 전체 에러: {str(e)[:50]}")
        return {
            'address': '', 'detailed_period': '', 'opening_hours': '',
            'notice': '', 'visit_events': '', 'on_site_events': '', 
            'purchase_events': '', 'other_events': '',
            'image_url': '', 'image_path': ''
        }


def crawl_popga_popups():
    """팝가 리스트 크롤링 - 수정된 선택자"""
    driver = None
    try:
        driver = create_driver()
        url = "https://popga.co.kr/list/popup?periodTypes%5B0%5D=IN_PROGRESS&periodTypes%5B1%5D=READY&size=12&sorts%5B0%5D.order=activated_at&areaCodes%5B0%5D=1120011400&areaCodes%5B1%5D=1120011500"
        
        print("🚀 리스트 접속...")
        driver.get(url)
        
        # 로딩 대기 개선
        try:
            WebDriverWait(driver, 20).until_not(EC.presence_of_element_located((By.CSS_SELECTOR, ".spinner")))
        except:
            print("  ⚠️ spinner 없음, 일반 대기")
        time.sleep(5)
        
        # 무한 스크롤
        print("📜 무한 스크롤...")
        last_height = driver.execute_script("return document.body.scrollHeight")
        for _ in range(5):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height: 
                break
            last_height = new_height
        
        # 더 유연한 리스트 아이템 찾기
        articles = driver.find_elements(By.CSS_SELECTOR, "article.relative, article[class*='relative'], div[role='article']")
        if not articles:
            articles = driver.find_elements(By.XPATH, "//a[contains(@href,'/popup/')]/ancestor::article | //a[contains(@href,'/popup/')]/parent::*")
        
        print(f"✅ {len(articles)}개 팝업 발견")
        
        popup_data = []
        for idx in range(len(articles)):
            try:
                article = articles[idx]
                i = idx + 1
                
                # 링크 찾기
                link_elems = article.find_elements(By.CSS_SELECTOR, "a")
                if not link_elems:
                    continue
                link_elem = link_elems[0]
                link = link_elem.get_attribute("href")
                url_valid, clean_url = validate_url(link or "")
                
                # 기본 정보
                title_elems = article.find_elements(By.CSS_SELECTOR, "p.line-clamp-1, h1, h2, h3, [class*='title'], [class*='name']")
                title = title_elems[0].text.strip() if title_elems else f"팝업_{i}"
                
                category_elems = article.find_elements(By.CSS_SELECTOR, "span.rounded.bg-black-200, [class*='category']")
                category = category_elems[0].text.strip() if category_elems else "미분류"
                
                location_elems = article.find_elements(By.CSS_SELECTOR, "p.text-black-600, [class*='location']")
                location = location_elems[0].text.strip() if location_elems else ""
                
                status_elems = article.find_elements(By.CSS_SELECTOR, "p.text-black-500, [class*='status']")
                status = status_elems[0].text.strip() if status_elems else "운영중"
                
                period_elems = article.find_elements(By.CSS_SELECTOR, "p.text-xs.text-black-500, [class*='period']")
                period = period_elems[0].text.strip() if period_elems else ""
                
                if url_valid:
                    popup_data.append({
                        "title": title, "category": category,
                        "location": location, "status": status, 
                        "period": period, "url": clean_url
                    })
                    print(f"  📋 [{i}/{len(articles)}] {title[:30]}...")
                    
            except Exception as e:
                print(f"  ❌ 리스트 [{i}/{len(articles)}] 스킵: {str(e)[:30]}")
                continue
        
        return popup_data
        
    except Exception as e:
        print(f"❌ 리스트 전체 에러: {e}")
        return []
    finally:
        if driver:
            driver.quit()


def process_and_validate_popups(raw_popups):
    """상세 크롤링 + 지오코딩"""
    validated_popups = []
    naver_client_id = os.getenv('NAVER_GEO_CLIENT_ID')
    naver_client_secret = os.getenv('NAVER_GEO_CLIENT_SECRET')
    driver = create_driver()
    
    db_conn = None
    try:
        db_conn = get_db_connection()
    except:
        print("⚠️ DB 연결 실패")
        db_conn = None
    
    total_count = len(raw_popups)
    for idx in range(total_count):
        i = idx + 1
        popup = raw_popups[idx]
        
        try:
            print(f"\n[{i}/{total_count}] {popup.get('title', 'No Title')[:30]}...")
            
            url_valid, clean_url = validate_url(popup.get('url', ''))
            if not url_valid: 
                continue
            
            detail_data = scrape_detail_page(driver, clean_url)

            # ===== 이미지 다운로드 =====
            image_path = download_popup_image(
                detail_data.get('image_url'), 
                popup.get('title', 'unknown')
            ) if detail_data.get('image_url') else None
            
            # 고유 ID 생성
            import time
            timestamp = int(time.time() * 1000) % 1000000
            safe_id = f"popga_{i:03d}_{timestamp:06d}"
            
            final_popup = {
                'id': safe_id,
                'popup_name': popup.get('title', ''),
                'image_url': detail_data.get('image_url', ''),
                'image_path': image_path,
                'address': detail_data['address'] or popup.get('location', ''),
                'category': popup.get('category', ''),
                'status': popup.get('status', ''),
                'popup_date': detail_data['detailed_period'] or popup.get('period', ''),
                'detail_link': clean_url,
                'notice': detail_data['notice'],
                'visit_events': detail_data['visit_events'],
                'on_site_events': detail_data['on_site_events'],
                'purchase_events': detail_data['purchase_events'],
                'other_events': detail_data.get('other_events', ''),
                'location': None,  # Point 객체 또는 None
                'geo_validated': False,
                'crawled_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            }

            # 네이버 지오코드 결과 처리
            geo_result = geocode_naver_map(final_popup['address'], 
                                        naver_client_id, naver_client_secret)
            if geo_result:
                final_popup.update({
                    'geo_x': geo_result['geo_x'],
                    'geo_y': geo_result['geo_y'],
                    'geo_validated': True
                })
                print(f"  ✅ 좌표: X={geo_result['geo_x']:.6f}, Y={geo_result['geo_y']:.6f}")
            
            validated_popups.append(final_popup)
            
        except Exception as e:
            print(f"❌ [{i}/{total_count}] 처리 실패: {str(e)[:50]}")
            continue
    
    driver.quit()
    
    # DB 저장 (지오코드 성공한 데이터만)
    if db_conn:
        geo_success = [p for p in validated_popups if p.get('geo_validated')]
        if geo_success:
            try:
                engine = create_engine(os.getenv('DATABASE_URL'))
                pd.DataFrame(geo_success).to_sql('popga_popups', engine, 
                                                if_exists='append', index=False)
                print(f"💾 DB 저장: {len(geo_success)}개")
            except Exception as e:
                print(f"⚠️ DB 저장 실패: {e}")
    
    # CSV/JSON 저장
    df = pd.DataFrame(validated_popups)
    df.to_csv("popga_detailed_popups.csv", index=False, encoding='utf-8-sig')
    with open("popga_detailed_popups.json", "w", encoding="utf-8") as f:
        json.dump(validated_popups, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 최종 완료: {len(validated_popups)}개")
    return validated_popups


if __name__ == "__main__":
    print("🎪 팝가 팝업 완전 크롤링 시작!")
    print("=" * 60)
    
    raw_popups = crawl_popga_popups()
    if raw_popups:
        validated_popups = process_and_validate_popups(raw_popups)
        
        print("\n📊 최종 통계:")
        df = pd.DataFrame(validated_popups)
        print(f"  💾 총 {len(validated_popups)}개")
        print(f"  🖼️  이미지: {df['image_path'].notna().sum()}개")
        print(f"  🗺️  지오코딩: {df['geo_validated'].sum()}개")
        print(f"  📍 서울: {(df['address'].str.contains('서울', na=False)).sum()}개")
        
        print("\n📋 미리보기:")
        display_cols = ['popup_name', 'image_path', 'address', 'popup_date', 
                       'visit_events', 'geo_validated']
        available_cols = [col for col in display_cols if col in df.columns]
        print(df[available_cols].head(3).to_string(index=False))
    else:
        print("❌ 리스트 크롤링 실패")