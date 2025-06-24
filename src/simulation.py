import pandas as pd
import numpy as np
import os
from src import config
from src.data_processing import consolidate_gbp_returns # Import the function to get combined data

def run_historical_bootstrapping(combined_returns_df: pd.DataFrame):
    """
    Performs historical bootstrapping Monte Carlo simulations and saves asset paths.
    """
    asset_names = combined_returns_df.columns.tolist()
    num_historical_months = len(combined_returns_df)

    if num_historical_months == 0:
        print("Error: No historical data available for bootstrapping. Skipping simulation.")
        return

    if num_historical_months < config.PLANNING_HORIZON_MONTHS:
        print(f"\nWarning: Number of historical months ({num_historical_months}) is less than the planning horizon in months ({config.PLANNING_HORIZON_MONTHS}).")
        print("This means some simulated paths will reuse historical months more frequently than others.")

    print(f"\n--- Running {config.NUM_SIMULATIONS} Monte Carlo Simulations ({config.PLANNING_HORIZON_YEARS} years horizon) ---")
    print("Using Historical Bootstrapping method...")

    simulated_asset_paths = {col: [] for col in asset_names}

    for s in range(config.NUM_SIMULATIONS):
        if (s + 1) % 1000 == 0:
            print(f"Simulations complete: {s + 1} / {config.NUM_SIMULATIONS}")

        current_sim_returns_for_assets = {col: [] for col in asset_names}

        for month_idx in range(config.PLANNING_HORIZON_MONTHS):
            random_index = np.random.randint(0, num_historical_months)
            historical_returns_this_month = combined_returns_df.iloc[random_index]

            for asset_name, return_val in historical_returns_this_month.items():
                current_sim_returns_for_assets[asset_name].append(return_val)

        for asset_name in asset_names:
            simulated_asset_paths[asset_name].append(current_sim_returns_for_assets[asset_name])

    print("\n--- Monte Carlo Simulation Complete ---")

    # Verify and Save Simulated Data
    print("\n--- Verifying and Saving Simulated Data ---")
    os.makedirs(config.SIMULATED_PATHS_DIR, exist_ok=True)

    for asset_name, paths in simulated_asset_paths.items():
        data_array = np.array(paths)
        np.save(os.path.join(config.SIMULATED_PATHS_DIR, f"{asset_name}_simulated_returns.npy"), data_array)
        print(f"Asset '{asset_name}': Shape of simulated paths is {data_array.shape} (Simulations x Months)")

    print(f"\nAll simulated asset paths saved to the '{config.SIMULATED_PATHS_DIR}' folder.")

def load_simulated_paths(asset_names: list, simulated_paths_dir: str):
    """
    Loads simulated asset paths from .npy files.
    """
    loaded_paths = {}
    print(f"\n--- Loading Simulated Paths from '{simulated_paths_dir}' ---")
    for asset_name in asset_names:
        file_path = os.path.join(simulated_paths_dir, f"{asset_name}_simulated_returns.npy")
        try:
            loaded_paths[asset_name] = np.load(file_path)
            print(f"Loaded {asset_name}: {loaded_paths[asset_name].shape}")
        except FileNotFoundError:
            print(f"Error: Simulated path file not found for {asset_name} at {file_path}. Skipping.")
        except Exception as e:
            print(f"An error occurred loading {asset_name}: {e}")
    return loaded_paths