import pandas as pd
import requests
from datetime import datetime
from typing import Dict, Optional
import os, time, environ
from sqlalchemy import create_engine
import numpy as np
from config.settings import BASE_DIR

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

def get_db_connection():
    """DB 연결"""
    database_url = "postgresql://{user}:{password}@db:5432/{dbname}".format(
        user=env("LOCAL_DB_USER"),
        password=env("LOCAL_DB_PASSWORD"),
        dbname=env("LOCAL_DB_NAME")
    )
    if database_url:
        engine = create_engine(database_url, pool_pre_ping=True)
        return engine
    return None

def geocode_naver_map(address: str, client_id: str, client_secret: str) -> Optional[Dict[str, float]]:
    """네이버 지오코드 API → 좌표 튜플 반환"""
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
        
        if data.get('status') == 'OK' and data.get('addresses'):
            coords = data['addresses'][0]
            if coords.get('x') and coords.get('y'):
                return {
                    'geo_x': float(coords['x']),  # 경도
                    'geo_y': float(coords['y'])   # 위도
                }
        return None
        
    except Exception as e:
        print(f"  ❌ 지오코딩 에러: {str(e)[:50]}")
        return None

def validate_popup_data(df: pd.DataFrame) -> pd.DataFrame:
    """주소 인증 및 Place 모델 형식으로 변환"""
    print("🔍 팝업스토어 주소 인증 시작...")
    
    client_id = env('NAVER_GEO_CLIENT_ID')
    client_secret = env('NAVER_GEO_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        print("❌ 환경변수 NAVER_GEO_CLIENT_ID/CLIENT_SECRET 설정 필요!")
        return df
    
    results = []
    success_count = 0
    
    # ✅ CSV 구조에 완벽 맞춤: 안전한 iterrows + row.get()
    for row_num, (idx, row) in enumerate(df.iterrows(), 1):
        # ✅ CSV 컬럼명과 정확히 일치하는 안전한 추출
        category = str(row.get('카테고리', 'N/A'))
        name = str(row.get('팝업스토어명', ''))[:100]
        start_date = str(row.get('시작일', '')) if pd.notna(row.get('시작일', '')) else ''
        end_date = str(row.get('종료일', '')) if pd.notna(row.get('종료일', '')) else ''
        address = str(row.get('위치', '')).strip('"').strip()[:200]
        
        print(f"\n[{row_num}/{len(df)}] {category} | {name[:20]}...")
        
        today = datetime(2026, 1, 13)
        
        # 날짜 파싱 (빈 값 안전 처리)
        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d') if start_date and len(start_date) == 10 else datetime(1900, 1, 1)
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') if end_date and len(end_date) == 10 else datetime(2100, 1, 1)
        except:
            start_dt, end_dt = datetime(1900, 1, 1), datetime(2100, 1, 1)
        
        coords = None
        status = 'closed'
        if start_dt <= today <= end_dt:
            coords = geocode_naver_map(address, client_id, client_secret)
            if coords:
                status = 'open'
                success_count += 1
        
        # 안전한 좌표 처리
        geo_x = None
        geo_y = None
        if coords and coords.get('geo_x') is not None and coords.get('geo_y') is not None:
            geo_x = coords['geo_x']
            geo_y = coords['geo_y']
        
        result = {
            'user_id': None,
            'is_public': True,
            'name': name,
            'image_path': None,
            'address': address,
            'status': status,
            'start_date': start_date if start_date else None,
            'end_date': end_date if end_date else None,
            'geo_x': geo_x,
            'geo_y': geo_y,
            'geo_validated': bool(geo_x and geo_y),
            'link': None,
            'detail_category': category[:100],
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }
        results.append(result)
        time.sleep(0.1)
    
    print(f"\n🎉 주소 인증 완료! 성공: {success_count}/{len(df)}")
    return pd.DataFrame(results)

def save_to_database(df: pd.DataFrame, engine):
    """places_place 테이블 저장 - fillna 완전 제거"""
    try:
        print("💾 DB 저장 시작...")
        
        # ✅ 1. copy() + 컬럼 표준화
        df_clean = df.copy()
        df_clean.columns = [col.lower().replace(' ', '_') for col in df_clean.columns]
        
        # ✅ 2. 문자열 컬럼만 안전하게 처리 (100자 제한)
        string_columns = ['name', 'address', 'popup_date', 'detail_category']
        for col in string_columns:
            if col in df_clean.columns:
                # NaN을 빈 문자열로 + 길이 제한
                df_clean[col] = df_clean[col].fillna('').astype(str).str[:100]
        
        # ✅ 3. 숫자 컬럼 (NULL 허용)
        for col in ['geo_x', 'geo_y']:
            if col in df_clean.columns:
                df_clean[col] = pd.to_numeric(df_clean[col], errors='coerce')
        
        # ✅ 4. Boolean 컬럼
        for col in ['geo_validated', 'is_public']:
            if col in df_clean.columns:
                df_clean[col] = df_clean[col].fillna(False).astype(bool)
        
        # ✅ 5. 날짜 컬럼 확실히 추가
        df_clean['created_at'] = pd.Timestamp.now()
        df_clean['updated_at'] = pd.Timestamp.now()
        
        # ✅ 6. NULL이 있는 컬럼만 제거하지 않고 그대로 둠 (PostGIS NULL 허용)
        df_unique = df_clean.drop_duplicates(subset=['name', 'address'], keep='last')
        print(f"📊 저장 데이터: {len(df_unique)}개")
        print(f"📋 컬럼: {list(df_unique.columns)}")
        
        # ✅ 7. fillna 없이 직접 to_sql (PostgreSQL NULL 자동 처리)
        df_unique.to_sql(
            name='places_place',
            con=engine,
            if_exists='append',
            index=False,
            method='multi'
        )
        
        print(f"💾 ✅ DB 저장 성공: {len(df_unique)}개 팝업스토어")
        return True
        
    except Exception as e:
        print(f"❌ DB 저장 실패: {str(e)}")
        print(f"📋 현재 컬럼: {list(df.columns)}")
        return False
    
# 실행 코드
if __name__ == "__main__":
    csv_filename = 'popups.csv'
    
    try:
        df = pd.read_csv(csv_filename, encoding='utf-8-sig')
        print(f"📁 {csv_filename} 로드 완료: {len(df)}개 팝업스토어")
        print(f"📋 컬럼: {list(df.columns)}")
    except FileNotFoundError:
        print(f"❌ {csv_filename} 파일을 같은 폴더에 넣어주세요!")
        exit(1)
    
    # 1. 주소 인증
    validated_df = validate_popup_data(df)
    
    # 2. CSV 백업
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    validated_df.to_csv(f'팝업스토어_인증완료_{timestamp}.csv', index=False, encoding='utf-8-sig')
    
    # 3. DB 저장 (진행중인 팝업만)
    engine = get_db_connection()
    if engine:
        now_open = validated_df[validated_df['status'] == 'open']
        if not now_open.empty:
            save_to_database(now_open, engine)
        else:
            print("ℹ️  진행중인 팝업스토어가 없습니다.")
        engine.dispose()
        print("🎉 전체 작업 완료!")
    else:
        print("⚠️ DB 연결 실패 - CSV만 저장됨")
    
    # 통계
    print(f"\n📊 최종 통계:")
    success_count = len(validated_df[validated_df['geo_validated'] == True])
    open_count = len(validated_df[validated_df['status'] == 'open'])
    success_rate = (success_count / len(validated_df)) * 100
    print(f"  - 인증 성공: {success_rate:.1f}% ({success_count}/{len(validated_df)})")
    print(f"  - 진행중 팝업: {open_count}개")
    print(f"  - CSV 백업: 팝업스토어_인증완료_{timestamp}.csv")