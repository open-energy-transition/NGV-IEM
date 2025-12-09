import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

df_sq = pd.read_csv(snakemake.input.metrics_sq, index_col=0)
df_iem = pd.read_csv(snakemake.input.metrics_iem, index_col=0)


# 2. Drop the unwanted column
# axis=1 tells pandas to look in columns, not rows
column_to_drop = 'Total annual congestion income [€]'

# Check if it exists before dropping to avoid errors if the file format changes
if column_to_drop in df_sq.columns:
    df_sq = df_sq.drop(column_to_drop, axis=1)
if column_to_drop in df_iem.columns:
    df_iem = df_iem.drop(column_to_drop, axis=1)

df_diff = df_iem - df_sq

# 3. Create the Subplots
# nrows=3, ncols=1 creates a vertical stack
# sharex=True means they all share the same X-axis labels (cleaner look)
fig, axes = plt.subplots(nrows=3, ncols=1, figsize=(10, 12), sharex=True)

# Define columns and colors for each plot
variables = df_diff.columns
colors = ['#1f77b4', '#ff7f0e', '#2ca02c']  # Blue, Orange, Green

# Loop through each variable and plot it on its own axis
for i, var in enumerate(variables):
    ax = axes[i]

    # Plot the bar chart
    sns.barplot(
        x=df_diff.index,
        y=df_diff[var],
        ax=ax,
        color=colors[i],
        edgecolor='black',
        alpha=0.8
    )

    # Add a horizontal zero line (crucial for difference plots)
    ax.axhline(0, color='black', linewidth=1.5)

    # Styling
    ax.set_title(f'Change in {var}', fontsize=14, fontweight='bold')
    ax.set_ylabel('Difference')
    ax.grid(True, axis='y', linestyle='--', alpha=0.5)

# Only add the X-label to the bottom plot
axes[-1].set_xlabel('Interconnector', fontsize=14, fontweight='bold')
axes[-1].tick_params(axis='x', rotation=45)  # Rotate labels if needed

plt.tight_layout()
plt.savefig(snakemake.output[0])
