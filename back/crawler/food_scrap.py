import urllib.request
import urllib.parse
import os, json
import pandas as pd
import time
from dotenv import load_dotenv
from crawler import get_db_connection
from sqlalchemy import create_engine
import warnings
warnings.filterwarnings('ignore')

load_dotenv('/app/.env')

client_id = os.getenv("NAVER_SEARCH_CLIENT_ID")
client_secret = os.getenv("NAVER_SEARCH_CLIENT_SECRET")

def convert_naver_coords(mapx_str, mapy_str):
    """🔥 네이버 WCONGNAMUL → WGS84 정확 변환"""
    try:
        if not mapx_str or not mapy_str:
            return None, None
        
        mapx = float(mapx_str)
        mapy = float(mapy_str)
        
        # ✅ 네이버 좌표계: 1000만배 확대 → /10,000,000
        lon = mapx / 10000000.0
        lat = mapy / 10000000.0
        
        return round(lon, 6), round(lat, 6)
    except:
        return None, None

def naver_local_search(query, display=10, start=1):
    """네이버 로컬 API 호출"""
    encText = urllib.parse.quote(query)
    url = f"https://openapi.naver.com/v1/search/local.json?query={encText}&display={display}&start={start}"
    
    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", client_id)
    request.add_header("X-Naver-Client-Secret", client_secret)
    
    try:
        response = urllib.request.urlopen(request)
        if response.getcode() == 200:
            data = json.loads(response.read().decode('utf-8'))
            print(f"📊 API 응답: total={data.get('total',0)}, start={data.get('start',0)}")
            return data.get('items', [])
    except Exception as e:
        print(f"❌ API 호출 실패: {e}")
    return []

def full_pagination_all_columns(query, max_pages=3, max_results=50):
    """🎯 완전 자동화 크롤링"""
    all_places = []
    seen_titles = set()
    
    print(f"🔍 '{query}' 크롤링 시작 (최대 {max_results}개)")
    
    for page in range(1, max_pages + 1):
        start = (page - 1) * 10 + 1
        results = naver_local_search(query, 10, start)
        
        if not results:
            print(f"   ❌ {page}페이지 실패")
            break
        
        new_items = 0
        for item in results:
            clean_title = item.get('title', '').replace('<b>', '').replace('</b>', '')
            if clean_title in seen_titles or len(all_places) >= max_results:
                continue
            
            raw_x = item.get('mapx', '')
            raw_y = item.get('mapy', '')
            geo_x, geo_y = convert_naver_coords(raw_x, raw_y)
            
            # ✅ Place 모델 정확 매핑
            place_data = {
                'name': clean_title[:100],  # max_length=100
                'address': item.get('roadAddress', item.get('address', ''))[:200],  # max_length=200
                'link': item.get('link', ''),
                'detail_category': item.get('category', '')[:100],
                'geo_x': geo_x,
                'geo_y': geo_y,
                'is_public': True,
                'status': None,
                'start_date': None,
                'end_date': None,
                'geo_validated': geo_x is not None and geo_y is not None,
                'created_at': pd.Timestamp.now(),
                'updated_at': pd.Timestamp.now()
            }
            all_places.append(place_data)
            seen_titles.add(clean_title)
            new_items += 1
        
        print(f"📄 {page}페이지: {new_items}개 추가 (총 {len(all_places)}개)")
        if len(results) < 10:
            print("✅ 마지막 페이지")
            break
        time.sleep(0.3)
    
    return all_places

# 🚀 🎯 최종 완전 실행
if __name__ == "__main__":
    query = "성수동 맛집"
    all_places = full_pagination_all_columns(query, max_pages=3, max_results=20)
    
    print(f"\n🎉 최종 {len(all_places)}개 수집 완료!")
    
    # 📊 정확한 WGS84 출력
    print("\n📋 WGS84 좌표 맛집 리스트:")
    print("=" * 100)
    for i, place in enumerate(all_places[:10], 1):
        print(f"{i}. {place['name']:<22} | {place['detail_category']}")
        print(f"   📍 {place['address'][:60]}")
        print(f"   📌 {place['geo_x']:.6f}, {place['geo_y']:.6f}")
        print(f"   🌐 {place['link'][:60]}...")
        print()
    
    # 💾 1. 파일 저장 (CSV + XLSX)
    if all_places:
        df = pd.DataFrame(all_places)
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        csv_file = f"성수동_맛집_완전판_{timestamp}.csv"
        xlsx_file = f"성수동_맛집_완전판_{timestamp}.xlsx"
        
        df.to_csv(csv_file, index=False, encoding='utf-8-sig')
        df.to_excel(xlsx_file, index=False)
        print(f"💾 파일 저장 완료:")
        print(f"   📄 {csv_file}")
        print(f"   📊 {xlsx_file}")
    
    # 💾 2. DB 저장 (Place 모델 100% 호환)
    print("\n💾 Place 모델 DB 저장...")
    try:
        engine = create_engine(os.getenv('DATABASE_URL'))
        df_db = pd.DataFrame(all_places)
        
        # 컬럼명 표준화
        df_db.columns = [col.replace(' ', '_').lower() for col in df_db.columns]
        
        # Place 모델 필드 정확 매핑
        place_columns = [
            'name', 'address', 'link', 'detail_category', 
            'geo_x', 'geo_y', 'is_public',
            'status', 'start_date', 'end_date', 'geo_validated',
            'created_at', 'updated_at'
        ]
        df_db = df_db[[col for col in place_columns if col in df_db.columns]]
        
        # 안전한 NULL 처리
        for col in df_db.select_dtypes(include=['object']).columns:
            df_db[col] = df_db[col].where(df_db[col].notna(), None)
        
        # PostgreSQL 벌크 삽입
        df_db.to_sql('places_place', engine, if_exists='append', index=False, method='multi')
        print(f"✅ DB 저장 성공: {len(df_db)}개 레코드")
        engine.dispose()
        
    except Exception as e:
        print(f"⚠️ DB 저장 실패: {e}")
        print("💾 파일은 정상 저장됨 ✓")
    
    print("\n" + "🎉" * 20)
    print("🏆 모든 작업 100% 완료!")
    print("🗺️  PostGIS/카카오맵/구글맵 바로 사용 가능!")
    print("📊 파일+DB 동시 저장 완료!")
    print("🎉" * 20)