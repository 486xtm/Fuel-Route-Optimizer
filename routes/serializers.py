"""
Serializers for the routes API.
"""
from rest_framework import serializers


class RouteRequestSerializer(serializers.Serializer):
    """Serializer for route optimization request."""

    start_location = serializers.CharField(
        max_length=255,
        help_text="Starting location (e.g., 'New York, NY' or 'Los Angeles, CA')"
    )
    end_location = serializers.CharField(
        max_length=255,
        help_text="Ending location (e.g., 'Miami, FL' or 'Seattle, WA')"
    )
    initial_fuel_miles = serializers.IntegerField(
        required=False,
        default=500,
        min_value=1,
        max_value=500,
        help_text="Initial fuel amount in miles (default: 500, max: 500)"
    )


class CoordinatesSerializer(serializers.Serializer):
    """Serializer for geographic coordinates."""
    
    lat = serializers.FloatField()
    lon = serializers.FloatField()


class FuelStopSerializer(serializers.Serializer):
    """Serializer for a fuel stop."""
    
    sequence = serializers.IntegerField()
    station_name = serializers.CharField()
    address = serializers.CharField()
    city = serializers.CharField()
    state = serializers.CharField()
    coordinates = CoordinatesSerializer()
    price_per_gallon = serializers.FloatField()
    gallons = serializers.FloatField()
    cost = serializers.FloatField()
    distance_from_start = serializers.FloatField()


class RouteResponseSerializer(serializers.Serializer):
    """Serializer for route optimization response."""

    start_location = serializers.CharField()
    end_location = serializers.CharField()
    start_coords = CoordinatesSerializer()
    end_coords = CoordinatesSerializer()
    total_distance_miles = serializers.FloatField()
    total_duration_hours = serializers.FloatField()
    route_geometry = serializers.ListField(
        child=serializers.ListField(child=serializers.FloatField())
    )
    fuel_stops = FuelStopSerializer(many=True)
    total_fuel_gallons = serializers.FloatField()
    total_fuel_cost = serializers.FloatField()
    miles_per_gallon = serializers.IntegerField()
    max_range_miles = serializers.IntegerField()

