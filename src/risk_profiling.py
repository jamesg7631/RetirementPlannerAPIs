import pandas as pd
import numpy as np
import os
from src import config
from src.simulation import load_simulated_paths
from src.portfolio_analysis import calculate_portfolio_metrics # To reuse portfolio volatility calculation

def calculate_max_drawdown(value_series: pd.Series) -> float:
    """
    Calculates the maximum drawdown for a given value series.
    Drawdown is a negative percentage.
    """
    peak_value = value_series.expanding(min_periods=1).max()
    drawdown = (value_series / peak_value) - 1.0
    return drawdown.min()

def define_and_select_model_portfolios(efficient_frontier_df: pd.DataFrame):
    """
    Defines risk bands, identifies model portfolios from the efficient frontier,
    and calculates their simulated maximum drawdowns.
    """
    if efficient_frontier_df.empty:
        print("Error: Efficient Frontier DataFrame is empty. Cannot define model portfolios.")
        return pd.DataFrame()

    # Asset names from the efficient frontier columns (excluding metrics)
    asset_names = [col for col in efficient_frontier_df.columns if col not in ['Volatility', 'Return', 'Sharpe_Ratio']]

    # Load simulated paths (needed for drawdown calculation)
    loaded_sim_paths = load_simulated_paths(asset_names, config.SIMULATED_PATHS_DIR)
    if not loaded_sim_paths:
        print("Error: Simulated paths not loaded. Cannot calculate max drawdowns for model portfolios.")
        return pd.DataFrame()

    num_simulations = loaded_sim_paths[asset_names[0]].shape[0]
    planning_horizon_months = loaded_sim_paths[asset_names[0]].shape[1]

    final_model_portfolios = {}

    print("\n--- Identifying Model Portfolios & Calculating Drawdowns ---")

    # Iterate through each desired risk level based on target volatilities
    for risk_level, target_vol in config.TARGET_VOLATILITIES_FOR_RISK_LEVELS.items():
        # Find the portfolio on the efficient frontier closest to the target volatility
        idx = (efficient_frontier_df['Volatility'] - target_vol).abs().idxmin()
        selected_portfolio_mvo = efficient_frontier_df.loc[idx].copy()

        print(f"Processing Risk {risk_level} (Target Vol: {target_vol:.2%}):")
        print(f"  Selected MVO Portfolio (Vol: {selected_portfolio_mvo['Volatility']:.2%}, Return: {selected_portfolio_mvo['Return']:.2%})...")

        # --- Calculate Max Drawdown for this selected portfolio using simulated_asset_paths ---
        portfolio_weights = selected_portfolio_mvo[asset_names].values

        max_drawdowns_for_this_portfolio_sims = []

        # Iterate through each simulation path
        for sim_idx in range(num_simulations):
            initial_value = 1.0
            portfolio_values = [initial_value]

            # Get and compound monthly returns for this specific simulation run
            for month_idx in range(planning_horizon_months):
                monthly_returns_all_assets = np.array([
                    loaded_sim_paths[asset_name][sim_idx, month_idx]
                    for asset_name in asset_names
                ])

                portfolio_monthly_return = np.sum(monthly_returns_all_assets * portfolio_weights)
                portfolio_values.append(portfolio_values[-1] * (1 + portfolio_monthly_return))

            portfolio_value_series = pd.Series(portfolio_values)
            max_drawdowns_for_this_portfolio_sims.append(calculate_max_drawdown(portfolio_value_series))

        # Get the 1st percentile (worst 1%) of max drawdowns from all simulations for this portfolio
        simulated_1st_percentile_max_drawdown = np.percentile(max_drawdowns_for_this_portfolio_sims, 1)

        # --- Assign Final Risk Level based on Combined Criteria ("Highest Risk Wins") ---

        # Determine risk level based on Volatility (using the actual portfolio volatility)
        vol_risk_level = 0
        actual_volatility = selected_portfolio_mvo['Volatility']
        for r_lvl, defs in config.RISK_BAND_DEFINITIONS.items():
            if actual_volatility >= defs['vol_min'] and actual_volatility < defs['vol_max']:
                vol_risk_level = r_lvl
                break
        if vol_risk_level == 0 and actual_volatility >= config.RISK_BAND_DEFINITIONS[10]['vol_min']: # For highest band
            vol_risk_level = 10
        if vol_risk_level == 0: vol_risk_level = 1 # Default to Risk 1 if lower than all defined bands

        # Determine risk level based on Max Drawdown (using the simulated 1st percentile drawdown)
        dd_risk_level = 0
        actual_max_drawdown = simulated_1st_percentile_max_drawdown
        for r_lvl in sorted(config.RISK_BAND_DEFINITIONS.keys(), reverse=True): # Iterate in reverse for highest risk
            if actual_max_drawdown <= config.RISK_BAND_DEFINITIONS[r_lvl]['dd_max']:
                dd_risk_level = r_lvl
                break
        if dd_risk_level == 0: dd_risk_level = 1 # Default to Risk 1 if less risky than all defined bands

        # The final assigned risk level is the maximum of the two derived levels
        final_assigned_risk_level = max(vol_risk_level, dd_risk_level)

        # Store the results for this model portfolio
        portfolio_data_dict = selected_portfolio_mvo.to_dict()
        portfolio_data_dict['Simulated_1st_Percentile_Max_Drawdown'] = simulated_1st_percentile_max_drawdown
        portfolio_data_dict['Vol_Risk_Level_Assigned'] = vol_risk_level
        portfolio_data_dict['DD_Risk_Level_Assigned'] = dd_risk_level
        portfolio_data_dict['Final_Assigned_Risk_Level'] = final_assigned_risk_level

        final_model_portfolios[risk_level] = portfolio_data_dict

        print(f"  Calculated 1st Percentile Max Drawdown: {simulated_1st_percentile_max_drawdown:.2%}")
        print(f"  Assigned Risk Level (Volatility): {vol_risk_level}")
        print(f"  Assigned Risk Level (Drawdown): {dd_risk_level}")
        print(f"  Final Assigned Risk Level: {final_assigned_risk_level}")
        print("=" * 50)

    # Convert the final_model_portfolios dictionary to a DataFrame for saving/viewing
    model_portfolios_summary_df = pd.DataFrame(final_model_portfolios).T
    model_portfolios_summary_df.index.name = 'Target_Risk_Level'

    print("\n--- Summary of Final Model Portfolios with Assigned Risk Levels ---")
    print(model_portfolios_summary_df[[
        'Volatility', 'Return', 'Simulated_1st_Percentile_Max_Drawdown',
        'Vol_Risk_Level_Assigned', 'DD_Risk_Level_Assigned', 'Final_Assigned_Risk_Level'
    ]].round(4))

    # Save the comprehensive model portfolios data
    model_portfolios_summary_df.to_csv(os.path.join(config.OUTPUT_DATA_DIR, 'final_model_portfolios_with_risk_levels.csv'))
    print(f"\nFinal model portfolios data saved to '{os.path.join(config.OUTPUT_DATA_DIR, 'final_model_portfolios_with_risk_levels.csv')}'.")

    return model_portfolios_summary_df