import requests
import pandas as pd
import io

def get_nifty500_tickers() -> list[str]:
    """
    Fetches the latest Nifty 500 tickers from NSE indices CSV.
    """
    url = "https://archives.nseindia.com/content/indices/ind_nifty500list.csv"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        df = pd.read_csv(io.StringIO(response.text))
        return df['Symbol'].tolist()
    except Exception as e:
        print(f"Error fetching Nifty 500 tickers: {e}")
        return []
