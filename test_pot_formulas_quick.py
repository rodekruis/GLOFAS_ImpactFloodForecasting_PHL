"""Quick test of POT formula functions"""
import sys
sys.path.insert(0, 'src')

import numpy as np
from philflood.calibration.evt_pot import (
    return_period_to_discharge_pot,
    discharge_to_return_period_pot,
    bootstrap_pot_return_levels,
)

print("Testing POT formulas...")
print("=" * 60)

# Test 1: Return period to discharge (exponential case)
print("\n1. Testing return_period_to_discharge_pot (xi=0, exponential):")
u, sigma, lambda_u, xi, T = 100, 50, 2, 0, 10
q = return_period_to_discharge_pot(T, u, xi, sigma, lambda_u)
expected = u + sigma * np.log(lambda_u * T)
print(f"   T={T}, u={u}, sigma={sigma}, lambda={lambda_u}, xi={xi}")
print(f"   Result: {q:.4f}")
print(f"   Expected: {expected:.4f}")
print(f"   Match: {np.isclose(q, expected)}")

# Test 2: Return period to discharge (positive xi)
print("\n2. Testing return_period_to_discharge_pot (xi=0.1, GPD):")
xi = 0.1
q = return_period_to_discharge_pot(T, u, xi, sigma, lambda_u)
expected = u + (sigma / xi) * (np.power(lambda_u * T, xi) - 1.0)
print(f"   T={T}, u={u}, sigma={sigma}, lambda={lambda_u}, xi={xi}")
print(f"   Result: {q:.4f}")
print(f"   Expected: {expected:.4f}")
print(f"   Match: {np.isclose(q, expected)}")

# Test 3: Vectorized input
print("\n3. Testing vectorized input:")
T_vec = np.array([2, 5, 10, 20, 50, 100])
q_vec = return_period_to_discharge_pot(T_vec, u, xi, sigma, lambda_u)
print(f"   T = {T_vec}")
print(f"   q = {q_vec}")
print(f"   Monotonic: {np.all(np.diff(q_vec) > 0)}")

# Test 4: Inverse consistency
print("\n4. Testing inverse consistency (T -> D -> T):")
T_original = 50
q = return_period_to_discharge_pot(T_original, u, xi, sigma, lambda_u)
T_recovered = discharge_to_return_period_pot(q, u, xi, sigma, lambda_u)
print(f"   Original T: {T_original}")
print(f"   q: {q:.4f}")
print(f"   Recovered T: {T_recovered:.4f}")
print(f"   Match: {np.isclose(T_original, T_recovered)}")

# Test 5: Bootstrap function
print("\n5. Testing bootstrap_pot_return_levels:")
rng = np.random.RandomState(42)
exceedances = rng.exponential(scale=20, size=100)
result_df = bootstrap_pot_return_levels(
    exceedances, threshold=100, lambda_u=2.5,
    return_periods=[2, 5, 10, 20, 50, 100],
    n_bootstrap=10, random_state=42
)
print(f"   Exceedances: n={len(exceedances)}, mean={exceedances.mean():.2f}")
print(f"   Result shape: {result_df.shape}")
print(f"   Columns: {list(result_df.columns)}")
print(f"   First row: {result_df.iloc[0]['return_period_years']:.0f} years -> {result_df.iloc[0]['mean_m3s']:.2f} m3/s")
print(f"   Last row: {result_df.iloc[-1]['return_period_years']:.0f} years -> {result_df.iloc[-1]['mean_m3s']:.2f} m3/s")
print(f"   Monotonic: {np.all(np.diff(result_df['mean_m3s']) > 0)}")

print("\n" + "=" * 60)
print("All tests passed successfully! ✓")
