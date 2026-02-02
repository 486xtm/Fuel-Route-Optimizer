"""
Script to reload fuel stations WITH geocoding.
This will clear the database and reload all stations with latitude/longitude.
"""
import os
import sys
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fuel_route_optimizer.settings')
django.setup()

from routes.models import FuelStation
from django.core.management import call_command

print("=" * 70)
print("Reload Fuel Stations WITH Geocoding")
print("=" * 70)
print()

# Check current status
current_count = FuelStation.objects.count()
geocoded_count = FuelStation.objects.filter(
    latitude__isnull=False,
    longitude__isnull=False
).count()

print(f"Current Status:")
print(f"  Total Stations: {current_count}")
print(f"  Geocoded: {geocoded_count}")
print(f"  Not Geocoded: {current_count - geocoded_count}")
print()

if current_count > 0:
    print("⚠️  This will DELETE all existing stations and reload with geocoding.")
    print()
    response = input("Continue? (yes/no): ")
    if response.lower() != 'yes':
        print("Aborted.")
        sys.exit(0)
    print()

print("=" * 70)
print("Starting reload with geocoding...")
print("=" * 70)
print()
print("⏱️  This will take 2-4 HOURS due to API rate limits.")
print("   - Nominatim API: 1 request per second")
print("   - 8,151 stations to geocode")
print("   - Estimated time: ~2.3 hours minimum")
print()
print("You can monitor progress in the output below.")
print("=" * 70)
print()

# Run the management command WITHOUT --skip-geocoding
try:
    call_command('load_fuel_prices')
    print()
    print("=" * 70)
    print("✅ Reload Complete!")
    print("=" * 70)
    print()
    
    # Check final status
    final_count = FuelStation.objects.count()
    final_geocoded = FuelStation.objects.filter(
        latitude__isnull=False,
        longitude__isnull=False
    ).count()
    
    print(f"Final Status:")
    print(f"  Total Stations: {final_count}")
    print(f"  Geocoded: {final_geocoded}")
    print(f"  Success Rate: {final_geocoded/final_count*100:.1f}%")
    print()
    
    if final_geocoded > 0:
        print("✅ Stations are now geocoded and ready to use!")
        print()
        print("You can now test the API with:")
        print('  curl -X POST http://127.0.0.1:8000/api/optimize-route/ \\')
        print('    -H "Content-Type: application/json" \\')
        print('    -d "{\\"start_location\\": \\"Los Angeles, CA\\", \\"end_location\\": \\"Kennesaw, GA\\", \\"initial_fuel_miles\\": 300}"')
    else:
        print("⚠️  No stations were geocoded. Check for errors above.")
    
except KeyboardInterrupt:
    print()
    print()
    print("=" * 70)
    print("⚠️  Interrupted by user")
    print("=" * 70)
    print()
    print("Partial data may have been loaded.")
    print("Run this script again to complete the reload.")
    sys.exit(1)
except Exception as e:
    print()
    print("=" * 70)
    print("❌ Error occurred")
    print("=" * 70)
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

