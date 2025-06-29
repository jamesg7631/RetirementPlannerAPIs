import pandas as pd
import numpy as np
import os
from src import config
from src.simulation import load_simulated_paths
# Note, I have moved the model portfolio from the outputs/filename to outputs/model_portfolios/filename

def load_model_portfolio_weights(term_name:str, risk_level:int, output_data_dir: str, asset_names: list) -> pd.Series:
    """
    Load the asset allocation weights for a chosen model portfolio
    """
    filepath = os.path.join(output_data_dir, f"model_portfolios_{term_name}.csv")
    try:
        model_portfolios_df = pd.read_csv(filepath, index_col='Target_Risk_Level')
        if risk_level not in model_portfolios_df.index:
            raise ValueError(f"Risk level {risk_level} not found for {term_name} in model portfolios.")

        weights = model_portfolios_df.loc[risk_level][asset_names]
        return weights
    except FileNotFoundError:
        print(f"Error: Model portfolios wer not found for {term_name} at {filepath}")
        return pd.Series(0.0, index=asset_names)
    except Exception as e:
        print(f"Error loading model portfolio for {term_name} at {filepath}.")
        return pd.Series(0.0, index=asset_names)

# Quick Calculation. I forget to model inflation but I want to build the rest of the application to get a quick
# prototype. Model inflation and adjust the below later
# Also, the below uses the model portfolios risk 1-10 model portfolios. However, client could have other funds.
# Could do historical bootstrapping using the yahoo finance API of the fund they are invested in.
# Could potentially break the application though if they request a fund which has an unexpected data format.
# Could result in incorrect calc as a currency conversion could be missed.
# Alternatively, could map fund to our asset classes and use that as the below.
def run_client_retirement_simulation(
        initial_balance:float,
        current_age: int,
        retirement_age:int,
        annual_contribution:float,
        annual_withdrawal_at_retirement: float,
        life_expectancy: int, # Will replace with mortality simulations from lifetables later
        selected_risk_level: int,
        selected_term_name: str,
        average_annual_inflation: float = 0.02 # Change this after modelling inflation later
):
    print("--- Starting Retirement Simulation for Client")
    print(f"Profile: Risk {selected_risk_level}, Term {selected_term_name}")
    print(f"Initial Balance: £{initial_balance:,.2f}")

    all_asset_names = [
        t.replace('_monthly_returns_GBP.csv', '').replace('_monthly_returns.csv', '')
        for t in config.USD_ASSETS_TO_CONVERT + [config.MONEYMARKET_GBP_RETURNS_FILE, config.GBP_ASSET_ORIGINAL_FILE]
    ]

    # Might break with last change I made
    portfolio_weights = load_model_portfolio_weights(selected_term_name, selected_risk_level, config.OUTPUT_DATA_DIR,
                                                    all_asset_names)
    if portfolio_weights.sum() == 0.0:
        print("Error: Could not successfully load portfolio weights")
        return [], []

    loaded_sim_paths = load_simulated_paths(all_asset_names, config.SIMULATED_PATHS_DIR)
    monthly_inflation_factor = (1 + average_annual_inflation)**(1/config.NUM_MONTHS_IN_YEAR)

    # Planning horizon calcs
    pre_retirement_months = (retirement_age - current_age) * config.NUM_MONTHS_IN_YEAR
    post_retirement_months = (life_expectancy - retirement_age) * config.NUM_MONTHS_IN_YEAR
    total_planning_months = pre_retirement_months + post_retirement_months

    final_balances = []
    all_portfolio_histories = []

    print(f"Running {config.NUM_SIMULATIONS} simulations over {total_planning_months} months...")

    for i in range(config.NUM_SIMULATIONS):
        if (i + 1) % 100 == 0:
            print(f"Simulation {i + 1}/{config.NUM_SIMULATIONS} complete")

        current_balance = initial_balance
        portfolio_history_current_sim = [initial_balance]
        current_annual_contribution_inflated = annual_contribution
        current_annual_withdrawal_inflated = annual_withdrawal_at_retirement

        # Loop through the total planning horizon, month by month
        for month_in_horizon  in range(total_planning_months):
            sim_month_index = month_in_horizon
            if sim_month_index >= config.PLANNING_HORIZON_MONTHS:
                break
            monthly_returns_all_assets = np.array([
                loaded_sim_paths[asset_name][i,sim_month_index]
                for asset_name in all_asset_names
            ])

            # Calculate portfolio's monthly return
            portfolio_monthly_return = np.sum(monthly_returns_all_assets * portfolio_weights.values)
            current_balance *= (1 + portfolio_monthly_return)

            current_year_in_horizon = month_in_horizon // config.NUM_MONTHS_IN_YEAR

            # Check if it's an annual adjustment point (start of a new year in the horizon)
            if month_in_horizon % config.NUM_MONTHS_IN_YEAR == 0 and month_in_horizon > 0:
                current_annual_contribution_inflated *= (1 + average_annual_inflation)
                current_annual_withdrawal_inflated *= (1 + average_annual_inflation)

            if month_in_horizon < pre_retirement_months:
                current_balance += (current_annual_contribution_inflated / config.NUM_MONTHS_IN_YEAR)
            else:
                current_balance -= (current_annual_withdrawal_inflated / config.NUM_MONTHS_IN_YEAR)

            if current_balance <= 0:
                current_balance = 0
                portfolio_history_current_sim.append(current_balance)
                print(f"Run out of money in year {current_year_in_horizon}!")
                break

            portfolio_history_current_sim.append(current_balance)
        final_balances.append(current_balance)
        all_portfolio_histories.append(portfolio_history_current_sim)

    print("--- Retirement Simulation Complete ---")
    return final_balances, all_portfolio_histories





