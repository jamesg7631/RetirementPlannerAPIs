import pandas as pd
import numpy as np
import os

from src import config
from src.simulation import load_simulated_paths
import time
# Note, I have moved the model portfolio from the outputs/filename to outputs/model_portfolios/filename

# Could Maybe divide into smaller classes later
# Could also perhaps use dob instead of current age
class RetirementSimulatorModelPortfolios:
    def __init__(self, current_age:int, retirement_age: int, initial_balance, life_expectancy, risk_level:int, output_data_dir:str, asset_names:list):
        self.current_age = current_age
        self.retirement_age = retirement_age
        self.initial_balance = initial_balance
        self.life_expectancy = life_expectancy
        # self.term_name = term_name
        # self.risk_level = risk_level
        self.output_data_dir = output_data_dir
        self.asset_names = asset_names
        self.all_sim_names = self.asset_names.copy()
        self.all_sim_names.append(config.INFLATION_COLUMN_NAME)
        self.load_model_portfolio_weights(risk_level)
        self.loaded_sim_paths = load_simulated_paths(self.all_sim_names, config.SIMULATED_PATHS_DIR) # Don't understand why I am getting a warning. Pay close attention when running in debug mode
        print()

    def get_term_name(self):
        term_name = ""
        investment_horizon = self.life_expectancy - self.current_age
        for term in reversed(config.TIME_HORIZON_LOOKBACK_YEARS):
            year = config.TIME_HORIZON_LOOKBACK_YEARS[term]
            if year is None:
                term_name = term
            elif investment_horizon < year:
                term_name = term

        return term_name


    def load_model_portfolio_weights(self, risk_level:int) ->None:
        term_name = self.get_term_name()
        filepath = os.path.join(self.output_data_dir, f"model_portfolios_{term_name}.csv")
        try:
            model_portfolios_df = pd.read_csv(filepath, index_col='Target_Risk_Level')
            if risk_level not in model_portfolios_df.index:
                raise ValueError(f"Risk level {risk_level} not found for {term_name} in model portfolios.")

            self.model_portfolio_weights = model_portfolios_df.loc[risk_level][self.asset_names]
            print(f"Portfolio weights sum to {self.model_portfolio_weights.sum()}")
        except FileNotFoundError:
            print(f"Error: Model portfolios wer not found for {term_name} at {filepath}")
            self.model_portfolio_weights = pd.Series(0.0, index=self.asset_names)
        except Exception as e:
            print(f"Error loading model portfolio for {term_name} at {filepath}.")
            self.model_portfolio_weights = pd.Series(0.0, index=self.asset_names)

    def run_client_retirement_simulation(self, contribution_amount, initial_balance, withdrawal_amount:float):
        start_time = time.perf_counter()

        pre_retirement_months = (self.retirement_age - self.current_age) * 12
        post_retirement_months = (self.life_expectancy - self.retirement_age) * 12
        # total_planning_months = pre_retirement_months + post_retirement_months
        all_portfolio_histories =[]

        for current_sim_number in range(config.NUM_SIMULATIONS):
            # if (current_sim_number + 1) % 100 == 0:
            #     print(f"Running {config.NUM_SIMULATIONS} simulation over {total_planning_months}")
            pf_history_current_sim = self.constant_nominal_contribution(contribution_amount, initial_balance, current_sim_number, pre_retirement_months)
            pf_history_current_sim = self.constant_nominal_withdrawal(withdrawal_amount, pf_history_current_sim, current_sim_number, pre_retirement_months, post_retirement_months)
            all_portfolio_histories.append(pf_history_current_sim)


        end_time = time.perf_counter()
        duration = end_time - start_time
        print(f"Execution time: {duration:.6f} seconds")

        return all_portfolio_histories

    # --- Contribution Strategies ---
    def constant_nominal_contribution(self, contribution_amount, initial_balance, simulation_number:int, pre_retirement_months: int):
        current_balance = initial_balance
        portfolio_history_current_sim = [initial_balance]
        weights = self.model_portfolio_weights.values.reshape(-1, 1)
        sim_returns_pre_retirement = np.array([
            self.loaded_sim_paths[asset_name][simulation_number, :pre_retirement_months]
            for asset_name in self.asset_names
        ])
        portfolio_monthly_returns = (weights.T @ sim_returns_pre_retirement).flatten()

        for month_in_horizon in range(pre_retirement_months):
            sim_month_index = month_in_horizon
            if sim_month_index >= config.PLANNING_HORIZON_MONTHS:
                break
                ### Come back to this
            monthly_returns_all_assets = np.array([
                self.loaded_sim_paths[asset_name][simulation_number,sim_month_index]
                for asset_name in self.asset_names
            ])


        # Get the pre-calculated portfolio return for the current month
        portfolio_monthly_return = portfolio_monthly_returns[month_in_horizon]

        # Update the balance sequentiall
        current_balance = (current_balance * (1 + portfolio_monthly_return)) + contribution_amount
        portfolio_history_current_sim.append(current_balance)

        return portfolio_history_current_sim

    # --- Withdrawal Strategies
    def constant_nominal_withdrawal(self, withdrawal_amount, portfolio_history_current_sim:list, simulation_number:int, pre_retirement_months, post_retirement_months):
        current_balance = portfolio_history_current_sim[-1]
        for month_in_horizon in range(post_retirement_months):
            real_current_month = month_in_horizon + pre_retirement_months
            if real_current_month >= config.PLANNING_HORIZON_MONTHS:
                break
            monthly_returns_all_assets = np.array([
                self.loaded_sim_paths[asset_name][simulation_number, real_current_month]
                for asset_name in self.asset_names
            ])
            portfolio_monthly_return = np.sum(monthly_returns_all_assets * self.model_portfolio_weights.values)
            current_balance = (current_balance * (1 + portfolio_monthly_return)) - withdrawal_amount
            portfolio_history_current_sim.append(current_balance)

        return portfolio_history_current_sim

if __name__ == "__main__":
    all_asset_names = [
        t.replace('_monthly_returns_GBP.csv', '').replace('_monthly_returns.csv', '')
        for t in config.USD_ASSETS_TO_CONVERT + [config.MONEYMARKET_GBP_RETURNS_FILE, config.GBP_ASSET_ORIGINAL_FILE]
    ]
    ret_planner = RetirementSimulatorModelPortfolios(25, 67,
                                                     100000, 77, 1, config.OUTPUT_DATA_DIR, all_asset_names)

    ret_planner.run_client_retirement_simulation(500, 100000, 500)
    print()