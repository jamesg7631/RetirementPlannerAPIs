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
NUM_SIMULATIONS = 1000
PLANNING_HORIZON_YEARS = 75
PLANNING_HORIZON_MONTHS = PLANNING_HORIZON_YEARS * 12

# MVO and Risk Profiling Parameters
NUM_RANDOM_PORTFOLIOS_MVO = 50000 # Number of random portfolios for efficient frontier approximation
NUM_MONTHS_IN_YEAR = 12

#  --- Time Horizon Parameters
# Uses the most recent historical lookback periods for MVO for each term
# The actual number of historical months is len(combined_monthly_returns_gbp) = 175 months or ~ 14.5 years. This needs improved!
# This will need to be improved for the 21+ year term

TIME_HORIZON_LOOKBACK_YEARS = {
    "5_year": 5,
    "10_year": 10,
    "15_year": 15,
    "21_plus_year": None ### Assuming if I can obtain history beyond 21+year would I use None or limit the number of years I go back, for instance to 21?
}

# --- Risk Band Definitions
# These need to be frequently recalibrated. Once per quarter?
RISK_BAND_DEFINITIONS_BY_TERM = {
    "5_year": {
        1: {'vol_min': 0.1095, 'vol_max': 0.1177, 'dd_max': -0.650},
        2: {'vol_min': 0.1177, 'vol_max': 0.1259, 'dd_max': -0.680},
        3: {'vol_min': 0.1259, 'vol_max': 0.1341, 'dd_max': -0.710},
        4: {'vol_min': 0.1341, 'vol_max': 0.1423, 'dd_max': -0.740},
        5: {'vol_min': 0.1423, 'vol_max': 0.1505, 'dd_max': -0.770},
        6: {'vol_min': 0.1505, 'vol_max': 0.1587, 'dd_max': -0.800},
        7: {'vol_min': 0.1587, 'vol_max': 0.1669, 'dd_max': -0.830},
        8: {'vol_min': 0.1669, 'vol_max': 0.1751, 'dd_max': -0.860},
        9: {'vol_min': 0.1751, 'vol_max': 0.1833, 'dd_max': -0.890},
        10: {'vol_min': 0.1833, 'vol_max': 0.1937, 'dd_max': -1.0}
    },
    "10_year": {
        1: {'vol_min': 0.0991, 'vol_max': 0.1074, 'dd_max': -0.650},
        2: {'vol_min': 0.1074, 'vol_max': 0.1157, 'dd_max': -0.680},
        3: {'vol_min': 0.1157, 'vol_max': 0.1240, 'dd_max': -0.710},
        4: {'vol_min': 0.1240, 'vol_max': 0.1323, 'dd_max': -0.740},
        5: {'vol_min': 0.1323, 'vol_max': 0.1406, 'dd_max': -0.770},
        6: {'vol_min': 0.1406, 'vol_max': 0.1489, 'dd_max': -0.800},
        7: {'vol_min': 0.1489, 'vol_max': 0.1572, 'dd_max': -0.830},
        8: {'vol_min': 0.1572, 'vol_max': 0.1655, 'dd_max': -0.860},
        9: {'vol_min': 0.1655, 'vol_max': 0.1738, 'dd_max': -0.890},
        10: {'vol_min': 0.1738, 'vol_max': 0.1843, 'dd_max': -1.0}
    },
    "15_year": {
        1: {'vol_min': 0.0952, 'vol_max': 0.1039, 'dd_max': -0.650},
        2: {'vol_min': 0.1039, 'vol_max': 0.1126, 'dd_max': -0.690},
        3: {'vol_min': 0.1126, 'vol_max': 0.1213, 'dd_max': -0.710},
        4: {'vol_min': 0.1213, 'vol_max': 0.1300, 'dd_max': -0.740},
        5: {'vol_min': 0.1300, 'vol_max': 0.1387, 'dd_max': -0.770},
        6: {'vol_min': 0.1387, 'vol_max': 0.1474, 'dd_max': -0.800},
        7: {'vol_min': 0.1474, 'vol_max': 0.1561, 'dd_max': -0.830},
        8: {'vol_min': 0.1561, 'vol_max': 0.1648, 'dd_max': -0.860},
        9: {'vol_min': 0.1648, 'vol_max': 0.1735, 'dd_max': -0.900},
        10: {'vol_min': 0.1735, 'vol_max': 0.1845, 'dd_max': -1.0}
    },
    "21_plus_year": {
        1: {'vol_min': 0.0830, 'vol_max': 0.0926, 'dd_max': -0.650},
        2: {'vol_min': 0.0926, 'vol_max': 0.1022, 'dd_max': -0.680},
        3: {'vol_min': 0.1022, 'vol_max': 0.1118, 'dd_max': -0.710},
        4: {'vol_min': 0.1118, 'vol_max': 0.1214, 'dd_max': -0.740},
        5: {'vol_min': 0.1214, 'vol_max': 0.1310, 'dd_max': -0.770},
        6: {'vol_min': 0.1310, 'vol_max': 0.1406, 'dd_max': -0.800},
        7: {'vol_min': 0.1406, 'vol_max': 0.1502, 'dd_max': -0.830},
        8: {'vol_min': 0.1502, 'vol_max': 0.1598, 'dd_max': -0.860},
        9: {'vol_min': 0.1598, 'vol_max': 0.1694, 'dd_max': -0.890},
        10: {'vol_min': 0.1694, 'vol_max': 0.1808, 'dd_max': -1.0}
    }
}

# No longer in use. Make sure code runs without and remove

# TARGET_VOLATILITIES_FOR_RISK_LEVELS_BY_TERM = {
#     "5_year": {
#         1: 0.1136, 2: 0.1218, 3: 0.1300, 4: 0.1382, 5: 0.1464,
#         6: 0.1546, 7: 0.1628, 8: 0.1710, 9: 0.1792, 10: 0.1885
#     },
#     "10_year": {
#         1: 0.1032, 2: 0.1116, 3: 0.1198, 4: 0.1281, 5: 0.1365,
#         6: 0.1448, 7: 0.1531, 8: 0.1614, 9: 0.1697, 10: 0.1790
#     },
#     "15_year": {
#         1: 0.0996, 2: 0.1083, 3: 0.1170, 4: 0.1257, 5: 0.1344,
#         6: 0.1430, 7: 0.1518, 8: 0.1604, 9: 0.1692, 10: 0.1790
#     },
#     "21_plus_year": {
#         1: 0.0878, 2: 0.0974, 3: 0.1070, 4: 0.1166, 5: 0.1262,
#         6: 0.1358, 7: 0.1454, 8: 0.1550, 9: 0.1646, 10: 0.1751
#     }
# }
