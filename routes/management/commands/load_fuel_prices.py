import csv
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from routes.models import FuelStation
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time


class Command(BaseCommand):
    help = 'Load fuel prices from CSV file and geocode locations'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='fuel-prices-for-be-assessment.csv',
            help='Path to the CSV file with fuel prices'
        )
        parser.add_argument(
            '--skip-geocoding',
            action='store_true',
            help='Skip geocoding to speed up initial load'
        )

    def geocode_location(self, geolocator, address, city, state, retries=3):
        """Geocode a location with retry logic."""
        full_address = f"{address}, {city}, {state}, USA"
        
        for attempt in range(retries):
            try:
                location = geolocator.geocode(full_address, timeout=10)
                if location:
                    return location.latitude, location.longitude
                # Try with just city and state if full address fails
                location = geolocator.geocode(f"{city}, {state}, USA", timeout=10)
                if location:
                    return location.latitude, location.longitude
                return None, None
            except (GeocoderTimedOut, GeocoderServiceError) as e:
                if attempt < retries - 1:
                    time.sleep(1)
                    continue
                self.stdout.write(
                    self.style.WARNING(f"Geocoding failed for {city}, {state}: {str(e)}")
                )
                return None, None
        return None, None

    def handle(self, *args, **options):
        file_path = options['file']
        skip_geocoding = options['skip_geocoding']
        
        self.stdout.write(self.style.SUCCESS(f'Loading fuel prices from {file_path}...'))
        
        # Initialize geocoder
        geolocator = None
        if not skip_geocoding:
            geolocator = Nominatim(user_agent="fuel_route_optimizer")
        
        # Clear existing data
        FuelStation.objects.all().delete()
        
        stations_to_create = []
        geocoded_count = 0
        
        with open(file_path, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            for idx, row in enumerate(reader, 1):
                try:
                    # Parse the CSV row
                    station = FuelStation(
                        opis_truckstop_id=int(row['OPIS Truckstop ID']),
                        name=row['Truckstop Name'].strip(),
                        address=row['Address'].strip(),
                        city=row['City'].strip(),
                        state=row['State'].strip(),
                        rack_id=int(row['Rack ID']),
                        retail_price=Decimal(row['Retail Price'])
                    )
                    
                    # Geocode if not skipped
                    if geolocator and not skip_geocoding:
                        lat, lon = self.geocode_location(
                            geolocator, 
                            station.address, 
                            station.city, 
                            station.state
                        )
                        if lat and lon:
                            station.latitude = Decimal(str(lat))
                            station.longitude = Decimal(str(lon))
                            geocoded_count += 1
                        
                        # Rate limiting for Nominatim (1 request per second)
                        time.sleep(1.1)
                    
                    stations_to_create.append(station)
                    
                    if idx % 100 == 0:
                        self.stdout.write(f'Processed {idx} stations...')
                
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error processing row {idx}: {str(e)}')
                    )
                    continue
        
        # Bulk create all stations
        with transaction.atomic():
            FuelStation.objects.bulk_create(stations_to_create, batch_size=500)
        
        total_count = len(stations_to_create)
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully loaded {total_count} fuel stations'
            )
        )
        if not skip_geocoding:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Geocoded {geocoded_count} out of {total_count} stations'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    'Geocoding was skipped. Run without --skip-geocoding to add coordinates.'
                )
            )

