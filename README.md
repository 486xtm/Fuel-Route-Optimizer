# Fuel Route Optimizer

A production-ready Django REST API with interactive web interface that calculates optimal fuel stops along routes within the USA. Built as a technical assessment demonstrating advanced algorithm design, API optimization, and full-stack development.

## 🎯 Project Overview

**Challenge**: Build a fuel route optimization system that:

- Accepts start/end locations within USA
- Returns route with optimal fuel stops based on cost-effectiveness
- Vehicle specs: 500-mile max range, 10 MPG fuel efficiency
- Uses provided CSV file with 8,151 fuel station prices
- Integrates a free map/routing API
- **Critical requirement**: "One call to the map/route API is ideal"
- Optimizes for quick API responses

**Solution Delivered**:

- ✅ Django 6.0.1 REST API with DRF 3.16.1
- ✅ Modern responsive web interface with dark/light mode
- ✅ Interactive Leaflet.js map with route visualization
- ✅ Smart Look-Ahead Greedy Algorithm
- ✅ **Exactly ONE routing API call per request** (ideal performance)
- ✅ Multi-level caching (geocoding: 24h, routes: 1h, results: 1h)
- ✅ Production-ready with comprehensive error handling

## 🏆 Key Achievements

### 1. Optimal API Call Efficiency ⚡

**Requirement**: "One call to the map/route API is ideal, two or three is acceptable"

**Our Solution**: **Exactly ONE routing API call per request** ✅

**How We Achieved This**:

1. Single call to OpenRouteService `/v2/directions/driving-car/geojson` endpoint
2. Returns route with ~2,000 coordinate points (geometry array)
3. All fuel stop searches use geometric distance calculations (geopy.geodesic)
4. No additional API calls for distance measurements
5. Database spatial queries with bounding box filtering

**Result**: Ideal performance with minimal external dependencies

### 2. Smart Look-Ahead Greedy Algorithm 🧠

**Challenge**: Minimize total fuel cost while maintaining realistic purchasing behavior

**Our Solution**: Intelligent algorithm that looks ahead for cheaper stations and buys only the minimum fuel needed

**Algorithm Features**:

- Configurable initial fuel amount (default 500 miles, range 1-500)
- Looks ahead within max range for cheaper stations
- Buys minimum fuel to reach cheaper stations (not filling up unnecessarily)
- At last stop: buys exact fuel needed for destination (no waste)

### 3. Modern Full-Stack Interface 🎨

**Frontend Features**:

- Responsive design with Tailwind CSS 3.0
- Dark/light mode toggle with localStorage persistence
- Interactive Leaflet.js map with route visualization
- Real-time fuel stop markers with detailed popups

## 🛠️ Tech Stack

**Backend**:

- Django 6.0.1 (Latest stable - January 2025)
- Django REST Framework 3.16.1
- SQLite database with spatial indexes
- Python 3.14+

**External APIs**:

- OpenRouteService API (Free routing with GeoJSON)
- Nominatim/Geopy (Free geocoding with rate limiting)

**Frontend**:

- Tailwind CSS 3.0 (Utility-first CSS framework)
- Leaflet.js (Interactive maps)

**Libraries**:

- geopy 2.4.1 (Geodesic distance calculations)
- requests 2.31.0 (HTTP client)

## 🧠 Algorithm Explanation

### Smart Look-Ahead Greedy Algorithm

The core optimization algorithm uses an intelligent greedy approach with look-ahead capability to minimize total fuel cost.

#### Algorithm Overview

```
Input: Route geometry, total distance, initial fuel amount
Output: List of optimal fuel stops with purchase amounts

1. Start with initial fuel (default 500 miles, configurable 1-500)
2. Find all candidate stations along route (within 10 miles)
3. For each position along route:
   a. If can reach destination with current fuel → DONE
   b. Find all reachable stations with current fuel
   c. Select cheapest reachable station
   d. Look ahead for cheaper stations within max range
   e. If cheaper station exists ahead:
      - Buy MINIMUM fuel needed to reach it
   f. Else (no cheaper station ahead):
      - Check distance to destination
      - If destination ≤ 500 miles: Buy EXACT fuel for destination
      - If destination > 500 miles: Fill up to max range (500 miles)
   g. Move to selected station, update fuel level
4. Return optimized fuel stop list
```

#### Key Algorithm Features

**1. Candidate Station Finding**

- Samples route geometry every 10th point (~200 checks for 2,000 points)
- Uses bounding box queries for efficient database filtering
- Finds stations within 10 miles of route
- Tracks unique stations to avoid duplicates
- Sorts by distance from start

**2. Smart Fuel Purchasing**

- **Look-Ahead**: Checks for cheaper stations within max range (500 miles)
- **Minimum Purchase**: Buys only fuel needed to reach cheaper station
- **Last Stop Optimization**: Buys exact fuel for destination (no waste)
- **Greedy Fallback**: Fills up if no cheaper station ahead

**3. Cost Optimization**

- Prioritizes cheapest stations among reachable options
- Avoids unnecessary fill-ups

#### Algorithm Complexity

- **Time Complexity**: O(n × m) where n = route points, m = stations per point
- **Space Complexity**: O(s) where s = total unique stations
- **Optimizations**:
  - Route sampling (every 10th point)
  - Bounding box queries (database indexes)
  - Early termination when destination reachable
  - Caching (geocoding, routes, results)

## 🚀 Setup Instructions

### Prerequisites

- Python 3.14+ installed
- pip package manager
- OpenRouteService API key (free)

### Installation Steps

1. **Navigate to project directory**

   ```bash
   cd Spotter
   ```

2. **Create virtual environment** (if not exists)

   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**

   Windows:

   ```bash
   venv\Scripts\activate
   ```

   macOS/Linux:

   ```bash
   source venv/bin/activate
   ```

4. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

   Or manually:

   ```bash
   pip install django==6.0.1 djangorestframework==3.16.1 requests==2.31.0 geopy==2.4.1
   ```

5. **Configure OpenRouteService API Key**
   - Sign up for free at: https://openrouteservice.org/dev/#/signup
   - Edit `fuel_route_optimizer/settings.py`:
     ```python
     OPENROUTESERVICE_API_KEY = 'your_actual_api_key_here'
     ```

6. **Run database migrations**

   ```bash
   python manage.py migrate
   ```

7. **Load fuel station data**

   ```bash
   python manage.py load_fuel_prices
   ```

   This loads 8,151 fuel stations from `fuel-prices-for-be-assessment.csv`

8. **(Optional) Geocode fuel stations**

   **Note**: Stations are loaded without coordinates initially. To enable full functionality:

   ```bash
   python reload_with_geocoding.py
   ```

   **Warning**: This takes 2-4 hours due to API rate limits (1 request/second for 8,151 stations)

### Running the Application

**Start the Django development server:**

Windows:

```bash
python manage.py runserver
```

macOS/Linux:

```bash
python manage.py runserver
```

**Access the application:**

- Web Interface: http://127.0.0.1:8000/
- API Endpoint: http://127.0.0.1:8000/api/optimize-route/

## 📡 API Documentation

### Endpoint: Optimize Route

**POST** `/api/optimize-route/`

Calculate optimal route with fuel stops between two US locations.

**Request Body:**

```json
{
  "start_location": "Los Angeles, CA",
  "end_location": "New York, NY",
  "initial_fuel_miles": 500
}
```

**Parameters:**

| Parameter            | Type    | Required | Default | Range | Description                             |
| -------------------- | ------- | -------- | ------- | ----- | --------------------------------------- |
| `start_location`     | string  | Yes      | -       | -     | Starting location (e.g., "Chicago, IL") |
| `end_location`       | string  | Yes      | -       | -     | Ending location (e.g., "Houston, TX")   |
| `initial_fuel_miles` | integer | No       | 500     | 1-500 | Initial fuel amount in miles            |

**Response:**

```json
{
  "start_location": "Los Angeles, CA",
  "end_location": "New York, NY",
  "start_coords": {
    "lat": 34.0522,
    "lon": -118.2437
  },
  "end_coords": {
    "lat": 40.7128,
    "lon": -74.0060
  },
  "total_distance_miles": 2789.5,
  "total_duration_hours": 41.2,
  "route_geometry": [
    [-118.2437, 34.0522],
    [-118.2440, 34.0525],
    ...
  ],
  "fuel_stops": [
    {
      "sequence": 1,
      "station_name": "Pilot Travel Center",
      "address": "I-40, EXIT 37",
      "city": "Barstow",
      "state": "CA",
      "coordinates": {
        "lat": 34.8958,
        "lon": -117.0228
      },
      "price_per_gallon": 3.45,
      "gallons": 45.0,
      "cost": 155.25,
      "distance_from_start": 450.0
    },
    {
      "sequence": 2,
      "station_name": "Love's Travel Stop",
      "address": "I-40, EXIT 139",
      "city": "Flagstaff",
      "state": "AZ",
      "coordinates": {
        "lat": 35.1983,
        "lon": -111.6513
      },
      "price_per_gallon": 3.38,
      "gallons": 50.0,
      "cost": 169.00,
      "distance_from_start": 900.0
    }
  ],
  "total_fuel_gallons": 278.95,
  "total_fuel_cost": 962.53,
  "miles_per_gallon": 10,
  "max_range_miles": 500
}
```
