# ... (keep existing code and imports) ...
import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('FMP_API_KEY')
BASE_URL = 'https://financialmodelingprep.com/api/v3'

def get_stock_price(ticker):
    # ... (this function remains the same)
    url = f"{BASE_URL}/quote-short/{ticker.upper()}?apikey={API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data:
            return data[0].get('price', 0)
        return 0
    except requests.exceptions.RequestException as e:
        print(f"API Error fetching price for {ticker}: {e}")
        return 0

# --- ADD THIS NEW FUNCTION ---
def search_stock_tickers(query):
    """Searches for stock tickers matching the query from the API."""
    if not query:
        return []
    # This searches the API and prioritizes stocks from the NSE exchange
    url = f"{BASE_URL}/search?query={query}&limit=10&exchange=NSE&apikey={API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        # We only need the symbol and name for our recommendations
        results = [{'symbol': item.get('symbol'), 'name': item.get('name')} for item in data]
        return results
    except requests.exceptions.RequestException as e:
        print(f"API Error searching for tickers: {e}")
        return []
