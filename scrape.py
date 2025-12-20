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

# --- SETUP ---
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, 'r') as f:
            return json.load(f)
    return {} if "cache" in filepath else []

def save_json(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=2)

def get_coordinates(city_state, cache):
    # Check cache first
    if city_state in cache:
        return cache[city_state]
    
    # If not in cache, ask Nominatim (OpenStreetMap)
    geolocator = Nominatim(user_agent="spectrum_high_split_mapper_v1")
    try:
        print(f"Geocoding: {city_state}...")
        location = geolocator.geocode(city_state + ", USA")
        time.sleep(1.5) # Pause to be polite to the API
        
        if location:
            coords = {"lat": location.latitude, "lon": location.longitude}
            cache[city_state] = coords
            return coords
    except Exception as e:
        print(f"Error geocoding {city_state}: {e}")
    
    return None

def scrape_forum():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    response = requests.get(URL, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find the main post. Spectrum uses Vanilla Forums.
    # We look for the user content div.
    content_div = soup.find("div", class_="Message")
    if not content_div:
        print("Could not find the main post content.")
        return []

    text_content = content_div.get_text("\n")

    # Regex to find "City Name, ST"
    # Matches: Capital letter word, optional extra words, comma, 2 capital letters
    pattern = r"([A-Z][a-zA-Z\s\.]+),\s([A-Z]{2})"
    matches = re.findall(pattern, text_content)

    cities = []
    seen = set()

    for city, state in matches:
        full_name = f"{city.strip()}, {state}"
        # Filter out junk matches (e.g., long sentences that accidentally match)
        if len(city) < 30 and full_name not in seen:
            cities.append(full_name)
            seen.add(full_name)
    
    return cities

def main():
    history = load_json(HISTORY_FILE)
    geo_cache = load_json(CACHE_FILE)
    
    found_cities = scrape_forum()
    today = datetime.now().strftime("%Y-%m-%d")
    
    todays_data = []
    
    for city_name in found_cities:
        coords = get_coordinates(city_name, geo_cache)
        if coords:
            todays_data.append({
                "city": city_name,
                "lat": coords['lat'],
                "lon": coords['lon']
            })
    
    # Save the updated cache immediately
    save_json(CACHE_FILE, geo_cache)

    # Add to history
    # Only add if it's different from the last entry or if history is empty
    snapshot = {
        "date": today,
        "cities": todays_data
    }
    
    history.append(snapshot)
    save_json(HISTORY_FILE, history)
    print(f"Success. Scraped {len(todays_data)} cities.")

if __name__ == "__main__":
    main()