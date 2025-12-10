import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

targetdir = '/Users/tpa/MyProjects/NGV-IEM/results/draft_report/tables/netflow_timeseries_status_quo_2030.csv'
targetdir2 = '/Users/tpa/MyProjects/NGV-IEM/results/draft_report/tables/price_difference_timeseries_status_quo_2030.csv'

df_netflow = pd.read_csv(targetdir, index_col=0)
df_price_diff= pd.read_csv(targetdir2, index_col=0)

#df_netflow = pd.read_csv(snakemake.input.nf_sq, index_col=0)
#df_price_diff = pd.read_csv(snakemake.input.pd_sq, index_col=0)

# Select interconnection
intercon = "GB00-FR00"

# TODO change filtering, to be done based on selected intercon

data = pd.DataFrame({
    'Price Difference [€/MWh]': df_price_diff[intercon],
    'Flow [MW]': df_netflow[intercon]
})

# 2. Outlier Removal Logic (The Quantile Method)
# We calculate the 1st and 99th percentiles.
# Anything outside this range is considered an outlier.

# Calculate limits for Price
p_low = data['Price Difference [€/MWh]'].quantile(0.01)
p_high = data['Price Difference [€/MWh]'].quantile(0.99)


# Create a "Mask" (True/False list) for valid data
mask = (
    (data['Price Difference [€/MWh]'] >= p_low) &
    (data['Price Difference [€/MWh]'] <= p_high)
)

# Apply the filter
data_clean = data[mask]

print(f"Original points: {len(data)}, Points after filtering: {len(data_clean)}")

'''
# Alternative - Set threshold
data_clean = data[
    (data['Price Difference [€/MWh]'] < 500) &
    (data['Price Difference [€/MWh]'] > -500)
]
'''
# 3. Plotting
plt.figure(figsize=(10, 10))  # Square figure is best for parity plots
sns.set_context("talk")

# The Scatter Plot
sns.scatterplot(
    data=data_clean,
    x='Price Difference [€/MWh]',
    y='Flow [MW]',
    s=100,  # Size of dots
    alpha=0.7,  # Transparency (helps if dots overlap)
    edgecolor='black'  # distinct borders
)

max_abs_val = max(
    abs(data_clean['Price Difference [€/MWh]'].min()),
    abs(data_clean['Price Difference [€/MWh]'].max())
)

# 2. Add a little "padding" (e.g., 10%) so points aren't crushed against the edge
limit = max_abs_val * 1.1

# 3. Apply the limits
plt.xlim(-limit, limit)
plt.title(f'Interconnector: {intercon}')
plt.savefig('interconnector.pdf', bbox_inches='tight')
plt.show()