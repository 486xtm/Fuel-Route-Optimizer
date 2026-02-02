"""
Routing service using OpenRouteService API.
Free tier: 2000 requests/day, 40 requests/minute
Sign up at: https://openrouteservice.org/dev/#/signup
"""
import requests
from django.conf import settings
from django.core.cache import cache
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import hashlib
import json


class RoutingService:
    """Service for calculating routes and geocoding locations."""
    
    BASE_URL = "https://api.openrouteservice.org/v2"
    
    def __init__(self):
        self.api_key = settings.OPENROUTESERVICE_API_KEY
        self.geolocator = Nominatim(user_agent="fuel_route_optimizer")
    
    def geocode_location(self, location_string):
        """
        Geocode a location string to coordinates.
        Returns: (latitude, longitude) or None if not found
        """
        # Check cache first
        cache_key = f"geocode_{hashlib.md5(location_string.encode()).hexdigest()}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            location = self.geolocator.geocode(location_string + ", USA", timeout=10)
            if location:
                result = (location.latitude, location.longitude)
                cache.set(cache_key, result, timeout=86400)  # Cache for 24 hours
                return result
        except Exception as e:
            print(f"Geocoding error: {str(e)}")
        
        return None
    
    def get_route(self, start_coords, end_coords):
        """
        Get route between two coordinates using OpenRouteService.

        Args:
            start_coords: tuple of (latitude, longitude)
            end_coords: tuple of (latitude, longitude)

        Returns:
            dict with 'distance' (in miles), 'duration' (in seconds),
            'geometry' (list of [lon, lat] coordinates)
        """
        # Create cache key (use hash to avoid special characters)
        cache_key = f"route_{hashlib.md5(f'{start_coords}_{end_coords}'.encode()).hexdigest()}"
        cached_route = cache.get(cache_key)
        if cached_route:
            return cached_route
        
        # OpenRouteService expects [longitude, latitude] format
        coordinates = [
            [start_coords[1], start_coords[0]],  # start: [lon, lat]
            [end_coords[1], end_coords[0]]        # end: [lon, lat]
        ]
        
        headers = {
            'Authorization': self.api_key,
            'Content-Type': 'application/json'
        }
        
        body = {
            'coordinates': coordinates,
            'instructions': False,
            'preference': 'recommended',
            'geometry_simplify': False,
            'continue_straight': False
        }
        
        try:
            response = requests.post(
                f"{self.BASE_URL}/directions/driving-car/geojson",  # Request GeoJSON format
                json=body,
                headers=headers,
                timeout=10
            )

            # Check if response is successful
            if response.status_code != 200:
                print(f"Routing API error: Status {response.status_code}, Response: {response.text}")
                return self._calculate_fallback_route(start_coords, end_coords)

            data = response.json()

            # Check if the response has the expected structure (GeoJSON format)
            if 'features' not in data or len(data['features']) == 0:
                print(f"Routing API error: No features in response. Response: {data}")
                return self._calculate_fallback_route(start_coords, end_coords)

            feature = data['features'][0]
            properties = feature['properties']
            geometry = feature['geometry']

            # Convert meters to miles
            distance_miles = properties['summary']['distance'] / 1609.34

            result = {
                'distance': distance_miles,
                'duration': properties['summary']['duration'],
                'geometry': geometry['coordinates']  # List of [lon, lat] from GeoJSON
            }

            # Cache the result
            cache.set(cache_key, result, timeout=3600)  # Cache for 1 hour

            return result

        except (requests.exceptions.RequestException, KeyError, ValueError, TypeError) as e:
            print(f"Routing API error: {str(e)}")
            import traceback
            traceback.print_exc()
            # Fallback to straight-line distance if API fails
            return self._calculate_fallback_route(start_coords, end_coords)
    
    def _calculate_fallback_route(self, start_coords, end_coords):
        """
        Calculate a simple straight-line route as fallback.
        This is used when the routing API is unavailable.
        """
        distance_miles = geodesic(start_coords, end_coords).miles
        
        # Estimate duration assuming 60 mph average
        duration_seconds = (distance_miles / 60) * 3600
        
        return {
            'distance': distance_miles,
            'duration': duration_seconds,
            'geometry': [
                [start_coords[1], start_coords[0]],  # [lon, lat]
                [end_coords[1], end_coords[0]]
            ]
        }
    
    def calculate_distance(self, coord1, coord2):
        """
        Calculate distance between two coordinates in miles.
        
        Args:
            coord1: tuple of (latitude, longitude)
            coord2: tuple of (latitude, longitude)
        
        Returns:
            float: distance in miles
        """
        return geodesic(coord1, coord2).miles

