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
    """⚡ OR-Tools 안정 Cycle TSP → Path 변환"""

    @staticmethod
    def solve_path(
        distance_matrix: np.ndarray,
        start_index: int = 0,
        time_limit: int = 90
    ) -> List[int]:

        n = distance_matrix.shape[0]
        if n <= 1:
            return list(range(n))

        # 소규모는 NN이 더 안정 + 빠름
        if n <= 2:
            return ORToolsTSP._nearest_neighbor_path(distance_matrix, start_index)

        try:
            return ORToolsTSP._ortools_cycle_to_path(
                distance_matrix,
                start_index,
                time_limit
            )
        except Exception as e:
            logger.warning(f"❌ OR-Tools 실패 → NN 폴백: {str(e)[:60]}")
            return ORToolsTSP._nearest_neighbor_path(distance_matrix, start_index)

    @staticmethod
    def _ortools_cycle_to_path(
        matrix: np.ndarray,
        start_index: int,
        time_limit: int
    ) -> List[int]:

        n = matrix.shape[0]

        manager = pywrapcp.RoutingIndexManager(n, 1, start_index)
        routing = pywrapcp.RoutingModel(manager)

        def distance_callback(from_index, to_index):
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return max(1, int(matrix[from_node][to_node]))

        transit_callback_index = routing.RegisterTransitCallback(distance_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = (
            routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        )
        search_parameters.local_search_metaheuristic = (
            routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH
        )
        search_parameters.time_limit.FromSeconds(time_limit)

        solution = routing.SolveWithParameters(search_parameters)
        if not solution:
            raise ValueError("OR-Tools 솔루션 없음")

        # cycle route 추출
        route = []
        index = routing.Start(0)
        while not routing.IsEnd(index):
            route.append(manager.IndexToNode(index))
            index = solution.Value(routing.NextVar(index))

        # cycle → path (start_index 기준으로 절단)
        if route[0] == start_index:
            return route

        idx = route.index(start_index)
        return route[idx:] + route[:idx]

    @staticmethod
    def _nearest_neighbor_path(matrix: np.ndarray, start: int) -> List[int]:
        n = matrix.shape[0]
        visited = [False] * n
        route = [start]
        visited[start] = True
        current = start

        for _ in range(n - 1):
            next_node, min_dist = -1, float('inf')
            for j in range(n):
                if not visited[j] and matrix[current][j] < min_dist:
                    min_dist = matrix[current][j]
                    next_node = j
            if next_node == -1:
                break
            route.append(next_node)
            visited[next_node] = True
            current = next_node

        return route

class RouteOptimizationView(APIView):
    """🗺️ 팝업스토어 경로 최적화 API - 역 자동선택 + 1~100개 완전 처리"""
    
    permission_classes = [AllowAny]

    STATIONS = {
        'tukseom': [37.5330, 127.0700],    # 뚝섬역 2호선
        'seongsu': [37.5445, 127.0467],    # 성수역 2호선  
        'konkuk': [37.5397, 127.0708],     # 건대입구역 2호선
        'daejeon': [36.3504, 127.3845],    # 대전역 (기본값)
    }

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine 직선거리 계산 (초 단위)"""
        if lat1 == lat2 and lon1 == lon2:
            return 0.0
        
        R = 6371.0  # 지구 반경(km)
        WALKING_SPEED = 4.8  # km/h
        
        lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(radians, [lat1, lon1, lat2, lon2])
        dlat, dlon = lat2_rad - lat1_rad, lon2_rad - lon1_rad
        
        a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        distance_km = R * c
        
        return (distance_km / WALKING_SPEED) * 3600  # 초 단위

    def _select_station_by_popup_density(self, coordinates: List[List[float]]) -> tuple:
        """📍 팝업스토어 중심점 기준 가장 가까운 역 자동 선택"""
        if len(coordinates) < 2:
            return 'daejeon', self.STATIONS['daejeon'], 0.0
        
        # 팝업 중심점(centroid) 계산
        center_lat = sum(coord[0] for coord in coordinates) / len(coordinates)
        center_lon = sum(coord[1] for coord in coordinates) / len(coordinates)
        popup_center = [center_lat, center_lon]
        
        # 각 역과의 도보시간 계산
        distances = []
        for station_name, station_coord in self.STATIONS.items():
            duration = self._haversine_distance(
                popup_center[0], popup_center[1], 
                station_coord[0], station_coord[1]
            )
            distances.append((station_name, station_coord, duration))
        
        # 가장 가까운 역 선택
        nearest_station, station_coords, distance = min(distances, key=lambda x: x[2])
        logger.info(f"🚉 팝업중심({popup_center[0]:.4f},{popup_center[1]:.4f}) → {nearest_station}")
        return nearest_station, station_coords, distance

    def _sort_by_proximity(self, coordinates: List[List[float]], reference_point: List[float]) -> List[int]:
        """🔍 기준점 기준 거리순 정렬 (인덱스 반환)"""
        distances = []
        for i, (lat, lon) in enumerate(coordinates):
            duration = self._haversine_distance(
                reference_point[0], reference_point[1], lat, lon
            )
            distances.append((i, duration))
        
        distances.sort(key=lambda x: x[1])
        return [idx for idx, _ in distances]
    
    def _split_by_station_distance(
        self,
        coordinates: List[List[float]],
        station_coords: List[float],
        threshold_minutes: float = 15.0
    ) -> tuple[list[int], list[int]]:
        """
        역 기준 도보 거리로 near / far 분리
        """
        near, far = [], []

        for i, (lat, lon) in enumerate(coordinates):
            duration_sec = self._haversine_distance(
                station_coords[0], station_coords[1], lat, lon
            )
            duration_min = duration_sec / 60

            if duration_min <= threshold_minutes:
                near.append(i)
            else:
                far.append(i)

        return near, far

    @extend_schema(
        summary="팝업스토어 최적 방문 순서 계산 (역 자동선택)",
        description="팝업 위치 기반 자동 역선택 + OSRM + OR-Tools TSP",
        tags=['🗺️ Route Optimization'],
        request={'application/json': {
            'type': 'object',
            'properties': {
                'coordinates': {
                    'type': 'array',
                    'items': {'type': 'array', 'items': {'type': 'number'}},
                    'minItems': 1, 'maxItems': 100,
                    'description': '[[lat1,lon1], [lat2,lon2], ...]'
                },
                'mode': {'type': 'string', 'enum': ['foot', 'car', 'bike'], 'default': 'foot'},
                'start_index': {'type': 'integer', 'minimum': 0},
                'time_limit': {'type': 'integer', 'minimum': 10, 'maximum': 300, 'default': 90}
            }
        }},
        responses={200: OpenApiResponse(description='최적 경로 + 추천역 정보')}
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
        
        # 좌표 형식 검증
        for i, coord in enumerate(coordinates):
            if (len(coord) != 2 or 
                not all(isinstance(x, (int, float)) for x in coord) or
                not (-90 <= coord[0] <= 90 and -180 <= coord[1] <= 180)):
                return Response({
                    'success': False,
                    'error': f'coordinates[{i}] 유효하지 않음'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        mode = data.get('mode', 'foot')
        start_index = data.get('start_index', 0) % n
        time_limit = data.get('time_limit', 90)
        
        logger.info(f"🗺️ 최적화 요청: {n}개 지점 ({mode})")
        
        try:
            # 1. 팝업 위치 기반 자동 역 선택
            station_name, station_coords, station_distance = self._select_station_by_popup_density(coordinates)
            
            # 2. 거리 매트릭스 계산 (기존 OSRM)
            calculator = OSRMDistanceCalculator()
            duration_matrix = calculator.get_duration_matrix(coordinates, mode)
            
            # 3️. 역 기준 near / far 분리
            near, far = self._split_by_station_distance(
                coordinates,
                station_coords,
                threshold_minutes=15.0
            )

            logger.info(f"📍 역 기준 분리: near={len(near)}, far={len(far)}")

            route_indices = []

            # 4. near 먼저 TSP
            if near:
                near_matrix = duration_matrix[np.ix_(near, near)]

                # 시작점이 near에 있으면 그걸로, 아니면 near[0]
                near_start = near.index(start_index) if start_index in near else 0

                near_route = ORToolsTSP.solve_path(
                    near_matrix,
                    start_index=near_start,
                    time_limit=time_limit
                )

                route_indices.extend([near[i] for i in near_route])

            # 5️. far 나중에 TSP
            if far:
                far_matrix = duration_matrix[np.ix_(far, far)]

                far_route = ORToolsTSP.solve_path(
                    far_matrix,
                    start_index=0,
                    time_limit=time_limit
                )

                route_indices.extend([far[i] for i in far_route])

            # 6. 경로 좌표
            route_coords = [coordinates[i] for i in route_indices]

            # 7. 총 소요시간 (편도)
            total_duration = 0.0
            for i in range(len(route_indices) - 1):
                a, b = route_indices[i], route_indices[i + 1]
                total_duration += duration_matrix[a][b]
            
            # 8. 캐싱
            coord_hash = hash(json.dumps(sorted(coordinates, key=lambda x: (x[0], x[1]))))
            cache_key = f"route_opt_{coord_hash}_{mode}_{station_name}"
            cache.set(cache_key, {
                'route_indices': route_indices,
                'total_duration': total_duration,
                'station': station_name
            }, 1800)
            
            # 9. 응답
            elapsed = time.time() - start_time
            popup_center = [sum(c[0] for c in coordinates)/n, sum(c[1] for c in coordinates)/n]
            
            result = {
                'success': True,
                'n_locations': n,
                'coordinates': coordinates,
                'route_indices': route_indices,
                'route_coordinates': route_coords,
                'total_duration': float(total_duration),
                'total_duration_minutes': round(total_duration / 60, 1),
                'start_index': start_index,
                'mode': mode,
                'osrm_used': calculator.osrm_available,
                'processing_time': round(elapsed, 2),
                
                # 🚉 역 정보
                'auto_selected_station': station_name,
                'station_coordinates': station_coords,
                'station_to_popup_center_minutes': round(station_distance / 60, 1),
                'popup_center': popup_center,
            }
            
            logger.info(f"✅ 완료: {n}개 → {result['total_duration_minutes']:.1f}분 ({station_name}역)")
            return Response(result, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"❌ 경로 최적화 실패: {str(e)}", exc_info=True)
            return Response({
                'success': False,
                'error': str(e),
                'n_locations': n
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
