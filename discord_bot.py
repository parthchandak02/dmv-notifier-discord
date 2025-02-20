# discord_bot.py
import os
import requests
import time
import asyncio
from datetime import datetime
from typing import Optional, List, Dict
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import random
import json
import urllib.parse

# Load environment variables
load_dotenv()

# Configuration
NUMBER_OF_FEW_DATES = 1
FIND_DATES_BEFORE = datetime.strptime(os.getenv("FIND_DATES_BEFORE", "2025-02-27"), "%Y-%m-%d")
DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
if not DISCORD_WEBHOOK_URL:
    raise ValueError("DISCORD_WEBHOOK_URL environment variable is required")

# Interval to check for new dates (in seconds)
LOOKUP_INTERVAL_SEC = int(os.getenv("LOOKUP_INTERVAL_SEC", "600"))  # Default 10 minutes

# Configure retry strategy
retry_strategy = Retry(
    total=3,  # number of retries
    backoff_factor=1,  # wait 1, 2, 4 seconds between retries
    status_forcelist=[429, 500, 502, 503, 504],  # HTTP status codes to retry on
)
adapter = HTTPAdapter(max_retries=retry_strategy)
http = requests.Session()
http.mount("https://", adapter)
http.mount("http://", adapter)

# Base URL for DMV API
DMV_APPOINTMENT_API_ENDPOINT = "https://www.dmv.ca.gov/portal/wp-json/dmv/v1/appointment/branches"

# Branch codes with required special characters
branch_codes = {
    "redwood_city": "548!c6a4228d96cbe545c591e4257d1c035da72cbe10671d502597460e5f0730",
    "san_mateo": "593!fabfb52efab03764853fcdefa999d2a0be739510bec5207f4b82d5fb16e0",
}

# Query parameters with required special characters
dates_querystring = {
    "services[]": "DT!1857a62125c4425a24d85aceac6726cb8df3687d47b03b692e27bd8d17814",
    "numberOfCustomers": "1"
}

# State tracking
last_updated_timestamp = None
current_latest_dates: Dict[str, List[datetime]] = {}
error_counts: Dict[str, int] = {}
last_request_time: Dict[str, float] = {}

def format_date(date: datetime) -> str:
    """Format date in a human-readable format."""
    return date.strftime("%A, %B %d, %Y")

def send_discord_message(content: str) -> bool:
    """Send a message to Discord via webhook."""
    try:
        data = {
            "content": content,
            "username": "DMV Bot",
            "avatar_url": "https://www.dmv.ca.gov/portal/wp-content/uploads/2020/02/DMV_DataPortal.png"
        }

        response = http.post(DISCORD_WEBHOOK_URL, json=data, timeout=10)
        response.raise_for_status()

        # Handle rate limiting
        if response.status_code == 429:
            retry_after = float(response.headers.get('Retry-After', 1))
            print(f"Rate limited by Discord. Waiting {retry_after} seconds...")
            time.sleep(retry_after)
            return send_discord_message(content)

        return True
    except Exception as e:
        print(f"Error sending Discord message: {e}")
        return False

def should_make_request(city: str) -> bool:
    """Determine if we should make a request based on error history and timing."""
    current_time = time.time()

    # If this is the first request for this city
    if city not in last_request_time:
        last_request_time[city] = current_time
        error_counts[city] = 0
        return True

    # Calculate time since last request
    time_since_last_request = current_time - last_request_time[city]

    # If we've had errors, implement exponential backoff
    if error_counts.get(city, 0) > 0:
        required_wait = min(300 * (2 ** (error_counts[city] - 1)), 3600)  # Max 1 hour wait
        if time_since_last_request < required_wait:
            print(f"Waiting {required_wait - time_since_last_request:.0f} more seconds before retrying {city}...")
            return False

    # Add random jitter to prevent synchronized requests
    elif time_since_last_request < LOOKUP_INTERVAL_SEC + random.randint(1, 30):
        return False

    return True

async def get_available_dates(city: str) -> Optional[List[datetime]]:
    """Get available appointment dates for a DMV location."""
    if not should_make_request(city):
        return None

    try:
        print(f"Making request for {city}...")

        # Add headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.dmv.ca.gov/portal/appointments/book-appointment/',
            'Origin': 'https://www.dmv.ca.gov',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache'
        }

        # First, verify the branch exists
        response = http.get(
            DMV_APPOINTMENT_API_ENDPOINT,
            headers=headers,
            timeout=60
        )
        response.raise_for_status()

        # Properly encode the branch code and service ID
        branch_code = urllib.parse.quote(branch_codes[city], safe='')
        service_id = urllib.parse.quote(dates_querystring["services[]"], safe='')

        # Get dates for the specific branch
        dates_url = f"{DMV_APPOINTMENT_API_ENDPOINT}/{branch_code}/dates"
        params = {
            "services[]": service_id,
            "numberOfCustomers": "1"
        }

        response = http.get(
            dates_url,
            params=params,
            headers=headers,
            timeout=60
        )
        response.raise_for_status()

        dates_str = response.json()

        if not dates_str:
            print(f"No dates returned for {city}")
            return None

        # Parse dates
        dates = [datetime.strptime(date_str, "%Y-%m-%d") for date_str in dates_str]
        dates.sort()

        # Update tracking variables on success
        last_request_time[city] = time.time()
        error_counts[city] = 0

        return dates

    except Exception as e:
        error_counts[city] = error_counts.get(city, 0) + 1
        print(f"Error requesting dates for {city} (attempt {error_counts[city]}): {str(e)}")
        return None

async def check_and_notify(report_only_changes: bool = True) -> None:
    """Check for available dates and send notifications."""
    global last_updated_timestamp

    for city in branch_codes.keys():
        dates = await get_available_dates(city)

        if not dates:
            continue

        earliest_date = dates[0]

        # Skip if date is after our target date
        if earliest_date > FIND_DATES_BEFORE:
            continue

        # Format dates for notification
        formatted_dates = [format_date(date) for date in dates[:NUMBER_OF_FEW_DATES]]

        # Check if this is a new or changed date
        is_new_date = (
            city not in current_latest_dates or
            not current_latest_dates[city] or
            earliest_date < current_latest_dates[city][0]
        )

        if is_new_date or not report_only_changes:
            emoji = "🚨" if is_new_date else "📅"
            message = (
                f"{emoji} **DMV Appointment Available!**\n"
                f"Location: {city.replace('_', ' ').title()}\n"
                f"Date{'s' if len(formatted_dates) > 1 else ''}: {', '.join(formatted_dates)}\n"
                f"Book here: https://www.dmv.ca.gov/portal/appointments/book-appointment/"
            )

            if send_discord_message(message):
                current_latest_dates[city] = dates
                last_updated_timestamp = datetime.now()

async def main():
    """Main function to run the DMV appointment checker."""
    print(f"Starting DMV appointment checker. Will check every {LOOKUP_INTERVAL_SEC} seconds.")
    print("Notifications will be sent via Discord")
    print(f"Looking for appointments before: {format_date(FIND_DATES_BEFORE)}")

    # Send initial status message
    send_discord_message("🚗 DMV Appointment Bot is now running!\nI will notify you when I find earlier appointment dates.")

    # Initial check for all dates
    await check_and_notify(report_only_changes=False)

    while True:
        try:
            await check_and_notify()
            await asyncio.sleep(LOOKUP_INTERVAL_SEC)
        except Exception as e:
            print(f"Error in main loop: {e}")
            error_msg = f"⚠️ **Error in DMV Bot:**\n```\n{str(e)}\n```"
            send_discord_message(error_msg)
            await asyncio.sleep(60)  # Wait a minute before retrying

if __name__ == "__main__":
    asyncio.run(main())
