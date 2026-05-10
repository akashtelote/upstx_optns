import os
import json
import io
import datetime
import requests
import logging
import pandas as pd
import yfinance as yf
from filelock import FileLock, Timeout
from core.loader import get_nifty500_tickers

logger = logging.getLogger(__name__)

# Optional imports for fallback mechanisms
try:
    from jugaad_data.nse import bulk_deals, block_deals
except ImportError:
    bulk_deals, block_deals = None, None

try:
    from fake_useragent import UserAgent
except ImportError:
    UserAgent = None

class SmartMoneyFilter:
    """
    Tracks institutional activity using NSE Bulk and Block deals.
    Implements a fallback mechanism for data fetching and calculates
    a 'Whale Score' based on institutional net buying.
    """

    INSTITUTIONAL_KEYWORDS = [
        'FUND', 'CAPITAL', 'BANK', 'ADVISORS', 'INSURANCE',
        'ASSET', 'INVESTMENT', 'PENSION'
    ]

    def __init__(self, metadata_path: str = "data/equity_metadata.json"):
        self.metadata_path = metadata_path
        self.metadata_lock = FileLock(f"{self.metadata_path}.lock", timeout=5)
        self.metadata = {}
        self._cached_deals = None

        self.headers = {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

        if UserAgent:
            self.headers['User-Agent'] = UserAgent().random
        else:
            self.headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

        self._ensure_metadata_cache()

    def _get_last_trading_day(self) -> datetime.date:
        """Returns the last trading day (excluding weekends)."""
        today = datetime.datetime.now().date()
        if today.weekday() == 0:  # Monday -> Friday
            return today - datetime.timedelta(days=3)
        elif today.weekday() == 6: # Sunday -> Friday
            return today - datetime.timedelta(days=2)
        elif today.weekday() == 5: # Saturday -> Friday
            return today - datetime.timedelta(days=1)
        else:
            return today - datetime.timedelta(days=1)

    def _ensure_metadata_cache(self):
        """
        Ensures the metadata cache exists and is fresh.
        Refreshes if older than 7 days or if today is Sunday.
        """
        needs_refresh = True
        today = datetime.datetime.now()

        try:
            with self.metadata_lock:
                if os.path.exists(self.metadata_path):
                    file_mtime = datetime.datetime.fromtimestamp(os.path.getmtime(self.metadata_path))
                    age_days = (today - file_mtime).days

                    # Check refresh conditions
                    if age_days < 7 and today.weekday() != 6: # 6 is Sunday
                        needs_refresh = False
                        with open(self.metadata_path, 'r') as f:
                            try:
                                self.metadata = json.load(f)
                            except json.JSONDecodeError:
                                needs_refresh = True

                if needs_refresh:
                    self._refresh_metadata()
        except Timeout:
            logger.warning("Metadata cache is locked. Could not acquire lock within timeout.")
            if not self.metadata:
                logger.info("Attempting read-only fallback since metadata is empty.")
                if os.path.exists(self.metadata_path):
                    try:
                        with open(self.metadata_path, 'r') as f:
                            self.metadata = json.load(f)
                    except Exception as e:
                        logger.error(f"Read-only fallback failed: {e}")

    def _refresh_metadata(self):
        """Fetches Nifty 500 metadata from yfinance and caches it."""
        logger.info("Refreshing equity metadata cache...")
        tickers = get_nifty500_tickers()

        if not tickers:
            logger.error("Failed to fetch Nifty 500 tickers for metadata refresh.")
            return

        # Add .NS suffix for yfinance
        yf_tickers = [f"{t}.NS" for t in tickers]

        try:
            # Batch download info (this can be slow for 500 tickers, we fetch sharesOutstanding)
            # A more robust way is fetching info individually or using yf.Tickers
            tickers_obj = yf.Tickers(' '.join(yf_tickers))

            new_metadata = {}
            for t_symbol in yf_tickers:
                try:
                    info = tickers_obj.tickers[t_symbol].info
                    shares = info.get('sharesOutstanding')
                    if shares:
                        # Store without .NS
                        base_symbol = t_symbol.replace('.NS', '')
                        new_metadata[base_symbol] = {'sharesOutstanding': shares}
                except Exception as e:
                    # Ignore individual ticker errors to keep the process going
                    pass

            if new_metadata:
                self.metadata = new_metadata
                os.makedirs(os.path.dirname(self.metadata_path), exist_ok=True)
                with open(self.metadata_path, 'w') as f:
                    json.dump(new_metadata, f, indent=4)
                logger.info(f"Successfully refreshed metadata for {len(new_metadata)} tickers.")
            else:
                logger.warning("Failed to refresh any ticker metadata.")

        except Exception as e:
            logger.error(f"Error refreshing metadata: {e}")

    def _fetch_deals_jugaad(self, date_obj: datetime.date) -> pd.DataFrame:
        """Attempt to fetch deals using jugaad-data."""
        if bulk_deals is None or block_deals is None:
            # Although imported, it's missing from the init in some versions, but we still attempt
            return pd.DataFrame()

        dfs = []
        try:
            bulk = bulk_deals(date_obj, date_obj)
            if bulk:
                dfs.append(pd.DataFrame(bulk))
        except Exception as e:
            logger.warning(f"jugaad bulk fetch failed: {e}")

        try:
            block = block_deals(date_obj, date_obj)
            if block:
                dfs.append(pd.DataFrame(block))
        except Exception as e:
            logger.warning(f"jugaad block fetch failed: {e}")

        if dfs:
            return pd.concat(dfs, ignore_index=True)
        return pd.DataFrame()

    def _fetch_deals_http(self) -> pd.DataFrame:
        """Attempt to fetch deals using direct HTTP requests to NSE archives."""
        url_bulk = "https://nsearchives.nseindia.com/content/equities/bulk.csv"
        url_block = "https://nsearchives.nseindia.com/content/equities/block.csv"

        dfs = []
        session = requests.Session()

        # Hit main page first to get cookies/session
        try:
            session.get("https://www.nseindia.com", headers=self.headers, timeout=10)
        except:
            pass

        for url in [url_bulk, url_block]:
            try:
                response = session.get(url, headers=self.headers, timeout=10)
                if response.status_code == 200:
                    df = pd.read_csv(io.StringIO(response.text))
                    dfs.append(df)
                else:
                    raise Exception(f"HTTP Status {response.status_code}")
            except Exception as e:
                logger.warning(f"HTTP fetch failed for {url}: {e}")
                raise

        if dfs:
            return pd.concat(dfs, ignore_index=True)
        return pd.DataFrame()

    def _fetch_deals_playwright(self) -> pd.DataFrame:
        """Attempt to fetch deals using Playwright."""
        import subprocess

        script = """
import asyncio
from playwright.async_api import async_playwright
import pandas as pd

async def fetch():
    urls = [
        "https://nsearchives.nseindia.com/content/equities/bulk.csv",
        "https://nsearchives.nseindia.com/content/equities/block.csv"
    ]
    dfs = []
    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
            accept_downloads=True
        )
        page = await context.new_page()

        for url in urls:
            try:
                async with page.expect_download(timeout=15000) as download_info:
                    try:
                        await page.goto(url, timeout=15000)
                    except Exception as e:
                        if "Download is starting" not in str(e):
                            raise e

                download = await download_info.value
                path = await download.path()
                df = pd.read_csv(path)
                dfs.append(df)
            except Exception as e:
                pass
        await browser.close()

    for df in dfs:
        print("---CSV_START---")
        print(df.to_csv(index=False))
        print("---CSV_END---")

asyncio.run(fetch())
"""
        try:
            result = subprocess.run(['python', '-c', script], capture_output=True, text=True, timeout=60)
            output = result.stdout

            dfs = []
            parts = output.split("---CSV_START---")
            for part in parts[1:]:
                csv_content = part.split("---CSV_END---")[0].strip()
                if csv_content:
                    dfs.append(pd.read_csv(io.StringIO(csv_content)))

            if dfs:
                return pd.concat(dfs, ignore_index=True)
            return pd.DataFrame()
        except Exception as e:
            logger.warning(f"Playwright fetch failed: {e}")
            return pd.DataFrame()

    def _is_institutional(self, client_name: str) -> bool:
        """Checks if a client name matches any of the institutional keywords."""
        if not client_name or pd.isna(client_name):
            return False
        client_name_upper = str(client_name).upper()
        return any(keyword in client_name_upper for keyword in self.INSTITUTIONAL_KEYWORDS)

    def process_smart_money(self) -> dict:
        """
        Calculates whale scores for all symbols based on institutional net buying.
        Saves the results to data/whale_scores.json and returns the dictionary.
        """
        self._ensure_metadata_cache()
        deals_df = self.get_deals()

        if deals_df.empty:
            logger.info("No deals found for the target date.")
            return {}

        # Standardize columns: strip and uppercase
        deals_df.columns = [str(c).strip().upper() for c in deals_df.columns]

        # Find exact columns
        symbol_col = next((c for c in deals_df.columns if 'SYMBOL' in c), None)
        client_col = next((c for c in deals_df.columns if 'CLIENT' in c), None)
        bs_col = next((c for c in deals_df.columns if 'BUY' in c or 'SELL' in c or 'REMARKS' in c), None)
        qty_col = next((c for c in deals_df.columns if 'QUANTITY' in c or 'QTY' in c), None)

        if not all([symbol_col, client_col, bs_col, qty_col]):
            logger.warning(f"Could not map required columns. Found: {deals_df.columns.tolist()}")
            return {}

        whale_scores = {}
        grouped = deals_df.groupby(symbol_col)

        for symbol, group in grouped:
            # Handle float or other non-string symbols safely
            symbol_str = str(symbol).strip()

            metadata = self.metadata.get(symbol_str)
            if not metadata or 'sharesOutstanding' not in metadata:
                continue

            shares_outstanding = metadata['sharesOutstanding']
            if not shares_outstanding or shares_outstanding <= 0:
                continue

            net_buying = 0
            for _, row in group.iterrows():
                client_name = row[client_col]
                if self._is_institutional(client_name):
                    try:
                        qty = float(str(row[qty_col]).replace(',', ''))
                    except ValueError:
                        qty = 0

                    bs_action = str(row[bs_col]).strip().upper()
                    if 'BUY' in bs_action:
                        net_buying += qty
                    elif 'SELL' in bs_action:
                        net_buying -= qty

            if net_buying > 0:
                pct_bought = (net_buying / shares_outstanding) * 100
                if pct_bought > 0.5:
                    whale_scores[symbol_str] = 1

        os.makedirs("data", exist_ok=True)
        with open("data/whale_scores.json", "w") as f:
            json.dump(whale_scores, f, indent=4)

        logger.info(f"Processed smart money. Found {len(whale_scores)} whales.")
        return whale_scores

    def get_deals(self) -> pd.DataFrame:
        """Fetches deals using the multi-stage fallback."""
        if self._cached_deals is not None:
            return self._cached_deals

        target_date = self._get_last_trading_day()

        # 1. Try jugaad-data (Currently known to have issues, but keeping as stage 1)
        # Temporarily disabled due to NSE blocking/hanging issues
        # try:
        #     df = self._fetch_deals_jugaad(target_date)
        #     if not df.empty:
        #         return df
        # except Exception:
        #     pass

        # 2. Try Direct HTTP
        try:
            df = self._fetch_deals_http()
            if not df.empty:
                self._cached_deals = df
                return df
        except Exception:
            pass

        # 3. Try Playwright
        df = self._fetch_deals_playwright()
        self._cached_deals = df
        return df

    def get_whale_score(self, symbol: str) -> int:
        """
        Calculates the Whale Score for a given symbol based on the latest deals.
        Whale Score = 1 if institutional net buying > 0.5% of total equity, else 0.
        """
        # Get total equity (shares outstanding)
        metadata = self.metadata.get(symbol)
        if not metadata or 'sharesOutstanding' not in metadata:
            return 0

        shares_outstanding = metadata['sharesOutstanding']
        if not shares_outstanding or shares_outstanding <= 0:
            return 0

        # Fetch deals
        deals_df = self.get_deals()
        if deals_df.empty:
            return 0

        # Standardize columns (Bulk/Block CSVs might have slightly different names, but generally 'Symbol', 'Client Name', 'Buy / Sell', 'Quantity Traded')
        if 'Symbol' not in deals_df.columns:
            # Try to find symbol column if it has extra spaces
            col_map = {c: c.strip() for c in deals_df.columns}
            deals_df.rename(columns=col_map, inplace=True)

        if 'Symbol' not in deals_df.columns:
            return 0

        # Filter for the symbol
        symbol_deals = deals_df[deals_df['Symbol'] == symbol]
        if symbol_deals.empty:
            return 0

        # Filter for institutional clients
        # The column name is usually "Client Name"
        client_col = next((c for c in symbol_deals.columns if 'Client' in c and 'Name' in c), None)
        bs_col = next((c for c in symbol_deals.columns if 'Buy' in c and 'Sell' in c), None)
        qty_col = next((c for c in symbol_deals.columns if 'Quantity' in c), None)

        if not client_col or not bs_col or not qty_col:
            return 0

        # Create a boolean mask for institutional keywords
        pattern = '|'.join(self.INSTITUTIONAL_KEYWORDS)
        inst_mask = symbol_deals[client_col].str.contains(pattern, case=False, na=False)
        inst_deals = symbol_deals[inst_mask]

        if inst_deals.empty:
            return 0

        # Calculate net buying
        net_buying = 0
        for _, row in inst_deals.iterrows():
            qty = float(str(row[qty_col]).replace(',', ''))
            bs_action = str(row[bs_col]).strip().upper()

            if bs_action == 'BUY':
                net_buying += qty
            elif bs_action == 'SELL':
                net_buying -= qty

        # Calculate percentage of total equity
        pct_bought = (net_buying / shares_outstanding) * 100

        if pct_bought > 0.5:
            return 1

        return 0
