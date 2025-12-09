import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

#targetdir = '/Users/tpa/MyProjects/NGV-IEM/results/draft_report/tables/congestion_income_metrics_status_quo.csv'
#targetdir2 = '/Users/tpa/MyProjects/NGV-IEM/results/draft_report/tables/congestion_income_metrics_iem.csv'

#df_sq = pd.read_csv(targetdir, index_col=0)
#df_iem = pd.read_csv(targetdir2, index_col=0)

df_sq = pd.read_csv(snakemake.input.metrics_sq, index_col=0)
df_iem = pd.read_csv(snakemake.input.metrics_iem, index_col=0)

# Select interconnection
intercon = "GB00-BE00"

data = pd.DataFrame({
        'Status_Quo': df_sq[intercon], # Adjust column selection if needed
        'IEM': df_iem[intercon]
    })

# Calculate limits for Price
ci_low = data.quantile(0.01)
ci_high = data.quantile(0.99)


# Create a "Mask" (True/False list) for valid data
mask = (
    (data >= ci_low) &
    (data <= ci_high)
)

# Apply the filter
data_clean = data[mask]

# 3. Plotting
plt.figure(figsize=(10, 10))  # Square figure is best for parity plots
sns.set_context("talk")

# The Scatter Plot
sns.scatterplot(
    data=data_clean,
    x='Status_Quo',
    y='IEM',
    s=100,  # Size of dots
    alpha=0.7,  # Transparency (helps if dots overlap)
    edgecolor='black'  # distinct borders
)


# 4. Add the 45-degree "No Change" Line
# We find the min and max values to know where to draw the line
limit_min = min(data_clean.min())
limit_max = max(data_clean.max())

# Draw a dashed diagonal line
plt.plot([limit_min, limit_max], [limit_min, limit_max],
         color='red', linestyle='--', linewidth=2, label='No Change (y=x)')
'''
for idx, row in data.iterrows():
        # Simple Euclidean distance from the line, or just large absolute difference
        diff = abs(row['IEM'] - row['Status_Quo'])
        if diff > 100000: # Threshold: Only label if difference is huge (adjust this number!)
            plt.text(row['Status_Quo'], row['IEM'], idx,
                     fontsize=9, ha='right', va='bottom')

'''

# 6. Style
plt.xlabel('Explicit Allocation')
plt.ylabel('Implicit Allocation')
#plt.legend()
plt.grid(True, linestyle='--', alpha=0.3)

# Make axes equal so the 45-degree line looks actually 45 degrees
plt.axis('square')

plt.tight_layout()

plt.savefig(snakemake.output[0])