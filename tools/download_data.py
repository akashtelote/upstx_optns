import os
import yfinance as yf
import pandas as pd
from datetime import datetime

def download_nifty_data(start_date="2015-01-01", output_format="parquet"):
    """
    Downloads historical daily data for Nifty 50 (^NSEI), cleans it,
    and saves it to the specified format.
    """
    ticker = "^NSEI"
    end_date = datetime.today().strftime('%Y-%m-%d')

    print(f"Downloading {ticker} data from {start_date} to {end_date}...")
    df = yf.download(ticker, start=start_date, end=end_date)

    if df.empty:
        print("Error: No data downloaded.")
        return

    # yfinance returns MultiIndex columns if returning multiple tickers, or recently due to a change.
    # We need to flatten the columns.
    if isinstance(df.columns, pd.MultiIndex):
        # We use droplevel(1) or list comprehension because level 0 is Price ('Close', 'Open', etc.)
        # but the prompt suggested `df.columns = df.columns.droplevel(0)` as an example.
        # Dropping level 0 would leave ticker symbols. We will take the first element of each tuple,
        # which effectively extracts the 'Close', 'Open' string, handling both the prompt's intent
        # and yfinance's structure.
        df.columns = [col[0] if isinstance(col, tuple) else col for col in df.columns]

    # Standardize to lowercase
    df.columns = [str(c).lower() for c in df.columns]

    # Drop rows containing NaN values (holidays, etc)
    df = df.dropna()

    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)

    if output_format == "parquet":
        output_file = "data/nifty50_historical.parquet"
        df.to_parquet(output_file, engine="pyarrow")
        print(f"Data successfully saved to {output_file}")
    elif output_format == "csv":
        output_file = "data/nifty50_historical.csv"
        df.to_csv(output_file)
        print(f"Data successfully saved to {output_file}")
    else:
        print(f"Error: Unknown output format '{output_format}'")
        return

    print(f"Total records: {len(df)}")
    print("Preview of data:")
    print(df.head(3))

if __name__ == "__main__":
    download_nifty_data()
