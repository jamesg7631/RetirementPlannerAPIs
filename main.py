import os
from datetime import datetime
from src import config
from src import data_acquisition
from src import data_processing
from src import portfolio_analysis
from src import simulation
from src import risk_profiling

def run_full_pipeline():
    """
    Orchestrates the entire data processing and analysis pipeline.
    """
    print("--- Starting Full Retirement Planner Data Pipeline ---")

    # # Step 1: Acquire Raw Data (Daily prices from Yahoo Finance)
    # # This downloads CSVs to data/raw_daily/
    # data_acquisition.acquire_all_raw_data() ## Tested
    #
    # # Step 2: Process Raw Data into Monthly GBP Returns
    # # This converts daily data to monthly and performs USD->GBP conversion.
    # # Saves CSVs to data/outputs/gbp_monthly_returns/
    # data_processing.process_all_monthly_returns()

    # Step 3: Run Monte Carlo Simulation (Historical Bootstrapping)
    # First, consolidate the processed GBP monthly returns for simulation input.
    # The list of asset names here should match the asset names expected by simulation.py.
    # It includes all assets that will have _GBP.csv or just .csv.
    all_asset_names_for_sim = [
        'Moneymarket', 'AGG', 'LQD', 'HYG', 'IWDA.L', 'EEM', 'VNQI',
        'DBC', 'GLD', 'IGF', 'IUKP.L'
    ]
    consolidated_gbp_returns_for_sim = data_processing.consolidate_gbp_returns(
        all_asset_names_for_sim, config.GBP_MONTHLY_RETURNS_DIR
    )
    # if consolidated_gbp_returns_for_sim.empty:
    #     print("Skipping Monte Carlo simulation: No consolidated GBP returns data.")
    # else:
    #     # Run simulation and save .npy files to data/outputs/simulated_paths/
    #     simulation.run_historical_bootstrapping(consolidated_gbp_returns_for_sim)

    # Step 4: Perform Portfolio Analysis (MVO & Efficient Frontier)
    # This uses the same consolidated GBP returns data.
    # `run_portfolio_analysis` handles its own data consolidation internally, but we could pass it.
    portfolios_df, efficient_frontier_df = portfolio_analysis.run_portfolio_analysis()
    # # Step 5: Define Risk Profiles and Model Portfolios
    # if efficient_frontier_df is not None and not efficient_frontier_df.empty:
    #     # `define_and_select_model_portfolios` loads simulated paths internally
    #     risk_profiling.define_and_select_model_portfolios(efficient_frontier_df)
    # else:
    #     print("Skipping risk profiling: No Efficient Frontier data available.")
    #
    # print("\n--- Full Retirement Planner Data Pipeline Complete ---")

if __name__ == "__main__":
    run_full_pipeline()