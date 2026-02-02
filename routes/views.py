"""
API views for route optimization.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from routes.serializers import RouteRequestSerializer, RouteResponseSerializer
from routes.fuel_optimizer import FuelOptimizer
import hashlib


class OptimizeRouteView(APIView):
    """
    API endpoint to optimize a route with fuel stops.

    POST /api/optimize-route/

    Request body:
    {
        "start_location": "New York, NY",
        "end_location": "Los Angeles, CA",
        "initial_fuel_miles": 500  // Optional, default: 500, max: 500
    }

    Response:
    {
        "start_location": "New York, NY",
        "end_location": "Los Angeles, CA",
        "start_coords": {"lat": 40.7128, "lon": -74.0060},
        "end_coords": {"lat": 34.0522, "lon": -118.2437},
        "total_distance_miles": 2789.5,
        "total_duration_hours": 41.2,
        "route_geometry": [[lon, lat], ...],
        "fuel_stops": [
            {
                "sequence": 1,
                "station_name": "Example Truck Stop",
                "address": "123 Highway Rd",
                "city": "Pittsburgh",
                "state": "PA",
                "coordinates": {"lat": 40.4406, "lon": -79.9959},
                "price_per_gallon": 3.45,
                "gallons": 50.0,
                "cost": 172.50,
                "distance_from_start": 450.0
            },
            ...
        ],
        "total_fuel_gallons": 278.95,
        "total_fuel_cost": 962.53,
        "miles_per_gallon": 10,
        "max_range_miles": 500
    }
    """

    def post(self, request):
        """Handle POST request to optimize route."""
        # Validate request
        serializer = RouteRequestSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid request', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        start_location = serializer.validated_data['start_location']
        end_location = serializer.validated_data['end_location']
        initial_fuel_miles = serializer.validated_data.get('initial_fuel_miles', 500)

        # Check cache first (include initial_fuel_miles in cache key)
        cache_key = f"route_{hashlib.md5(f'{start_location}_{end_location}_{initial_fuel_miles}'.encode()).hexdigest()}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return Response(cached_result)

        try:
            # Optimize route with custom initial fuel
            optimizer = FuelOptimizer(initial_fuel_miles=initial_fuel_miles)

            result = optimizer.find_optimal_fuel_stops(start_location, end_location)

            # Validate response
            response_serializer = RouteResponseSerializer(data=result)
            if response_serializer.is_valid():
                # Cache the result for 1 hour
                cache.set(cache_key, response_serializer.data, timeout=3600)
                return Response(response_serializer.data)
            else:
                return Response(
                    {'error': 'Invalid response format', 'details': response_serializer.errors},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except ValueError as e:
            import traceback
            traceback.print_exc()
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response(
                {'error': 'An error occurred while optimizing the route', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

def index(request):
    """Render the frontend interface."""
    from django.shortcuts import render
    return render(request, 'index.html')
