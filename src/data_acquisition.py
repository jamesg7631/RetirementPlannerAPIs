import yfinance as yf
import pandas as pd
import os
from src import config

def download_daily_data(ticker_symbol: str, start_date: str, end_date: str, output_dir: str):
    """
    Downloads historical daily data for a given ticker and saves it to a CSV.
    """
    file_name = os.path.join(output_dir, f"{ticker_symbol.replace('^', '_')}_historical_data.csv")
    print(f"Downloading daily data for {ticker_symbol} from {start_date} to {end_date}...")
    try:
        etf_data = yf.download(ticker_symbol, start=start_date, end=end_date)
        if etf_data.empty:
            print(f"Warning: No data downloaded for {ticker_symbol}. Check ticker or dates.")
            return False

        etf_data.to_csv(file_name)
        print(f"Daily data for {ticker_symbol} saved to {file_name}")
        return True
    except Exception as e:
        print(f"Error downloading data for {ticker_symbol}: {e}")
        return False

def acquire_all_raw_data():
    """
    Acquires all necessary raw daily data from yfinance.
    """
    print("\n--- Starting Raw Data Acquisition ---")
    # Download daily data for asset tickers
    for ticker in config.ASSET_TICKER_LIST_DAILY:
        download_daily_data(ticker, config.DOWNLOAD_START_DATE, config.DOWNLOAD_END_DATE, config.RAW_DATA_DIR)
    # Download daily data for FX ticker
    download_daily_data(config.FX_TICKER, config.DOWNLOAD_START_DATE, config.DOWNLOAD_END_DATE, config.RAW_DATA_DIR)
    print("--- Raw Data Acquisition Complete ---")