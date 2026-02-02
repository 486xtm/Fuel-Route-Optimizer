"""
Fuel stop optimization algorithm.
Finds optimal fuel stops along a route based on:
- 500-mile maximum range
- Cost-effective fuel prices
- Proximity to the route

OPTIMIZED FOR MINIMAL API CALLS:
- Makes only ONE routing API call (for the main route)
- All fuel stop searches use geometric distance calculations
- No additional API calls for distance measurements
- Uses database spatial indexes for efficient filtering
"""
from geopy.distance import geodesic
from routes.models import FuelStation
from routes.routing_service import RoutingService


class FuelOptimizer:
    """Optimizer for finding cost-effective fuel stops along a route."""

    MAX_RANGE_MILES = 500
    MILES_PER_GALLON = 10
    MAX_DETOUR_MILES = 10  # Maximum miles off route to consider a station (reduced for accuracy)
    INITIAL_FUEL_MILES = 500  # Default initial fuel amount in miles

    def __init__(self, initial_fuel_miles=None):
        self.routing_service = RoutingService()
        self.initial_fuel_miles = initial_fuel_miles or self.INITIAL_FUEL_MILES
    
    def find_optimal_fuel_stops(self, start_location, end_location):
        """
        Find optimal fuel stops between start and end locations.

        Args:
            start_location: string (e.g., "New York, NY")
            end_location: string (e.g., "Los Angeles, CA")

        Returns:
            dict with route info, fuel stops, and total cost
        """
        # Geocode start and end locations
        start_coords = self.routing_service.geocode_location(start_location)
        end_coords = self.routing_service.geocode_location(end_location)

        if not start_coords or not end_coords:
            raise ValueError("Could not geocode start or end location")

        # Get the route
        route = self.routing_service.get_route(start_coords, end_coords)
        total_distance = route['distance']

        # Calculate fuel stops needed
        fuel_stops = self._calculate_fuel_stops(
            start_coords,
            end_coords,
            route['geometry'],
            total_distance
        )

        # Calculate total fuel cost
        total_fuel_needed = total_distance / self.MILES_PER_GALLON
        total_cost = sum(stop['cost'] for stop in fuel_stops)

        return {
            'start_location': start_location,
            'end_location': end_location,
            'start_coords': {'lat': start_coords[0], 'lon': start_coords[1]},
            'end_coords': {'lat': end_coords[0], 'lon': end_coords[1]},
            'total_distance_miles': round(total_distance, 2),
            'total_duration_hours': round(route['duration'] / 3600, 2),
            'route_geometry': route['geometry'],
            'fuel_stops': fuel_stops,
            'total_fuel_gallons': round(total_fuel_needed, 2),
            'total_fuel_cost': round(total_cost, 2),
            'miles_per_gallon': self.MILES_PER_GALLON,
            'max_range_miles': self.MAX_RANGE_MILES
        }
    
    def _calculate_fuel_stops(self, start_coords, end_coords, route_geometry, total_distance):
        """
        Calculate optimal fuel stops using smart look-ahead greedy algorithm.

        Algorithm:
        1. Start with initial fuel amount (default 500 miles)
        2. Look ahead for cheaper stations within current fuel range
        3. If cheaper station found: buy only minimum fuel needed to reach it
        4. If no cheaper station: fill up to max range and pick cheapest available
        5. Repeat until destination is reached

        Uses ONLY geometric calculations - NO additional API calls.
        """
        fuel_stops = []

        # If distance is less than initial fuel, no stops needed
        if total_distance <= self.initial_fuel_miles:
            return fuel_stops

        # Find all candidate stations along the route
        candidate_stations = self._find_all_candidate_stations(route_geometry, total_distance)

        if not candidate_stations:
            # No stations found - may indicate stations not geocoded or route in remote area
            return []

        # Smart look-ahead greedy algorithm
        current_distance = 0
        current_fuel = self.initial_fuel_miles
        sequence = 1

        while current_distance < total_distance:
            remaining_distance = total_distance - current_distance

            # If we can reach the destination with current fuel, we're done
            if current_fuel >= remaining_distance:
                break

            # Find all stations reachable with current fuel
            reachable_stations = [
                s for s in candidate_stations
                if current_distance < s['distance_from_start'] <= current_distance + current_fuel
            ]

            if not reachable_stations:
                # No stations reachable - this shouldn't happen with proper data
                break

            # Look for the cheapest station among reachable ones
            current_station = min(reachable_stations, key=lambda s: float(s['station'].retail_price))
            current_price = float(current_station['station'].retail_price)

            # Look ahead: find cheaper stations beyond current station
            distance_to_current = current_station['distance_from_start'] - current_distance
            fuel_after_current = current_fuel - distance_to_current

            # Find stations reachable from current station (within max range)
            stations_ahead = [
                s for s in candidate_stations
                if current_station['distance_from_start'] < s['distance_from_start']
                <= current_station['distance_from_start'] + self.MAX_RANGE_MILES
            ]

            # Find cheaper stations ahead
            cheaper_ahead = [
                s for s in stations_ahead
                if float(s['station'].retail_price) < current_price
            ]

            if cheaper_ahead:
                # Found cheaper station ahead - buy only minimum fuel needed
                cheapest_ahead = min(cheaper_ahead, key=lambda s: float(s['station'].retail_price))
                distance_to_cheaper = cheapest_ahead['distance_from_start'] - current_station['distance_from_start']

                # Calculate fuel needed to reach the cheaper station
                fuel_needed = distance_to_cheaper - fuel_after_current

                if fuel_needed > 0:
                    gallons_to_buy = fuel_needed / self.MILES_PER_GALLON

                    fuel_stops.append({
                        'sequence': sequence,
                        'station_name': current_station['station'].truckstop_name,
                        'address': current_station['station'].address,
                        'city': current_station['station'].city,
                        'state': current_station['station'].state,
                        'coordinates': {
                            'lat': float(current_station['station'].latitude) if current_station['station'].latitude else None,
                            'lon': float(current_station['station'].longitude) if current_station['station'].longitude else None
                        },
                        'price_per_gallon': current_price,
                        'gallons': round(gallons_to_buy, 2),
                        'cost': round(current_price * gallons_to_buy, 2),
                        'distance_from_start': round(current_station['distance_from_start'], 2)
                    })

                    sequence += 1
                    current_fuel = fuel_after_current + fuel_needed
                else:
                    # We already have enough fuel to reach cheaper station
                    current_fuel = fuel_after_current
            else:
                # No cheaper station ahead
                # Calculate distance from current station to destination
                distance_to_destination = total_distance - current_station['distance_from_start']

                # Determine how much fuel to buy
                if distance_to_destination <= self.MAX_RANGE_MILES:
                    # Destination is within max range - buy only what's needed to reach it
                    fuel_needed_for_destination = distance_to_destination - fuel_after_current

                    if fuel_needed_for_destination > 0:
                        gallons_to_buy = fuel_needed_for_destination / self.MILES_PER_GALLON

                        fuel_stops.append({
                            'sequence': sequence,
                            'station_name': current_station['station'].truckstop_name,
                            'address': current_station['station'].address,
                            'city': current_station['station'].city,
                            'state': current_station['station'].state,
                            'coordinates': {
                                'lat': float(current_station['station'].latitude) if current_station['station'].latitude else None,
                                'lon': float(current_station['station'].longitude) if current_station['station'].longitude else None
                            },
                            'price_per_gallon': current_price,
                            'gallons': round(gallons_to_buy, 2),
                            'cost': round(current_price * gallons_to_buy, 2),
                            'distance_from_start': round(current_station['distance_from_start'], 2)
                        })

                        sequence += 1
                        current_fuel = fuel_after_current + fuel_needed_for_destination
                    else:
                        # We already have enough fuel to reach destination
                        current_fuel = fuel_after_current
                else:
                    # Destination is beyond max range - fill up to max range
                    fuel_to_add = self.MAX_RANGE_MILES - fuel_after_current

                    if fuel_to_add > 0:
                        gallons_to_buy = fuel_to_add / self.MILES_PER_GALLON

                        fuel_stops.append({
                            'sequence': sequence,
                            'station_name': current_station['station'].truckstop_name,
                            'address': current_station['station'].address,
                            'city': current_station['station'].city,
                            'state': current_station['station'].state,
                            'coordinates': {
                                'lat': float(current_station['station'].latitude) if current_station['station'].latitude else None,
                                'lon': float(current_station['station'].longitude) if current_station['station'].longitude else None
                            },
                            'price_per_gallon': current_price,
                            'gallons': round(gallons_to_buy, 2),
                            'cost': round(current_price * gallons_to_buy, 2),
                            'distance_from_start': round(current_station['distance_from_start'], 2)
                        })

                        sequence += 1
                        current_fuel = self.MAX_RANGE_MILES
                    else:
                        current_fuel = fuel_after_current

            # Move to current station
            current_distance = current_station['distance_from_start']

        return fuel_stops

    def _find_all_candidate_stations(self, route_geometry, total_distance):
        """
        Find all stations along the route by checking near every geometry point.
        For each point in the route, find stations within MAX_DETOUR_MILES.
        If no station found near a point, skip it.
        Returns list of unique stations with their distance from start.
        """
        if not route_geometry or len(route_geometry) < 2:
            return []

        candidates_dict = {}  # Use dict to avoid duplicates: {station_id: station_info}

        # Calculate cumulative distances along the route
        cumulative_distances = [0]
        for i in range(1, len(route_geometry)):
            prev_point = (route_geometry[i-1][1], route_geometry[i-1][0])  # (lat, lon)
            curr_point = (route_geometry[i][1], route_geometry[i][0])
            segment_distance = geodesic(prev_point, curr_point).miles
            cumulative_distances.append(cumulative_distances[-1] + segment_distance)

        # Check every point in the route geometry
        # For ~2000 points, sample every 10th point for performance (~200 checks)
        sample_rate = max(1, len(route_geometry) // 200)

        for i in range(0, len(route_geometry), sample_rate):
            point = route_geometry[i]
            coords = (point[1], point[0])  # Convert [lon, lat] to (lat, lon)
            distance_from_start = cumulative_distances[i]

            # Find stations within MAX_DETOUR_MILES of this point
            nearby_stations = self._find_stations_near_point(coords)

            # If no stations found near this point, skip it
            if not nearby_stations:
                continue

            # Add stations to candidates
            for station in nearby_stations:
                # Calculate actual distance from station to this route point
                station_coords = (float(station.latitude), float(station.longitude))
                distance_to_point = geodesic(coords, station_coords).miles

                # Only include if within MAX_DETOUR_MILES
                if distance_to_point <= self.MAX_DETOUR_MILES:
                    # Track each station with its closest point to the route
                    if station.id not in candidates_dict:
                        candidates_dict[station.id] = {
                            'station': station,
                            'distance_from_start': distance_from_start,
                            'distance_to_route': distance_to_point
                        }
                    else:
                        # If we found this station before, keep the one with shorter detour
                        if distance_to_point < candidates_dict[station.id]['distance_to_route']:
                            candidates_dict[station.id] = {
                                'station': station,
                                'distance_from_start': distance_from_start,
                                'distance_to_route': distance_to_point
                            }

        # Convert dict to list
        candidates = list(candidates_dict.values())

        # Sort by distance from start
        candidates.sort(key=lambda x: x['distance_from_start'])
        return candidates

    def _find_stations_near_point(self, coords):
        """
        Find stations within MAX_DETOUR_MILES of a single point.
        Uses bounding box for efficient database query.

        Args:
            coords: tuple of (latitude, longitude)

        Returns:
            QuerySet of FuelStation objects
        """
        if not coords:
            return []

        lat, lon = coords

        # Create bounding box (approximate degrees for MAX_DETOUR_MILES)
        # 1 degree latitude ≈ 69 miles
        # 1 degree longitude ≈ 55 miles (varies by latitude)
        lat_delta = self.MAX_DETOUR_MILES / 69.0
        lon_delta = self.MAX_DETOUR_MILES / 55.0

        # Query stations within bounding box
        stations = FuelStation.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False,
            latitude__gte=lat - lat_delta,
            latitude__lte=lat + lat_delta,
            longitude__gte=lon - lon_delta,
            longitude__lte=lon + lon_delta
        ).order_by('retail_price')[:50]  # Get top 50 cheapest in this area

        return stations

