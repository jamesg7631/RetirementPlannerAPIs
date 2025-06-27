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

def get_target_volatilities_for_risk_level_by_term(risk_band_definitions_by_term: dict):
    target_volatilities = {}

    for term, band_entry in risk_band_definitions_by_term.items():
        target_volatilities[term] = {}
        for risk_level, volatilities in band_entry:
            min_vol = volatilities["min_vol"]
            max_vol = volatilities["max_vol"]
            mid_band_vol = (max_vol - min_vol) / 2
            target_volatilities[risk_level] = mid_band_vol

def define_and_select_model_portfolios_by_term(all_term_results: dict):
    """
    Defines risk bands and identifies model portfolios for each time horizon.
    Calculates their simulated maximum drawdowns.
    """
    if not all_term_results:
        print("Error: No portfolio analysis results provided. Cannot define model portfolios.")
        return {}

    all_term_model_portfolios = {} # To store the final model portfolio DataFrames by term

    for term_name, term_data in all_term_results.items():
        print(f"\n===== Defining Model Portfolios for {term_name} term =====")
        efficient_frontier_df = term_data['efficient_frontier_df']

        if efficient_frontier_df.empty:
            print(f"Skipping {term_name}: Efficient Frontier DataFrame is empty.")
            continue

        # Asset names from the efficient frontier columns (excluding metrics)
        asset_names = [col for col in efficient_frontier_df.columns if col not in ['Volatility', 'Return', 'Sharpe_Ratio']]

        # Load simulated paths (needed for drawdown calculation)
        # Assuming your simulated_paths_folder contains paths generated from the *full* history,
        # as usually, simulations are based on the longest available data.
        loaded_sim_paths = load_simulated_paths(asset_names, config.SIMULATED_PATHS_DIR)
        if not loaded_sim_paths:
            print(f"Error: Simulated paths not loaded for {term_name}. Cannot calculate max drawdowns for this term.")
            continue # Skip to next term if sim data isn't there

        num_simulations = loaded_sim_paths[asset_names[0]].shape[0]
        planning_horizon_months = loaded_sim_paths[asset_names[0]].shape[1]

        final_model_portfolios_for_term = {}

        # Get term-specific risk band definitions and target volatilities
        term_risk_bands = config.RISK_BAND_DEFINITIONS_BY_TERM.get(term_name)
        term_target_vols = get_target_volatilities_for_risk_level_by_term(term_name)

        if not term_risk_bands or not term_target_vols:
            print(f"Error: Risk band definitions or target volatilities not found for term '{term_name}'. Skipping.")
            continue


        # Iterate through each desired risk level based on target volatilities
        for risk_level in sorted(term_target_vols.keys()):
            target_vol = term_target_vols[risk_level]

            # Find the portfolio on the efficient frontier closest to the target volatility
            idx = (efficient_frontier_df['Volatility'] - target_vol).abs().idxmin()
            selected_portfolio_mvo = efficient_frontier_df.loc[idx].copy()

            print(f"Processing Risk {risk_level} (Target Vol: {target_vol:.2%}):")
            print(f"  Selected MVO Portfolio (Vol: {selected_portfolio_mvo['Volatility']:.2%}, Return: {selected_portfolio_mvo['Return']:.2%})...")

            # --- Calculate Max Drawdown for this selected portfolio using simulated_asset_paths ---
            portfolio_weights = selected_portfolio_mvo[asset_names].values

            max_drawdowns_for_this_portfolio_sims = []

            for sim_idx in range(num_simulations):
                initial_value = 1.0
                portfolio_values = [initial_value]

                for month_idx in range(planning_horizon_months):
                    monthly_returns_all_assets = np.array([
                        loaded_sim_paths[asset_name][sim_idx, month_idx]
                        for asset_name in asset_names
                    ])

                    portfolio_monthly_return = np.sum(monthly_returns_all_assets * portfolio_weights)
                    portfolio_values.append(portfolio_values[-1] * (1 + portfolio_monthly_return))

                portfolio_value_series = pd.Series(portfolio_values)
                max_drawdowns_for_this_portfolio_sims.append(calculate_max_drawdown(portfolio_value_series))

            simulated_1st_percentile_max_drawdown = np.percentile(max_drawdowns_for_this_portfolio_sims, 1)

            # --- Assign Final Risk Level based on Combined Criteria ("Highest Risk Wins") ---

            vol_risk_level = 0
            actual_volatility = selected_portfolio_mvo['Volatility']
            for r_lvl, defs in term_risk_bands.items():
                if actual_volatility >= defs['vol_min'] and actual_volatility < defs['vol_max']:
                    vol_risk_level = r_lvl
                    break
            if vol_risk_level == 0 and actual_volatility >= term_risk_bands[10]['vol_min']:
                vol_risk_level = 10
            if vol_risk_level == 0: vol_risk_level = 1

            dd_risk_level = 0
            actual_max_drawdown = simulated_1st_percentile_max_drawdown
            for r_lvl in sorted(term_risk_bands.keys(), reverse=True):
                if actual_max_drawdown <= term_risk_bands[r_lvl]['dd_max']:
                    dd_risk_level = r_lvl
                    break
            if dd_risk_level == 0: dd_risk_level = 1

            final_assigned_risk_level = max(vol_risk_level, dd_risk_level)

            portfolio_data_dict = selected_portfolio_mvo.to_dict()
            portfolio_data_dict['Simulated_1st_Percentile_Max_Drawdown'] = simulated_1st_percentile_max_drawdown
            portfolio_data_dict['Vol_Risk_Level_Assigned'] = vol_risk_level
            portfolio_data_dict['DD_Risk_Level_Assigned'] = dd_risk_level
            portfolio_data_dict['Final_Assigned_Risk_Level'] = final_assigned_risk_level

            final_model_portfolios_for_term[risk_level] = portfolio_data_dict

            print(f"  Calculated 1st Percentile Max Drawdown: {simulated_1st_percentile_max_drawdown:.2%}")
            print(f"  Assigned Risk Level (Volatility): {vol_risk_level}")
            print(f"  Assigned Risk Level (Drawdown): {dd_risk_level}")
            print(f"  Final Assigned Risk Level: {final_assigned_risk_level}")
            print("=" * 50)

        model_portfolios_summary_df = pd.DataFrame(final_model_portfolios_for_term).T
        model_portfolios_summary_df.index.name = 'Target_Risk_Level'

        print(f"\n--- Summary of Final Model Portfolios for {term_name} ---")
        print(model_portfolios_summary_df[[
            'Volatility', 'Return', 'Simulated_1st_Percentile_Max_Drawdown',
            'Vol_Risk_Level_Assigned', 'DD_Risk_Level_Assigned', 'Final_Assigned_Risk_Level'
        ]].round(4))

        # Save to a term-specific file
        output_filepath = os.path.join(config.OUTPUT_DATA_DIR, f'model_portfolios_{term_name}.csv')
        model_portfolios_summary_df.to_csv(output_filepath)
        print(f"Model portfolios for {term_name} saved to '{output_filepath}'.")

        all_term_model_portfolios[term_name] = model_portfolios_summary_df # Store for overall return

    print("\n--- All Model Portfolios by Term Defined ---")
    return all_term_model_portfolios