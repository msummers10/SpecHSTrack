import requests
from bs4 import BeautifulSoup
import json
import os
import re
import time
from datetime import datetime
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

# --- CONFIGURATION ---
URL = "https://community.spectrum.net/discussion/177269/high-split-what-is-it-and-when-is-our-network-evolution-coming-to-you"
DATA_DIR = "data"
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
CACHE_FILE = os.path.join(DATA_DIR, "geo_cache.json")

# Define our categories
# "BLUE" group
BLUE_HEADERS = ["completed", "not yet enabled", "live"]
# "YELLOW" group
YELLOW_HEADERS = ["pending", "2025", "2026", "future"]

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return {} if "cache" in filepath else []

def save_json(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def get_coordinates(city_state, cache):
    if city_state in cache:
        return cache[city_state]
    
    geolocator = Nominatim(user_agent="spectrum_high_split_mapper_v2")
    try:
        print(f"Geocoding: {city_state}...")
        location = geolocator.geocode(city_state + ", USA")
        time.sleep(1.2) 
        if location:
            coords = {"lat": location.latitude, "lon": location.longitude}
            cache[city_state] = coords
            return coords
    except Exception as e:
        print(f"Error geocoding {city_state}: {e}")
    return None

def scrape_forum():
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(URL, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    content_div = soup.find("div", class_="Message")
    if not content_div:
        return []

    # Get all text as a list of strings to preserve order
    lines = content_div.stripped_strings
    
    cities = []
    seen = set()
    current_status = "Unknown" # Default
    
    # Regex for "City, ST"
    city_pattern = r"([A-Z][a-zA-Z\s\.]+),\s([A-Z]{2})"

    for line in lines:
        line_lower = line.lower()
        
        # 1. Check if this line is a Header
        # We check Yellow headers first, then Blue
        found_header = False
        for h in YELLOW_HEADERS:
            if h in line_lower and len(line) < 50: # Length check prevents false positives in long sentences
                current_status = "yellow"
                found_header = True
                break
        
        if not found_header:
            for h in BLUE_HEADERS:
                if h in line_lower and len(line) < 50:
                    current_status = "blue"
                    break

        # 2. Check if this line contains a City
        matches = re.findall(city_pattern, line)
        for city, state in matches:
            full_name = f"{city.strip()}, {state}"
            
            # Save only if unique and valid length
            if len(city) < 30 and full_name not in seen:
                cities.append({
                    "name": full_name,
                    "status_color": current_status 
                })
                seen.add(full_name)

    return cities

def main():
    if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
    
    history = load_json(HISTORY_FILE)
    geo_cache = load_json(CACHE_FILE)
    
    scraped_items = scrape_forum()
    today = datetime.now().strftime("%Y-%m-%d")
    
    todays_data = []
    
    for item in scraped_items:
        coords = get_coordinates(item['name'], geo_cache)
        if coords:
            todays_data.append({
                "city": item['name'],
                "lat": coords['lat'],
                "lon": coords['lon'],
                "color": item['status_color'] # Save the color categorization
            })
    
    save_json(CACHE_FILE, geo_cache)

    snapshot = {
        "date": today,
        "cities": todays_data
    }
    
    history.append(snapshot)
    save_json(HISTORY_FILE, history)
    print(f"Success. Scraped {len(todays_data)} cities.")

if __name__ == "__main__":
    main()