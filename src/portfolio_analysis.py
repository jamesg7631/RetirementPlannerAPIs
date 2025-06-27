import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from src import config
from src.data_processing import consolidate_gbp_returns # Import the function to get combined data

def calculate_portfolio_metrics(weights, expected_returns, cov_matrix):
    """
    Calculates portfolio return and volatility.
    """
    p_return = np.sum(expected_returns * weights)
    p_volatility = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
    return p_return, p_volatility

def generate_efficient_frontier(combined_returns_df: pd.DataFrame):
    """
    Calculates MVO inputs, generates random portfolios, and approximates the Efficient Frontier.
    Returns portfolios_df and efficient_frontier DataFrame.
    """
    asset_names = combined_returns_df.columns.tolist()
    num_assets = len(asset_names)

    # Calculate MVO inputs (Annualized)
    expected_returns_annualized = (1 + combined_returns_df.mean())**config.NUM_MONTHS_IN_YEAR - 1
    covariance_matrix_annualized = combined_returns_df.cov() * config.NUM_MONTHS_IN_YEAR
    std_devs_annualized = np.sqrt(np.diag(covariance_matrix_annualized))
    std_devs_annualized = pd.Series(std_devs_annualized, index=asset_names)

    print("\n--- MVO Input Statistics (Annualized) ---")
    print("Expected Returns:\n", expected_returns_annualized)
    print("\nCovariance Matrix (first 5x5):\n", covariance_matrix_annualized.iloc[:5, :5])
    print("\nStandard Deviations (Volatility):\n", std_devs_annualized)

    # Generate Random Portfolios
    num_portfolios = config.NUM_RANDOM_PORTFOLIOS_MVO
    results = np.zeros((3, num_portfolios)) # Row 0: Vol, Row 1: Return, Row 2: Sharpe Ratio
    all_weights = np.zeros((num_portfolios, num_assets))

    print(f"\n--- Generating {num_portfolios} Random Portfolios for MVO ---")
    for i in range(num_portfolios):
        weights = np.random.random(num_assets)
        weights /= np.sum(weights) # Normalize weights

        p_return, p_volatility = calculate_portfolio_metrics(
            weights, expected_returns_annualized.values, covariance_matrix_annualized.values
        )

        results[0,i] = p_volatility
        results[1,i] = p_return
        results[2,i] = p_return / p_volatility # Sharpe Ratio (assuming 0 risk-free rate)
        all_weights[i,:] = weights

    columns = ['Volatility', 'Return', 'Sharpe_Ratio'] + asset_names
    portfolios_df = pd.DataFrame(data=np.c_[results.T, all_weights], columns=columns)
    print("Sample of generated portfolios (first 5 rows):\n", portfolios_df.head())

    # Approximate the Efficient Frontier
    portfolios_df_sorted = portfolios_df.sort_values(by=['Volatility', 'Return'], ascending=[True, False])
    volatility_bins = np.linspace(portfolios_df_sorted['Volatility'].min(), portfolios_df_sorted['Volatility'].max(), 100)

    efficient_frontier = pd.DataFrame(columns=portfolios_df.columns)
    for i in range(len(volatility_bins) - 1):
        bin_start = volatility_bins[i]
        bin_end = volatility_bins[i+1]
        bin_portfolios = portfolios_df_sorted[(portfolios_df_sorted['Volatility'] >= bin_start) &
                                              (portfolios_df_sorted['Volatility'] < bin_end)]
        if not bin_portfolios.empty:
            efficient_portfolio = bin_portfolios.loc[bin_portfolios['Return'].idxmax()]
            efficient_frontier = pd.concat([efficient_frontier, pd.DataFrame([efficient_portfolio])], ignore_index=True)

    efficient_frontier.drop_duplicates(subset=['Volatility'], inplace=True)
    efficient_frontier.sort_values(by='Volatility', inplace=True)

    print("\n--- Approximate Efficient Frontier Data (first 5 points) ---")
    print(efficient_frontier.head())

    return portfolios_df, efficient_frontier

def plot_efficient_frontier(portfolios_df: pd.DataFrame, efficient_frontier_df: pd.DataFrame, term_name:str):
    """
    Plots all random portfolios and highlights the Efficient Frontier.
    """
    print("\n--- Displaying Efficient Frontier Plot ---")
    plt.figure(figsize=(12, 7))
    plt.scatter(portfolios_df['Volatility'], portfolios_df['Return'],
                c=portfolios_df['Sharpe_Ratio'], cmap='viridis', s=10, alpha=0.5)
    plt.colorbar(label='Sharpe Ratio (Annualized)')
    plt.scatter(efficient_frontier_df['Volatility'], efficient_frontier_df['Return'],
                color='red', marker='o', s=50, label='Efficient Frontier')
    title = "Portfolio Optimization - Efficient Frontier (Annualized) for " + term_name + " Term"
    plt.title(title)
    plt.xlabel('Annualized Volatility (Standard Deviation)')
    plt.ylabel('Annualized Return')
    plt.grid(True)
    plt.legend()
    plt.show()

def run_portfolio_analysis_by_term():
    """
    Orchestrates the portfolio analysis steps for each defined time horizon.
    Generates and plots a separate Efficient Frontier for each term.
    Returns a dictionary of (portfolios_df, efficient_frontier_df) for each term.
    """
    print("\n--- Starting Portfolio Analysis by Term ---")

    all_term_results = {} # To store (portfolios_df, efficient_frontier_df) for each term

    # 1. Consolidate ALL GBP monthly returns data (full history)
    # This consolidated_full_history_returns will be filtered for each term's MVO.
    final_gbp_asset_files = [f"{t}_monthly_returns_GBP.csv" for t in config.USD_ASSETS_TO_CONVERT]
    final_gbp_asset_files.append(config.MONEYMARKET_GBP_RETURNS_FILE)
    final_gbp_asset_files.append(config.GBP_ASSET_ORIGINAL_FILE) # IUKP.L

    combined_full_history_returns = consolidate_gbp_returns(
        [t.replace('_monthly_returns_GBP.csv', '').replace('_monthly_returns.csv', '') for t in final_gbp_asset_files],
        config.GBP_MONTHLY_RETURNS_DIR
    )

    if combined_full_history_returns.empty:
        print("Error: Combined GBP returns data is empty for portfolio analysis. Exiting.")
        return {}

    # 2. Loop through each defined time horizon
    for term_name, lookback_years in config.TIME_HORIZON_LOOKBACK_YEARS.items():
        print(f"\n===== Running MVO for {term_name} term (Lookback: {lookback_years} years) =====")

        # Filter data for the specific lookback period
        if lookback_years is None: # Use full history for the longest term
            term_combined_returns = combined_full_history_returns.copy()
            print(f"  Using full history ({len(term_combined_returns)//12} years) for {term_name} term.")
        else:
            lookback_months = lookback_years * config.NUM_MONTHS_IN_YEAR
            if len(combined_full_history_returns) < lookback_months:
                print(f"  Warning: Not enough historical data ({len(combined_full_history_returns)} months) for {term_name} lookback ({lookback_months} months). Using all available data.")
                term_combined_returns = combined_full_history_returns.copy()
            else:
                # Select the most recent `lookback_months`
                term_combined_returns = combined_full_history_returns.tail(lookback_months).copy()
            print(f"  Using {len(term_combined_returns)//12} years of most recent data for {term_name} term.")

        if term_combined_returns.empty:
            print(f"  Skipping {term_name}: Filtered data is empty.")
            continue

        # Generate Efficient Frontier for this term
        portfolios_df_term, efficient_frontier_df_term = generate_efficient_frontier(term_combined_returns)

        # Plot Efficient Frontier for this term (optional, but highly recommended for calibration)
        print(f"\n--- Plot for {term_name} term ---")
        plot_efficient_frontier(portfolios_df_term, efficient_frontier_df_term, term_name)

        all_term_results[term_name] = {
            'portfolios_df': portfolios_df_term,
            'efficient_frontier_df': efficient_frontier_df_term
        }

    print("\n--- Portfolio Analysis by Term Complete ---")
    return all_term_results