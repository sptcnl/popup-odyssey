import urllib.request
import urllib.parse
import os, json
import pandas as pd
import time
from dotenv import load_dotenv
from crawler import get_db_connection
from sqlalchemy import create_engine

load_dotenv('/app/.env')

client_id = "DoBZ6S3cPiPVVsfQrhiJ"
client_secret = "eyV7XvqlI2"

def naver_local_search(query, display=10, start=1):
    """모든 컬럼 포함한 API 호출"""
    encText = urllib.parse.quote(query)
    url = f"https://openapi.naver.com/v1/search/local.json?query={encText}&display={display}&start={start}"
    
    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", client_id)
    request.add_header("X-Naver-Client-Secret", client_secret)
    
    try:
        response = urllib.request.urlopen(request)
        if response.getcode() == 200:
            data = json.loads(response.read().decode('utf-8'))
            print(f"📊 API 응답: total={data.get('total',0)}, start={data.get('start',0)}, display={data.get('display',0)}")
            return data.get('items', [])
    except Exception as e:
        print(f"❌ API 호출 실패: {e}")
    return []

def full_pagination_all_columns(query, max_pages=10, max_results=100):
    """모든 컬럼 + 페이지네이션 + 중복제거"""
    all_places = []
    seen_titles = set()
    
    print(f"🔍 '{query}' 완전 페이지네이션 시작 (최대 {max_pages}페이지)")
    
    for page in range(1, max_pages + 1):
        start = (page - 1) * 10 + 1
        results = naver_local_search(query, 10, start)
        
        if not results:
            print(f"   ❌ {page}페이지 연결 실패")
            break
        
        new_items = 0
        for item in results:
            clean_title = item.get('title', '').replace('<b>', '').replace('</b>', '')
            if clean_title not in seen_titles and len(all_places) < max_results:
                # 모든 컬럼 정리
                place_data = {
                    'name': clean_title,
                    'address': item.get('roadAddress', ''),
                    'link': item.get('link', ''),
                    'detail_category': item.get('category', ''),
                    'geo_x': item.get('mapx', ''),
                    'geo_y': item.get('mapy', ''),
                    'is_public': True,
                    'created_at': pd.Timestamp.now(),
                    'updated_at': pd.Timestamp.now()
                }
                all_places.append(place_data)
                seen_titles.add(clean_title)
                new_items += 1
        
        print(f"📄 {page}페이지: {len(results)}개 요청 → {new_items}개 추가 (총 {len(all_places)}개)")
        
        if len(results) < 10:
            print("✅ 마지막 페이지")
            break
        
        time.sleep(0.2)  # API 호출 제한
    
    return all_places

# 🚀 실행
query = "성수동 맛집"
all_places = full_pagination_all_columns(query, max_pages=1, max_results=5)

# 📊 완전 컬럼 출력
print(f"\n🎉 최종 {len(all_places)}개 수집 완료!\n")
print("📋 모든 컬럼 미리보기 (상위 5개):")
print("-" * 120)

for i, place in enumerate(all_places[:5], 1):
    print(f"{i}. {place['name']:<20} | {place['detail_category']:<20}")
    print(f"   📍 {place['address']}")
    print(f"   🌐 {place['link'][:50]}...")
    print(f"   📌 좌표: {place['geo_x']}, {place['geo_y']}")
    print("-" * 120)

# 💾 모든 컬럼 포함한 DataFrame 저장
if all_places:
    df = pd.DataFrame(all_places)
    
    # 컬럼 순서 최적화
    display_columns = [
        'title', 'category', 'roadAddress', 
        'mapx', 'mapy', 'link'
    ]
    df = df.reindex(columns=display_columns)
    
    # 커스텀 컬럼명
    df.columns = [
        'name', 'detail_category', 'address', 
        'geo_x', 'geo_y', 'link'
    ]
    
    # 타임스탬프 파일명
    timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    csv_file = f"성수동_맛집_완전판_{timestamp}.csv"
    xlsx_file = f"성수동_맛집_완전판_{timestamp}.xlsx"
    
    df.to_csv(csv_file, index=False, encoding='utf-8-sig')
    df.to_excel(xlsx_file, index=False)
    
    print(f"\n💾 저장완료:")
    print(f"   📄 {csv_file}")
    print(f"   📊 {xlsx_file}")
    print(f"\n📊 데이터 정보:")
    print(f"   총 {len(df)}개 | 컬럼 {len(df.columns)}개")
    print(f"   컬럼: {list(df.columns)}")
    
    # 상위 10개 미리보기
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)
    print("\n📋 상위 10개 맛집:")
    print(df.head(10).to_string(max_colwidth=20))

    db_conn = None
    try:
        db_conn = get_db_connection()
    except Exception as e:
        print(f"⚠️ DB 연결 실패: {e}")
    
    if db_conn and all_places:
        try:
            engine = create_engine(os.getenv('DATABASE_URL'))
        
            # DataFrame 준비
            df_db = pd.DataFrame(all_places)
            df_db['created_at'] = pd.Timestamp.now()
            df_db.columns = [col.replace(' ', '_').lower() for col in df_db.columns]
            
            # ✅ Engine에 직접 저장
            df_db.to_sql('places_place', engine, if_exists='append', index=False)
            print(f"💾 DB 저장 성공: {len(df_db)}개")
            engine.dispose()
        
        except Exception as e:
            print(f"⚠️ DB 저장 실패: {e}")
    else:
        print("⏭️ DB 저장 생략 (연결 실패 또는 데이터 없음)")

    print("\n🎉 모든 작업 완료!")