# src/retirement_planner.py

import pandas as pd
import numpy as np
import os
from src import config
from src.simulation import load_simulated_paths

def load_model_portfolio_weights(term_name: str, risk_level: int, output_data_dir: str, asset_names: list) -> pd.Series:
    """
    Loads the asset allocation weights for a specific model portfolio.
    """
    filepath = os.path.join(output_data_dir, f'model_portfolios_{term_name}.csv')
    try:
        model_portfolios_df = pd.read_csv(filepath, index_col='Target_Risk_Level')
        if risk_level not in model_portfolios_df.index:
            raise ValueError(f"Risk level {risk_level} not found for {term_name} in model portfolios.")

        # Extract weights for the specified risk level
        weights = model_portfolios_df.loc[risk_level][asset_names]
        # Ensure weights sum to 1 (or very close) due to potential float inaccuracies
        weights = weights / weights.sum()
        return weights
    except FileNotFoundError:
        print(f"Error: Model portfolios file not found for {term_name} at {filepath}.")
        return pd.Series(0.0, index=asset_names) # Return zero weights if not found
    except Exception as e:
        print(f"Error loading model portfolio for {term_name}, Risk {risk_level}: {e}")
        return pd.Series(0.0, index=asset_names)

def run_client_retirement_simulation(
        initial_balance: float,
        current_age: int,
        retirement_age: int,
        annual_contribution: float,
        annual_withdrawal_at_retirement: float, # This is the target spending power at retirement
        life_expectancy: int,
        selected_risk_level: int,
        selected_term_name: str,
        average_annual_inflation: float = 0.02 # Example fixed inflation rate (2%)
):
    """
    Runs Monte Carlo simulations for a specific client's retirement plan.

    Args:
        initial_balance (float): Starting portfolio value.
        current_age (int): Client's current age.
        retirement_age (int): Client's target retirement age.
        annual_contribution (float): Amount client plans to save annually (pre-retirement).
        annual_withdrawal_at_retirement (float): Target annual spending in retirement (at retirement age, inflated).
        life_expectancy (int): Age up to which to simulate (end of retirement).
        selected_risk_level (int): Client's chosen risk level (1-10).
        selected_term_name (str): The term/time horizon used for MVO (e.g., "21_plus_year").
        average_annual_inflation (float): Assumed constant annual inflation rate.

    Returns:
        list: A list of final portfolio balances (or 0 if ran out of money) for each simulation.
        list: A list of lists, where each inner list is the portfolio balance history for one simulation.
    """
    print(f"\n--- Starting Retirement Simulation for Client ---")
    print(f"Profile: Risk {selected_risk_level}, Term {selected_term_name}")
    print(f"Initial Balance: £{initial_balance:,.2f}")

    # 1. Load relevant model portfolio weights
    # Asset names are needed to correctly map weights. We can get them from config or combined_returns_df.
    # For robust lookup, assume all asset names for simulation are the same as used for MVO.
    all_asset_names = [
        t.replace('_monthly_returns_GBP.csv', '').replace('_monthly_returns.csv', '')
        for t in config.USD_ASSETS_TO_CONVERT + [config.MONEYMARKET_GBP_RETURNS_FILE, config.GBP_ASSET_ORIGINAL_FILE]
    ]

    portfolio_weights = load_model_portfolio_weights(
        selected_term_name, selected_risk_level, config.OUTPUT_DATA_DIR, all_asset_names
    )
    if portfolio_weights.sum() == 0.0: # Check if loading failed
        print("Error: Could not load valid portfolio weights. Exiting simulation.")
        return [], []

    # 2. Load all simulated asset paths
    loaded_sim_paths = load_simulated_paths(all_asset_names, config.SIMULATED_PATHS_DIR)
    if not loaded_sim_paths:
        print("Error: Simulated asset paths not loaded. Exiting simulation.")
        return [], []

    # Convert annual inflation to monthly factor
    monthly_inflation_factor = (1 + average_annual_inflation)**(1/config.NUM_MONTHS_IN_YEAR)

    # Calculate total planning horizon in months
    pre_retirement_months = (retirement_age - current_age) * config.NUM_MONTHS_IN_YEAR
    post_retirement_months = (life_expectancy - retirement_age) * config.NUM_MONTHS_IN_YEAR
    total_planning_months = pre_retirement_months + post_retirement_months

    # Store results
    final_balances = []
    all_portfolio_histories = [] # To store the path of portfolio values for each simulation

    print(f"Running {config.NUM_SIMULATIONS} simulations over {total_planning_months} months...")

    # For each simulation run
    for s_idx in range(config.NUM_SIMULATIONS):
        if (s_idx + 1) % 100 == 0: # Print progress every 100 simulations
            print(f"  Simulation {s_idx + 1}/{config.NUM_SIMULATIONS} complete.")

        current_balance = initial_balance
        portfolio_history_this_sim = [initial_balance] # Track balance over time

        current_annual_contribution_inflated = annual_contribution
        current_annual_withdrawal_inflated = annual_withdrawal_at_retirement

        # Loop through the total planning horizon, month by month
        for month_in_horizon in range(total_planning_months):
            # Calculate current month's simulated returns for all assets
            # Need to pick the correct month_idx from the 900-month simulation path
            sim_month_idx = month_in_horizon # Simple mapping: month 0 of planning = month 0 of sim path

            # Ensure sim_month_idx does not exceed loaded sim path length (900 months)
            if sim_month_idx >= config.PLANNING_HORIZON_MONTHS:
                # If planning horizon is longer than simulation horizon, assume zero growth or extend.
                # For simplicity here, we'll assume it runs out or stagnates.
                # In a real app, you'd likely project based on averages or warn.
                break # Stop this simulation if planning horizon exceeds simulated data

            monthly_returns_all_assets = np.array([
                loaded_sim_paths[asset_name][s_idx, sim_month_idx]
                for asset_name in all_asset_names
            ])

            # Calculate portfolio's monthly return
            portfolio_monthly_return = np.sum(monthly_returns_all_assets * portfolio_weights.values)
            current_balance *= (1 + portfolio_monthly_return)

            # Apply contributions/withdrawals (monthly, adjusted by inflation annually)
            current_year_in_horizon = month_in_horizon // config.NUM_MONTHS_IN_YEAR

            # Check if it's an annual adjustment point (start of a new year in the horizon)
            if month_in_horizon % config.NUM_MONTHS_IN_YEAR == 0 and month_in_horizon > 0:
                current_annual_contribution_inflated *= (1 + average_annual_inflation)
                current_annual_withdrawal_inflated *= (1 + average_annual_inflation)

            # Apply cash flows based on phase (pre-retirement vs. post-retirement)
            if month_in_horizon < pre_retirement_months:
                # Accumulation Phase
                current_balance += (current_annual_contribution_inflated / config.NUM_MONTHS_IN_YEAR)
            else:
                # Withdrawal Phase (in retirement)
                current_balance -= (current_annual_withdrawal_inflated / config.NUM_MONTHS_IN_YEAR)

            # Check for portfolio failure (ran out of money)
            if current_balance <= 0:
                current_balance = 0
                portfolio_history_this_sim.append(current_balance) # Record failure
                break # End this simulation run

            portfolio_history_this_sim.append(current_balance)

        final_balances.append(current_balance)
        all_portfolio_histories.append(portfolio_history_this_sim)

    print("--- Retirement Simulation Complete ---")
    return final_balances, all_portfolio_histories