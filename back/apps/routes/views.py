import os, json, logging, environ, requests, time, concurrent.futures
from typing import List, Dict, Any, Optional
from django.db import transaction
from django.core.cache import cache
from django.contrib.gis.geos import LineString, Point
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import numpy as np
from math import radians, sin, cos, sqrt, atan2
from drf_spectacular.utils import extend_schema, OpenApiResponse
from config.settings import BASE_DIR
from apps.routes.models import Route

logger = logging.getLogger(__name__)

env = environ.Env()
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

OSRM_URL = getattr(env, 'OSRM_URL', 'http://osrm-korea:5000')
logger.info(f"🔗 OSRM 자동 연결: {OSRM_URL}")

class HaversineCalculator:
    """📏 Haversine 직선거리 → 보행시간 변환 (OSRM 독립)"""
    
    WALKING_SPEED = 4.8  # km/h
    CAR_SPEED = 40.0     # km/h
    BIKE_SPEED = 15.0    # km/h
    
    @classmethod
    def distance(cls, lat1: float, lon1: float, lat2: float, lon2: float, mode: str = 'foot') -> float:
        """Haversine 공식 + 속도별 시간 변환 (초)"""
        if lat1 == lat2 and lon1 == lon2:
            return 0.0
            
        R = 6371.0
        lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(radians, [lat1, lon1, lat2, lon2])
        dlat, dlon = lat2_rad - lat1_rad, lon2_rad - lon1_rad
        
        a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance_km = R * c
        
        speed_map = {
            'foot': cls.WALKING_SPEED,
            'walking': cls.WALKING_SPEED,
            'car': cls.CAR_SPEED,
            'driving': cls.CAR_SPEED,
            'bike': cls.BIKE_SPEED,
            'cycling': cls.BIKE_SPEED
        }
        speed = speed_map.get(mode, cls.WALKING_SPEED)
        return (distance_km / speed) * 3600  # 초 단위

class OSRMDistanceCalculator:
    """🚀 OSRM 고속 거리 계산기 - 완전 Haversine 폴백"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PopupOdyssey/1.0',
            'Connection': 'keep-alive',
            'Accept': 'application/json'
        })
        self.haversine = HaversineCalculator()
        self.osrm_available = self._test_connection()
        logger.info(f"✅ OSRM 상태: {'사용가능' if self.osrm_available else 'Haversine 우선'}")
    
    def _test_connection(self) -> bool:
        """🔍 OSRM 연결 테스트 - 한국 좌표 + 올바른 URL"""
        try:
            # ✅ FIX 1: 한국 좌표 (서버 데이터와 일치)
            # ✅ FIX 2: 경로만 생성 (OSRM_URL 제외)
            test_path = "/route/v1/driving/126.9780,37.5665;126.9850,37.5700"
            test_url = f"{OSRM_URL}{test_path}?steps=false&overview=false"
            
            resp = self.session.get(test_url, timeout=5)
            return resp.status_code == 200 and resp.json().get('code') == 'Ok'
        except Exception as e:
            logger.debug(f"OSRM 연결 테스트 실패: {str(e)}")
            return False
    
    def get_duration_matrix(self, coordinates: List[List[float]], mode: str = 'foot') -> np.ndarray:
        """coordinates: [[lat1, lon1], [lat2, lon2], ...] → duration matrix(초)"""
        n = len(coordinates)
        if n == 0:
            return np.array([])
        
        # 1단계: Haversine 기본 매트릭스 (항상 안전)
        logger.info(f"🔄 Haversine 기본 매트릭스 생성 ({n}개)")
        matrix = np.full((n, n), 999999.0)
        np.fill_diagonal(matrix, 0)
        
        for i in range(n):
            for j in range(i+1, n):
                duration = self.haversine.distance(
                    coordinates[i][0], coordinates[i][1],
                    coordinates[j][0], coordinates[j][1], mode
                )
                matrix[i][j] = matrix[j][i] = duration
        
        # 2단계: OSRM 개선 (가능할 때만)
        if self.osrm_available and 2 <= n <= 30:
            try:
                logger.info(f"🚀 OSRM 매트릭스 계산 시도 ({n}개)")
                osrm_matrix = self._get_osrm_matrix(coordinates, mode)
                
                # 더 정확한 값만 OSRM 채택 (5km/86만초 이내)
                better_mask = (osrm_matrix < matrix) & (osrm_matrix < 500000)
                improved = np.sum(better_mask)
                matrix[better_mask] = osrm_matrix[better_mask]
                logger.info(f"✅ OSRM 개선 완료: {improved}/{n*(n-1)//2} 쌍 ({improved/(n*(n-1)//2)*100:.1f}%)")
            except Exception as e:
                logger.warning(f"❌ OSRM 실패 (Haversine 유지): {str(e)[:100]}")
        
        return matrix
    
    def _get_osrm_matrix(self, coordinates: List[List[float]], mode: str) -> np.ndarray:
        """Table API 우선 → Route API 병렬"""
        n = len(coordinates)
        osrm_mode = {'car': 'driving', 'bike': 'cycling'}.get(mode, mode)
        
        # Table API 우선 (n≤25, 가장 빠름)
        if n <= 25:
            try:
                matrix = self._table_api(coordinates, osrm_mode)
                success_rate = np.sum(matrix < 500000) / (n*n - n)
                if success_rate > 0.7:
                    logger.info(f"✅ Table API 성공: {success_rate*100:.0f}%")
                    return matrix
            except Exception as e:
                logger.debug(f"Table API 실패: {str(e)}")
        
        # Route API 병렬 fallback
        logger.info("🔄 Route API 병렬 계산")
        return self._route_api_parallel(coordinates, osrm_mode)
    
    def _table_api(self, coordinates: List[List[float]], mode: str) -> np.ndarray:
        """🗃️ OSRM Table API - [lat,lon] → lon,lat 문자열 변환"""
        # [[lat1,lon1], [lat2,lon2]] → "lon1,lat1;lon2,lat2"
        coords_str = ";".join(f"{lon},{lat}" for lat, lon in coordinates)
        url = f"{OSRM_URL}/table/v1/{mode}/{coords_str}?sources=all&destinations=all"
        
        resp = self.session.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        
        if data.get('code') != 'Ok':
            raise ValueError(f"Table API 실패: {data.get('code')} - {data}")
        
        matrix = np.array(data['durations'], dtype=float)
        np.fill_diagonal(matrix, 0)
        return matrix
    
    def _route_api_parallel(self, coordinates: List[List[float]], mode: str) -> np.ndarray:
        """⚡ 병렬 Route API - 최대 성능"""
        n = len(coordinates)
        matrix = np.full((n, n), 999999.0)
        np.fill_diagonal(matrix, 0)
        
        def get_route(i: int, j: int) -> float:
            """단일 경로 계산"""
            lat1, lon1 = coordinates[i]
            lat2, lon2 = coordinates[j]
            url = f"{OSRM_URL}/route/v1/{mode}/{lon1},{lat1};{lon2},{lat2}?overview=false&steps=false"
            
            try:
                resp = self.session.get(url, timeout=5)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get('code') == 'Ok' and data.get('routes'):
                        return float(data['routes'][0]['duration'])
            except:
                pass
            return 999999.0
        
        # 병렬 실행 (최대 12 스레드)
        with concurrent.futures.ThreadPoolExecutor(max_workers=12) as executor:
            futures = {
                executor.submit(get_route, i, j): (i, j)
                for i in range(n) for j in range(i+1, n)
            }
            
            for future in concurrent.futures.as_completed(futures):
                i, j = futures[future]
                try:
                    duration = future.result(timeout=2)
                    matrix[i][j] = matrix[j][i] = duration
                except:
                    pass
        
        return matrix

class ORToolsTSP:
    """⚡ OR-Tools TSP Solver - 완전 폴백"""
    
    @staticmethod
    def solve_tsp(distance_matrix: np.ndarray, time_limit: int = 90) -> List[int]:
        """TSP 최적화 + 2단계 폴백: OR-Tools → Nearest Neighbor"""
        n = distance_matrix.shape[0]
        if n < 2:
            return list(range(n))
        
        # 무한대 값 정리
        matrix = np.where(distance_matrix > 500000, 999999, distance_matrix)
        np.fill_diagonal(matrix, 0)
        
        try:
            route = ORToolsTSP._ortools_solve(matrix, time_limit)
            if len(route) == n and route[0] == 0:
                return route
        except Exception as e:
            logger.warning(f"❌ OR-Tools 실패 → NN 폴백: {str(e)[:50]}")
        
        # Nearest Neighbor 폴백
        return ORToolsTSP._nearest_neighbor(matrix)
    
    @staticmethod
    def _ortools_solve(matrix: np.ndarray, time_limit: int) -> List[int]:
        """OR-Tools 메인 솔버 (시작점 0 고정)"""
        n = matrix.shape[0]
        manager = pywrapcp.RoutingIndexManager(n, 1, 0)  # 1 vehicle, start at 0
        routing = pywrapcp.RoutingModel(manager)
        
        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return max(1, int(matrix[from_node, to_node]))
        
        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
        
        # 검색 파라미터 최적화
        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
        search_parameters.time_limit.FromSeconds(time_limit)
        search_parameters.log_search = True
        
        solution = routing.SolveWithParameters(search_parameters)
        if not solution:
            raise ValueError("OR-Tools 솔루션 생성 실패")
        
        # 경로 복원
        route = []
        index = routing.Start(0)
        while not routing.IsEnd(index):
            route.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))
        route.append(0)  # 시작점으로 복귀
        return route
    
    @staticmethod
    def _nearest_neighbor(matrix: np.ndarray) -> List[int]:
        """최적화된 Nearest Neighbor 휴리스틱"""
        n = matrix.shape[0]
        visited = [False] * n
        route = [0]  # 시작점 0
        visited[0] = True
        current = 0
        
        for _ in range(1, n):
            next_node, min_dist = -1, float('inf')
            for j in range(n):
                if not visited[j] and matrix[current][j] < min_dist:
                    min_dist = matrix[current][j]
                    next_node = j
            if next_node != -1:
                route.append(next_node)
                visited[next_node] = True
                current = next_node
        
        route.append(0)  # 시작점으로 복귀
        return route

class RouteOptimizationView(APIView):
    """🗺️ 팝업스토어 경로 최적화 API - 1~100개 완전 처리"""
    
    permission_classes = [AllowAny]
    
    @extend_schema(
        summary="팝업스토어 최적 방문 순서 계산",
        description="OSRM Table/Route 자동 폴백 + OR-Tools TSP + Haversine 완전 백업\n지원: 1~100개 지점, 도보/자전거/자동차",
        tags=['🗺️ Route Optimization'],
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'coordinates': {
                        'type': 'array',
                        'items': {
                            'type': 'array',
                            'items': {'type': 'number'},
                            'minItems': 2,
                            'maxItems': 2,
                            'description': '[위도, 경도]'
                        },
                        'minItems': 1,
                        'maxItems': 100,
                        'description': '[[lat1,lon1], [lat2,lon2], ...]'
                    },
                    'mode': {
                        'type': 'string',
                        'enum': ['foot', 'walking', 'car', 'driving', 'bike', 'cycling'],
                        'default': 'foot',
                        'description': '이동 수단'
                    },
                    'start_index': {
                        'type': 'integer',
                        'minimum': 0,
                        'description': '고정 출발 지점 인덱스 (기본값: 0)'
                    },
                    'time_limit': {
                        'type': 'integer',
                        'minimum': 10,
                        'maximum': 300,
                        'default': 90,
                        'description': 'OR-Tools 최적화 시간 제한(초)'
                    }
                }
            }
        },
        responses={
            200: OpenApiResponse(
                description='최적 경로 계산 완료',
                examples={
                    'success': {
                        'summary': '완료 예제',
                        'value': {
                            'success': True,
                            'n_locations': 3,
                            'route_indices': [0, 2, 1],
                            'route_coordinates': [[36.35, 127.38], [36.36, 127.39], [36.34, 127.37]],
                            'total_duration_minutes': 45.2,
                            'osrm_used': True,
                            'processing_time': 1.23
                        }
                    }
                }
            )
        }
    )
    
    def post(self, request):
        start_time = time.time()
        data = request.data
        
        # 입력 검증
        coordinates = data.get('coordinates', [])
        n = len(coordinates)
        
        if n < 1:
            return Response({'success': False, 'error': '최소 1개 좌표 필요'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        if n > 100:
            return Response({'success': False, 'error': '최대 100개 좌표만 지원'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # 좌표 형식 엄격 검증
        for i, coord in enumerate(coordinates):
            if (len(coord) != 2 or 
                not all(isinstance(x, (int, float)) for x in coord) or
                not (-90 <= coord[0] <= 90 and -180 <= coord[1] <= 180)):
                return Response({
                    'success': False,
                    'error': f'coordinates[{i}] 유효하지 않음: [lat(-90~90), lon(-180~180)] 필요'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        mode = data.get('mode', 'foot')
        start_index = data.get('start_index', 0) % n
        time_limit = data.get('time_limit', 90)
        
        logger.info(f"🗺️ 최적화 요청: {n}개 지점 ({mode}), 시작: {start_index}")
        
        try:
            # 1. 거리 매트릭스 계산 (OSRM + Haversine)
            calculator = OSRMDistanceCalculator()
            duration_matrix = calculator.get_duration_matrix(coordinates, mode)
            
            # 2. TSP 최적화 (OR-Tools + NN)
            tsp_solver = ORToolsTSP()
            route_indices = tsp_solver.solve_tsp(duration_matrix, time_limit)
            
            # 시작점 기준 재정렬
            start_pos = route_indices.index(start_index)
            route_indices = route_indices[start_pos:] + route_indices[:start_pos]
            
            # 3. 결과 계산
            route_coords = [coordinates[i] for i in route_indices]
            total_duration = sum(duration_matrix[route_indices[i]][route_indices[(i+1) % len(route_indices)]]
                               for i in range(len(route_indices)))
            
            # 4. 고속 캐싱 (좌표 해시 기반)
            coord_hash = hash(json.dumps(sorted(coordinates, key=lambda x: (x[0], x[1]))))
            cache_key = f"route_opt_{coord_hash}_{mode}_{start_index}"
            cache.set(cache_key, {
                'route_indices': route_indices,
                'total_duration': total_duration,
                'matrix_shape': duration_matrix.shape
            }, 1800)  # 30분 캐싱
            
            # 5. 상세 결과
            elapsed = time.time() - start_time
            result = {
                'success': True,
                'n_locations': n,
                'coordinates': coordinates,
                'route_indices': route_indices,
                'route_coordinates': route_coords,
                'total_duration': float(total_duration),
                'total_duration_minutes': round(total_duration / 60, 1),
                'total_duration_hours': round(total_duration / 3600, 2),
                'start_index': start_index,
                'mode': mode,
                'osrm_used': calculator.osrm_available,
                'processing_time': round(elapsed, 2),
                'status': '완료',
                'cache_key': cache_key,
                'estimated_quality': 'OSRM' if calculator.osrm_available else 'Haversine'
            }
            
            logger.info(f"✅ 최적화 완료: {n}개 → {result['total_duration_minutes']:.1f}분 "
                       f"({elapsed:.2f}s, OSRM:{calculator.osrm_available})")
            
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"❌ 경로 최적화 실패: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': '서버 내부 오류 - Haversine 폴백으로 재시도',
                'n_locations': n,
                'fallback': 'Haversine 사용'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)