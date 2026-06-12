import os
import requests
import yfinance as yf

# --- API Key for Searching ---
ALPHA_VANTAGE_API_KEY = os.getenv('ALPHA_VANTAGE_API_KEY')

# --- Price Fetching (using yfinance) ---
def get_stock_price(ticker):
    """Fetches the current price of a stock using yfinance."""
    try:
        stock = yf.Ticker(ticker)
        history = stock.history(period="5d")
        if not history.empty:
            return round(float(history['Close'].iloc[-1]), 2)
        
        info = stock.info
        price = info.get('regularMarketPrice') or info.get('currentPrice') or info.get('previousClose')
        if price:
            return round(float(price), 2)
        return 0
    except Exception as e:
        print(f"yfinance error for {ticker}: {e}")
        return 0

# --- Ticker Search (using Alpha Vantage with Translation) ---
def search_stock_tickers(query):
    """Searches for stock tickers using Alpha Vantage and translates them for yfinance."""
    if not query or not ALPHA_VANTAGE_API_KEY:
        return []
    
    params = {
        "function": "SYMBOL_SEARCH",
        "keywords": query,
        "apikey": ALPHA_VANTAGE_API_KEY
    }
    
    try:
        response = requests.get('https://www.alphavantage.co/query', params=params)
        response.raise_for_status()
        data = response.json()
        
        matches = data.get('bestMatches', [])
        
        # --- THIS IS THE FIX ---
        # Translate the symbols before sending them to the frontend.
        translated_results = []
        for item in matches:
            original_symbol = item.get('1. symbol', '')
            
            # Translate from Alpha Vantage format to yfinance format
            yfinance_symbol = original_symbol.replace('.BSE', '.BO').replace('.NSE', '.NS')
            
            translated_results.append({
                'symbol': yfinance_symbol, 
                'name': item.get('2. name')
            })

        # Prioritize Indian and US markets in search results
        final_results = [
            stock for stock in translated_results if ".BO" in stock['symbol'] 
                                                   or ".NS" in stock['symbol'] 
                                                   or "." not in stock['symbol']
        ]
        return final_results[:10] # Return top 10 relevant results
    
    except Exception as e:
        print(f"Alpha Vantage search error: {e}")
        return []