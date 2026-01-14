import os, json, logging, environ
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


class HaversineCalculator:
    """Haversine 거리 계산기 (미터 단위)"""
    @staticmethod
    def distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        R = 6371.0
        lat1_rad, lon1_rad, lat2_rad, lon2_rad = map(radians, [lat1, lon1, lat2, lon2])
        dlat, dlon = lat2_rad - lat1_rad, lon2_rad - lon1_rad
        a = sin(dlat/2)**2 + cos(lat1_rad) * cos(lat2_rad) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c * 1000


class ORToolsTSP:
    """OR-Tools Open TSP Solver - 30개 지원"""
    @staticmethod
    def solve_tsp(distance_matrix: np.ndarray, time_limit: int = 600) -> List[int]:  # 시간 ↑
        n = distance_matrix.shape[0]
        
        if n < 2:
            return list(range(n))
        if n == 2:
            return [0, 1]
        
        if np.any(distance_matrix < 0) or np.any(~np.isfinite(distance_matrix)):
            logger.error("Invalid distance matrix")
            return list(range(n))
        
        try:
            manager = pywrapcp.RoutingIndexManager(n, 1, 0)
            routing = pywrapcp.RoutingModel(manager)
            
            def distance_callback(from_index, to_index):
                from_node = manager.IndexToNode(from_index)
                to_node = manager.IndexToNode(to_index)
                return int(distance_matrix[from_node, to_node])
            
            transit_callback_index = routing.RegisterTransitCallback(distance_callback)
            routing.SetArcCostEvaluatorOfAllVehicles(transit_callback_index)
            
            search_parameters = pywrapcp.DefaultRoutingSearchParameters()
            search_parameters.first_solution_strategy = (
                routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC)
            search_parameters.local_search_metaheuristic = (
                routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH)
            search_parameters.time_limit.FromSeconds(time_limit)  # 10분
            
            solution = routing.SolveWithParameters(search_parameters)
            
            if solution:
                route = []
                index = routing.Start(0)
                while not routing.IsEnd(index):
                    route.append(manager.IndexToNode(index))
                    index = solution.Value(routing.NextVar(index))
                return route
            return ORToolsTSP._nearest_neighbor(distance_matrix)
            
        except Exception as e:
            logger.error(f"OR-Tools 크래시: {str(e)}, 최근접 이웃으로 폴백")
            return ORToolsTSP._nearest_neighbor(distance_matrix)
    
    @staticmethod
    def _nearest_neighbor(distance_matrix: np.ndarray) -> List[int]:
        n = distance_matrix.shape[0]
        visited = [False] * n
        route = [0]
        visited[0] = True
        
        current = 0
        for _ in range(1, n):
            next_node = -1
            min_dist = float('inf')
            for j in range(n):
                if not visited[j] and distance_matrix[current][j] < min_dist:
                    min_dist = distance_matrix[current][j]
                    next_node = j
            if next_node != -1:
                route.append(next_node)
                visited[next_node] = True
                current = next_node
        
        logger.info("TSP 폴백: 최근접 이웃 사용")
        return route


class CoordinatesRouteAPIView(APIView):
    permission_classes = [AllowAny]
    http_method_names = ['post']
    
    @extend_schema(
        request={
            'application/json': {
                'type': 'object',
                'properties': {
                    'coordinates': {
                        'type': 'array',
                        'description': '[[lat, lon], ...] 배열 (2-30개)',  # ✅ 변경
                        'items': {
                            'type': 'array',
                            'items': {'type': 'number'},
                            'minItems': 2,
                            'maxItems': 2
                        },
                        'minItems': 2,      # ✅ 변경
                        'maxItems': 30       # ✅ 변경
                    },
                    'user_id': {'type': 'integer', 'description': 'Optional'},
                    'walking_mode': {'type': 'boolean', 'default': True}
                },
                'required': ['coordinates']
            }
        },
        responses={
            200: OpenApiResponse(description='좌표 최적화 경로 (DB 저장됨)'),
            400: OpenApiResponse(description='유효하지 않은 입력')
        }
    )
    def post(self, request):
        # 1. 입력 검증: 2~30개 ✅ 변경
        coordinates = request.data.get('coordinates', [])
        if (not isinstance(coordinates, list) or 
            len(coordinates) < 2 or len(coordinates) > 30 or  # ✅ 30개로 확장
            not all(isinstance(coord, list) and len(coord) == 2 and 
                   all(isinstance(c, (int, float)) for c in coord) for coord in coordinates)):
            return Response(
                {"error": "coordinates는 2-30개의 [[lat, lon], ...] 배열이어야 합니다"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 좌표 검증
        validated_coordinates = []
        for i, coord in enumerate(coordinates):
            try:
                lat, lon = float(coord[0]), float(coord[1])
                if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                    return Response(
                        {"error": f"coordinates[{i}] 범위 오류: lat(-90~90), lon(-180~180)"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                validated_coordinates.append([lat, lon])
            except (ValueError, IndexError):
                return Response(
                    {"error": f"coordinates[{i}] 형식 오류"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # 2. 해시키 생성
        coord_tuples = tuple(tuple(c) for c in validated_coordinates)
        hash_key = hash(coord_tuples) % (10**18)
        hash_key_str = f"{hash_key:019d}"[:64]
        
        # 3. 기존 Route 체크
        existing_route = Route.objects.filter(hash_key=hash_key_str).first()
        if existing_route:
            logger.info(f"DB HIT: Route {existing_route.id}")
            return Response(self._serialize_route(existing_route))
        
        # 4. TSP 계산 (30개 지원)
        distance_matrix = self._calculate_distance_matrix(validated_coordinates)
        optimal_order = ORToolsTSP.solve_tsp(distance_matrix, time_limit=600)  # 10분
        
        # 5. GIS 객체 생성
        optimized_coords = [validated_coordinates[i] for i in optimal_order]
        line_coords = [(lon, lat) for lat, lon in optimized_coords]
        line_string = LineString(line_coords, srid=4326)
        original_points = [Point(lon, lat, srid=4326) for lat, lon in validated_coordinates]
        
        # 6. 거리/시간 계산
        total_distance_m = sum(
            distance_matrix[optimal_order[i]][optimal_order[i+1]]
            for i in range(len(optimal_order)-1)
        )
        total_distance_km = total_distance_m / 1000
        
        walking_mode = request.data.get('walking_mode', True)
        speed_kmh = 4.5 if walking_mode else 40.0
        duration_minutes = (total_distance_km / speed_kmh) * 60
        
        # 7. DB 저장
        route = Route.objects.create(
            user_id=request.data.get('user_id'),
            points=line_string,
            original_coordinates=original_points,
            total_distance=total_distance_km,
            duration=duration_minutes,
            optimal_order=optimal_order,
            locations_count=len(validated_coordinates),
            walking_mode=walking_mode,
            hash_key=hash_key_str
        )
        
        logger.info(f"✅ Route #{route.id}: {len(validated_coordinates)}개 → {total_distance_m:.0f}m")
        
        # 8. 캐시
        cache_key = f"route:{hash_key_str}"
        cache_result = self._serialize_route(route)
        cache.set(cache_key, cache_result, 24 * 60 * 60)
        
        return Response(cache_result)
    
    def _serialize_route(self, route: Route) -> dict:
        return {
            "id": route.id,
            "order": route.optimal_order,
            "coordinates": [[p.y, p.x] for p in route.original_coordinates],
            "optimized_coordinates": [
                [route.original_coordinates[i].y, route.original_coordinates[i].x] 
                for i in route.optimal_order
            ],
            "total_distance": round(route.total_distance * 1000, 1),
            "total_distance_km": round(route.total_distance, 3),
            "duration": round(route.duration, 1),
            "places_count": route.locations_count,
            "walking_mode": route.walking_mode
        }
    
    def _calculate_distance_matrix(self, coordinates: List[List[float]]) -> np.ndarray:
        n = len(coordinates)
        matrix = np.zeros((n, n))
        for i in range(n):
            for j in range(n):
                if i != j:
                    lat1, lon1 = coordinates[i]
                    lat2, lon2 = coordinates[j]
                    matrix[i][j] = HaversineCalculator.distance(lat1, lon1, lat2, lon2)
        return matrix