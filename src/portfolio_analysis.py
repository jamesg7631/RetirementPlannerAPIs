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

def plot_efficient_frontier(portfolios_df: pd.DataFrame, efficient_frontier_df: pd.DataFrame):
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
    plt.title('Portfolio Optimization - Efficient Frontier (Annualized)')
    plt.xlabel('Annualized Volatility (Standard Deviation)')
    plt.ylabel('Annualized Return')
    plt.grid(True)
    plt.legend()
    plt.show()

def run_portfolio_analysis():
    """
    Orchestrates the portfolio analysis steps: MVO, Efficient Frontier generation and plotting.
    """
    print("\n--- Starting Portfolio Analysis ---")

    # 1. Consolidate GBP monthly returns data
    # List all final GBP monthly return CSV filenames (including converted ones)
    final_gbp_asset_files = [f"{t}_monthly_returns_GBP.csv" for t in config.ASSET_TICKER_LIST_DAILY if t != config.GBP_ASSET_ORIGINAL_FILE.replace('_monthly_returns.csv', '')]
    final_gbp_asset_files.append(config.MONEYMARKET_GBP_RETURNS_FILE)
    final_gbp_asset_files.append(config.GBP_ASSET_ORIGINAL_FILE) # IUKP.L

    combined_returns = consolidate_gbp_returns(
        [t.replace('_monthly_returns_GBP.csv', '').replace('_monthly_returns.csv', '') for t in final_gbp_asset_files],
        config.GBP_MONTHLY_RETURNS_DIR
    )

    if combined_returns.empty:
        print("Error: Combined GBP returns data is empty for portfolio analysis. Exiting.")
        return None, None # Return None if no data

    # 2. Generate Efficient Frontier
    portfolios_df, efficient_frontier_df = generate_efficient_frontier(combined_returns)

    # 3. Plot Efficient Frontier
    plot_efficient_frontier(portfolios_df, efficient_frontier_df)
    print("--- Portfolio Analysis Complete ---")
    return portfolios_df, efficient_frontier_df # Return these for use in risk profiling