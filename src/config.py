import os
from datetime import datetime

# --- General Configuration ---
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'raw_daily')
BOE_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'boe')
OUTPUT_DATA_DIR = os.path.join(PROJECT_ROOT, 'data', 'outputs')
GBP_MONTHLY_RETURNS_DIR = os.path.join(OUTPUT_DATA_DIR, 'gbp_monthly_returns')
SIMULATED_PATHS_DIR = os.path.join(OUTPUT_DATA_DIR, 'simulated_paths')

# Create directories if they don't exist
os.makedirs(RAW_DATA_DIR, exist_ok=True)
os.makedirs(BOE_DATA_DIR, exist_ok=True)
os.makedirs(GBP_MONTHLY_RETURNS_DIR, exist_ok=True)
os.makedirs(SIMULATED_PATHS_DIR, exist_ok=True)

# --- Data Acquisition Parameters ---
DOWNLOAD_START_DATE = "2010-11-01"
DOWNLOAD_END_DATE = "2025-06-30"

# Tickers for which to download daily data and convert to monthly returns
ASSET_TICKER_LIST_DAILY = [
    'AGG', 'LQD', 'HYG', 'IWDA.L', 'EEM', 'VNQI', 'DBC', 'GLD', 'IUKP.L', 'IGF'
]
FX_TICKER = 'GBPUSD=X'

# BOE Interest Rate data file (relative to BOE_DATA_DIR)
BOE_RAW_FILE = 'BOE_rates_original.csv'
MONEYMARKET_GBP_RETURNS_FILE = 'Moneymarket_monthly_returns_GBP.csv'

# Assets that are USD-denominated and need conversion to GBP
USD_ASSETS_TO_CONVERT = [
    'AGG', 'LQD', 'HYG', 'IWDA.L', 'EEM', 'VNQI', 'DBC', 'GLD', 'IGF' # Assuming IWDA.L is USD for conversion as per your check
]
# Asset that is already in GBP
GBP_ASSET_ORIGINAL_FILE = 'IUKP.L_monthly_returns.csv'

# Monte Carlo Simulation Parameters
NUM_SIMULATIONS = 10000
PLANNING_HORIZON_YEARS = 75
PLANNING_HORIZON_MONTHS = PLANNING_HORIZON_YEARS * 12

# MVO and Risk Profiling Parameters
NUM_RANDOM_PORTFOLIOS_MVO = 50000 # Number of random portfolios for efficient frontier approximation
NUM_MONTHS_IN_YEAR = 12

# Risk band definitions ### Adjust these after running MVO and plotting
RISK_BAND_DEFINITIONS = {
    # Risk Level: {'vol_min': X, 'vol_max': Y, 'dd_max': Z}
    # dd_max is the *maximum allowed negative drawdown* (e.g., -0.075 means max 7.5% loss)
    1: {'vol_min': 0.090, 'vol_max': 0.100, 'dd_max': -0.075},
    2: {'vol_min': 0.100, 'vol_max': 0.110, 'dd_max': -0.100},
    3: {'vol_min': 0.110, 'vol_max': 0.120, 'dd_max': -0.125},
    4: {'vol_min': 0.120, 'vol_max': 0.130, 'dd_max': -0.150},
    5: {'vol_min': 0.130, 'vol_max': 0.140, 'dd_max': -0.175},
    6: {'vol_min': 0.140, 'vol_max': 0.150, 'dd_max': -0.200},
    7: {'vol_min': 0.150, 'vol_max': 0.160, 'dd_max': -0.250},
    8: {'vol_min': 0.160, 'vol_max': 0.170, 'dd_max': -0.300},
    9: {'vol_min': 0.170, 'vol_max': 0.180, 'dd_max': -0.350},
    10: {'vol_min': 0.180, 'vol_max': 1.0, 'dd_max': -1.0} # Upper bound for risk 10
}

# Target volatilities for selecting portfolios from the efficient frontier
TARGET_VOLATILITIES_FOR_RISK_LEVELS = {
    1: 0.095,  # ~9.5%
    2: 0.105,  # ~10.5%
    3: 0.115,  # ~11.5%
    4: 0.125,  # ~12.5%
    5: 0.135,  # ~13.5%
    6: 0.145,  # ~14.5%
    7: 0.155,  # ~15.5%
    8: 0.165,  # ~16.5%
    9: 0.175,  # ~17.5%
    10: 0.185   # ~18.5%
}
