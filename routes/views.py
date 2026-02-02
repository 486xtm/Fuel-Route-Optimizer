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

    def get_client_ip(self, request):
        """Get the client's IP address from the request."""
        import requests

        # First try to get IP from headers (for production behind proxy)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
            # If it's not localhost, return it
            if ip not in ['127.0.0.1', 'localhost', '::1']:
                return ip

        # Try REMOTE_ADDR
        remote_addr = request.META.get('REMOTE_ADDR')
        if remote_addr and remote_addr not in ['127.0.0.1', 'localhost', '::1']:
            return remote_addr

        # If we're running locally (127.0.0.1), get the real public IP
        try:
            response = requests.get('https://api.ipify.org?format=json', timeout=2)
            if response.status_code == 200:
                public_ip = response.json().get('ip')
                if public_ip:
                    return public_ip
        except Exception as e:
            print(f"Could not fetch public IP: {e}")

        # Fallback to whatever we have
        return remote_addr or '127.0.0.1'

    def get_ip_location(self, ip_address):
        """Get location information for an IP address."""
        import requests

        # Skip for localhost
        if ip_address in ['127.0.0.1', 'localhost', '::1']:
            return None, None, None

        try:
            # Use ip-api.com (free, no API key required, 45 requests/minute)
            response = requests.get(f'http://ip-api.com/json/{ip_address}', timeout=2)
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return data.get('city'), data.get('regionName'), data.get('country')
        except Exception as e:
            print(f"Could not fetch IP location: {e}")

        return None, None, None

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

        # Log IP address with geolocation
        from routes.models import IPLog
        ip_address = self.get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')

        # Get IP location
        ip_city, ip_region, ip_country = self.get_ip_location(ip_address)

        IPLog.objects.create(
            ip_address=ip_address,
            start_location=start_location,
            end_location=end_location,
            user_agent=user_agent,
            ip_city=ip_city,
            ip_region=ip_region,
            ip_country=ip_country
        )

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

class IPLogView(APIView):
    """
    API endpoint to retrieve IP logs.

    GET /api/ip-logs/

    Response:
    {
        "logs": [
            {
                "ip_address": "192.168.1.1",
                "timestamp": "2026-02-02T10:30:45Z",
                "start_location": "Los Angeles, CA",
                "end_location": "New York, NY",
                "user_agent": "Mozilla/5.0..."
            },
            ...
        ],
        "total_count": 150
    }
    """

    def get(self, request):
        """Handle GET request to retrieve IP logs."""
        from routes.models import IPLog

        # Get query parameters
        limit = request.GET.get('limit', 100)
        try:
            limit = int(limit)
            if limit > 1000:
                limit = 1000
        except ValueError:
            limit = 100

        # Get logs
        logs = IPLog.objects.all()[:limit]
        total_count = IPLog.objects.count()

        # Serialize logs
        logs_data = [
            {
                'ip_address': log.ip_address,
                'timestamp': log.timestamp.isoformat(),
                'start_location': log.start_location,
                'end_location': log.end_location,
                'user_agent': log.user_agent,
                'ip_city': log.ip_city,
                'ip_region': log.ip_region,
                'ip_country': log.ip_country
            }
            for log in logs
        ]

        return Response({
            'logs': logs_data,
            'total_count': total_count
        })


def index(request):
    """Render the frontend interface."""
    from django.shortcuts import render
    return render(request, 'index.html')


def ip_logs_page(request):
    """Render the IP logs page."""
    from django.shortcuts import render
    return render(request, 'ip_logs.html')
