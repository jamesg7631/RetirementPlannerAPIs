import pandas as pd
import numpy as np
import os
from datetime import datetime
from dateutil.relativedelta import relativedelta
import calendar
from src import config

class BOEInterestRate:
    def __init__(self, date, annual_rate):
        self.date = date
        self.annual_rate = annual_rate

def read_boe_raw(filepath: str) -> list:
    """
    Reads raw BOE interest rate data from a CSV.
    Assumes CSV format: Date (DD Month YY), Annual_Rate
    """
    interest_rates = []
    print(f"Reading BOE data from {filepath}...")
    try:
        with open(filepath) as new_file:
            next(new_file) # Skip header
            for line in new_file:
                items = line.strip().split(',')
                if len(items) < 2: continue # Skip bad lines
                original_date = items[0]
                # Handle possible date formats, e.g., "01 Jan 20" or "01 Jan 2020"
                # Try parsing with full year first, then two-digit year
                try:
                    date_obj = datetime.strptime(original_date, "%d %b %Y")
                except ValueError:
                    date_obj = datetime.strptime(original_date, "%d %b %y")
                interest_rate_entry = BOEInterestRate(date_obj, float(items[1]))
                interest_rates.append(interest_rate_entry)
        # Sort in ascending order by date for easier processing (obtain_monthly_cash_accrual expects descending)
        interest_rates.sort(key=lambda x: x.date)
        print(f"Loaded {len(interest_rates)} BOE interest rate entries.")
        return interest_rates
    except FileNotFoundError:
        print(f"Error: BOE raw data file not found at {filepath}.")
        return []
    except Exception as e:
        print(f"Error reading BOE raw data: {e}")
        return []

def calculate_monthly_cash_returns(interest_rate_data: list, starting_date: datetime, end_date: datetime) -> list:
    """
    Calculates monthly accumulation factors (returns) from BOE daily interest rates.
    """
    if not interest_rate_data:
        return []
    monthly_returns_list = []

    # 1. Prepare rate data: Create a lookup for rates by date (more efficient for daily loop)
    # Sort descending, as it's the natural way rates change going back in time.
    # Also, BOEInterestRate from read_boe is ASCENDING, so reverse it
    # to find current rate by iterating backwards (index current_rate_index - 1)
    interest_rate_data.sort(key=lambda x: x.date, reverse=True)

    # Find the initial rate index (the latest rate active before or on starting_date)
    current_rate_index = 0
    for i, entry in enumerate(interest_rate_data):
        if entry.date <= starting_date:
            current_rate_index = i
            break
    # If starting_date is earlier than all BOE dates, use the oldest rate
    if current_rate_index == 0 and interest_rate_data[-1].date > starting_date:
        current_rate_index = len(interest_rate_data) - 1 # Use oldest rate if start date is before first BOE rate

    # 2. Set up the monthly iteration
    # Start calculations from the beginning of the month of starting_date
    current_month_first_day = datetime(starting_date.year, starting_date.month, 1)
    print(f"Calculating monthly money market returns from {starting_date.strftime('%Y-%m')} to {end_date.strftime('%Y-%m')}...")
    while current_month_first_day <= end_date:
        # Determine the actual start day for daily accrual in this month
        day_for_daily_accrual_start = max(current_month_first_day, starting_date)

        # Determine the actual end day for daily accrual in this month
        next_month_first_day = current_month_first_day + relativedelta(months=1)
        day_for_daily_accrual_end = min(next_month_first_day - relativedelta(days=1), end_date)

        # Only process if the start day is not after the end day for this month's segment
        if day_for_daily_accrual_start > day_for_daily_accrual_end:
            current_month_first_day = next_month_first_day # Move to next month
            continue

        # Accumulate value over the month based on daily compounding
        value_at_start_of_month_period = 1.0
        current_day_in_loop = day_for_daily_accrual_start

        while current_day_in_loop <= day_for_daily_accrual_end:
            # Update current_rate_index if a *newer* rate has become active on or before current_day_in_loop.
            # interest_rate_data is sorted DESCENDING by date, so we move TOWARDS the beginning (index 0)
            # if the next (newer) rate entry's date is <= current_day_in_loop
            while current_rate_index > 0 and interest_rate_data[current_rate_index - 1].date <= current_day_in_loop:
                current_rate_index -= 1

            # Ensure we are not out of bounds
            if current_rate_index >= len(interest_rate_data):
                # This should ideally not happen if initial_rate_index is set correctly
                print(f"Warning: No BOE rate found for {current_day_in_loop}. Using last known rate.")
                current_annual_rate = interest_rate_data[-1].annual_rate # Fallback to oldest rate
            else:
                current_annual_rate = interest_rate_data[current_rate_index].annual_rate

            # Daily compounding
            days_in_year = 366 if calendar.isleap(current_day_in_loop.year) else 365
            daily_factor = (1 + (current_annual_rate / 100))**(1/days_in_year)
            value_at_start_of_month_period *= daily_factor

            current_day_in_loop += relativedelta(days=1)

        # Calculate monthly return for this period
        monthly_return = value_at_start_of_month_period - 1.0

        # Store the monthly return with the end date of the period
        monthly_returns_list.append({
            'Date': day_for_daily_accrual_end,
            'Monthly_Return': monthly_return
        })

        # Move to the next calendar month for the outer loop
        current_month_first_day = next_month_first_day

    print(f"Generated {len(monthly_returns_list)} monthly money market returns.")
    return monthly_returns_list

def convert_daily_to_monthly_returns(ticker_symbol: str, raw_data_dir: str, monthly_returns_dir: str):
    """
    Reads daily historical data, converts to monthly adjusted returns, and saves.
    """
    daily_file_name = os.path.join(raw_data_dir, f"{ticker_symbol.replace('^', '_')}_historical_data.csv")
    monthly_file_name = os.path.join(monthly_returns_dir, f"{ticker_symbol.replace('^', '_')}_monthly_returns.csv")

    if not os.path.exists(daily_file_name):
        print(f"Error: Daily data CSV for {ticker_symbol} not found at {daily_file_name}. Skipping monthly conversion.")
        return False

    print(f"Converting daily data to monthly returns for {ticker_symbol}...")
    try:
        #daily_data = pd.read_csv(daily_file_name, index_col='Date', parse_dates=True)
        daily_data = pd.read_csv(daily_file_name, sep=',', header=None, names=['Date', 'Adj Close', 'High', 'Low','Open', 'Volume'], skiprows= 3, parse_dates=['Date',], index_col='Date')
        # Use 'Adj Close' if available, otherwise 'Close'
        if 'Adj Close' in daily_data.columns:
            prices_to_use = daily_data['Adj Close']
        elif 'Close' in daily_data.columns:
            prices_to_use = daily_data['Close']
        else:
            print(f"Warning: Neither 'Adj Close' nor 'Close' found for {ticker_symbol}. Cannot convert to monthly returns.")
            return False

        monthly_prices = prices_to_use.resample('M').last()
        monthly_returns = monthly_prices.pct_change().dropna()
        monthly_returns.name = 'Monthly_Return' # Name the series for a clean CSV header

        monthly_returns.to_csv(monthly_file_name)
        print(f"Monthly returns for {ticker_symbol} saved to {monthly_file_name}")
        return True
    except Exception as e:
        print(f"Error converting {ticker_symbol} daily data: {e}")
        return False

def convert_usd_to_gbp_returns(usd_asset_ticker: str, fx_ticker: str, monthly_returns_dir: str):
    """
    Loads monthly returns for a USD-denominated asset, converts them to GBP returns
    using the FX monthly returns, and saves the new GBP returns to a CSV.
    """
    usd_input_file_name = os.path.join(monthly_returns_dir, f"{usd_asset_ticker.replace('^', '_')}_monthly_returns.csv")
    fx_input_file_name = os.path.join(monthly_returns_dir, f"{fx_ticker.replace('^', '_')}_monthly_returns.csv")
    gbp_output_file_name = os.path.join(monthly_returns_dir, f"{usd_asset_ticker.replace('^', '_')}_monthly_returns_GBP.csv")

    if not os.path.exists(usd_input_file_name):
        print(f"Error: USD monthly returns CSV for {usd_asset_ticker} not found at {usd_input_file_name}. Skipping conversion.")
        return False
    if not os.path.exists(fx_input_file_name):
        print(f"Error: FX monthly returns CSV for {fx_ticker} not found at {fx_input_file_name}. Skipping conversion.")
        return False

    print(f"Converting {usd_asset_ticker} (USD) to GBP returns...")
    try:
        usd_returns_df = pd.read_csv(usd_input_file_name, index_col='Date', parse_dates=True)
        fx_returns_df = pd.read_csv(fx_input_file_name, index_col='Date', parse_dates=True)

        usd_returns_series = usd_returns_df['Monthly_Return']
        fx_returns_series = fx_returns_df['Monthly_Return']

        # Align the FX returns with the USD asset returns
        combined_data = pd.DataFrame({
            'USD_Return': usd_returns_series,
            'FX_Return': fx_returns_series
        }).dropna()

        if combined_data.empty:
            print(f"Warning: No overlapping historical data found for {usd_asset_ticker} and FX rates. Skipping conversion.")
            return False

        # Perform the currency conversion: R_GBP = (1 + R_USD) * (1 + R_FX) - 1
        gbp_returns_series = (1 + combined_data['USD_Return']) * (1 + combined_data['FX_Return']) - 1
        gbp_returns_series.name = 'Monthly_Return'

        gbp_returns_series.to_csv(gbp_output_file_name)
        print(f"Converted monthly returns for {usd_asset_ticker} to GBP and saved to {gbp_output_file_name}")
        return True
    except Exception as e:
        print(f"Error converting {usd_asset_ticker} to GBP: {e}")
        return False

def consolidate_gbp_returns(asset_names: list, folder_path: str) -> pd.DataFrame:
    """
    Loads final GBP monthly returns from CSVs and combines them into a single DataFrame.
    This DataFrame is used as the input for MVO and Monte Carlo simulation.
    """
    all_returns = {}
    for asset_name in asset_names:
        # Check for GBP converted file first
        filename_gbp = os.path.join(folder_path, f"{asset_name}_monthly_returns_GBP.csv")
        # For IUKP.L, it's the original monthly returns file
        filename_original_gbp = os.path.join(folder_path, f"{asset_name}_monthly_returns.csv")

        file_to_load = None
        if os.path.exists(filename_gbp):
            file_to_load = filename_gbp
        elif os.path.exists(filename_original_gbp) and asset_name == 'IUKP.L':
            file_to_load = filename_original_gbp

        if not file_to_load:
            print(f"Warning: No suitable GBP monthly returns CSV found for {asset_name}. Skipping consolidation.")
            continue

        try:
            df = pd.read_csv(file_to_load, index_col='Date', parse_dates=True)
            # Both converted and original GBP returns should have this column name
            if 'Monthly_Return' in df.columns:
                all_returns[asset_name] = df['Monthly_Return']
            else:
                print(f"Warning: 'Monthly_Return' column not found in {file_to_load}. Skipping consolidation.")

        except Exception as e:
            print(f"Error processing {file_to_load} for consolidation: {e}")

    combined_df = pd.DataFrame(all_returns)
    initial_rows = len(combined_df)
    combined_df.dropna(inplace=True) # Ensure all rows are complete for consistent analysis
    final_rows = len(combined_df)

    if initial_rows != final_rows:
        print(f"Warning: Dropped {initial_rows - final_rows} rows in combined DataFrame during consolidation due to missing data for some assets.")
        print(f"Common data period: {combined_df.index.min().strftime('%Y-%m')} to {combined_df.index.max().strftime('%Y-%m')}")

    combined_df.sort_index(inplace=True) # Ensure chronological order

    print(f"Consolidated GBP monthly returns DataFrame shape: {combined_df.shape}")
    print(f"Data covers: {combined_df.index.min().strftime('%Y-%m')} to {combined_df.index.max().strftime('%Y-%m')}")
    return combined_df

def process_all_monthly_returns():
    """
    Orchestrates the conversion of all raw data into monthly GBP returns.
    """
    print("\n--- Starting Monthly Returns Processing ---")

    # 1. Convert daily ETF/FX data to monthly returns
    for ticker in config.ASSET_TICKER_LIST_DAILY:
        convert_daily_to_monthly_returns(ticker, config.RAW_DATA_DIR, config.GBP_MONTHLY_RETURNS_DIR)
    convert_daily_to_monthly_returns(config.FX_TICKER, config.RAW_DATA_DIR, config.GBP_MONTHLY_RETURNS_DIR)

    # 2. Convert BOE rates to Money Market monthly returns
    boe_raw_filepath = os.path.join(config.BOE_DATA_DIR, config.BOE_RAW_FILE)
    boe_rates = read_boe_raw(boe_raw_filepath)
    # Use dates that align with the downloaded data
    start_date_obj = datetime.strptime(config.DOWNLOAD_START_DATE, "%Y-%m-%d")
    end_date_obj = datetime.strptime(config.DOWNLOAD_END_DATE, "%Y-%m-%d")

    monthly_moneymarket_returns_list = calculate_monthly_cash_returns(boe_rates, start_date_obj, end_date_obj)

    # Convert list of dicts to DataFrame and save
    if monthly_moneymarket_returns_list:
        mm_df = pd.DataFrame(monthly_moneymarket_returns_list).set_index('Date')
        mm_df.index = pd.to_datetime(mm_df.index) # Ensure index is datetime
        mm_df.to_csv(os.path.join(config.GBP_MONTHLY_RETURNS_DIR, config.MONEYMARKET_GBP_RETURNS_FILE))
        print(f"Money market monthly returns saved to {os.path.join(config.GBP_MONTHLY_RETURNS_DIR, config.MONEYMARKET_GBP_RETURNS_FILE)}")
    else:
        print("Warning: No money market returns generated.")

    # 3. Convert USD asset monthly returns to GBP
    for usd_ticker in config.USD_ASSETS_TO_CONVERT:
        convert_usd_to_gbp_returns(usd_ticker, config.FX_TICKER, config.GBP_MONTHLY_RETURNS_DIR)

    print("--- Monthly Returns Processing Complete ---")