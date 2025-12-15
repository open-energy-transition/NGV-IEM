import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick # For nice % formatting



######### IMPORTANT ############## (scaling issues)
# Should decide if results will be aggregated for whole rest of EU or only the neighbors.
# Should decide if the absolute results will be presented or only the relative change or the absolute difference

# Current implementation: GB neighbors and relative change (better scaling?) (inconsistent with consumer surplus change)

# Load Data
df_sq = pd.read_csv(snakemake.input.sq, index_col=0)
df_iem = pd.read_csv(snakemake.input.iem, index_col=0)

# Calculate difference in Producer surplus
df_diff = df_iem - df_sq  #using status quo as reference

df_diff.to_csv(snakemake.output[0])

# Ensure the column has a consistent name for processing
# (Assuming the first column contains the OPEX data)
opex_col_sq = df_sq.columns[0]
opex_col_iem = df_iem.columns[0]


def aggregate_rest_of_eu(df, value_col, target, rest_label, total_label):
    """
    Aggregates: Target Zone, Rest of EU (Total - Target), and Total System
    """
    # 1. Get Target (GB00)
    if target in df.index:
        val_target = df.loc[target, value_col]
    else:
        val_target = 0
        print(f"Warning: {target} not found in dataframe.")

    # 2. Get Rest of EU (Everything EXCEPT Target)
    # We drop the target zone and sum the entire remaining dataframe column
    val_rest = df.drop(index=target, errors='ignore')[value_col].sum()

    # 3. Get Total System (Sum of EVERYTHING)
    val_total = df[value_col].sum()

    return pd.Series({
        target: val_target,
        rest_label: val_rest,
        total_label: val_total
    })

# Define who is the "Main" zone and who are the "Neighbors"
target_zone = 'GB00'
rest_eu_label = 'Rest of EU'
total_label = 'Total System'

# Apply the function
agg_sq = aggregate_rest_of_eu(df_sq, opex_col_sq, target_zone, rest_eu_label, total_label)
agg_iem = aggregate_rest_of_eu(df_iem, opex_col_iem, target_zone, rest_eu_label, total_label)

# --- 3. Calculate Percentage Change ---
# Formula: (New - Old) / Old * 100
pct_change = ((agg_iem - agg_sq) / agg_sq) * 100
df_plot = pct_change.reset_index()
df_plot.columns = ['Zone', 'Change (%)']

# --- 4. Plotting ---
plt.figure(figsize=(8, 6))
sns.set_context("talk")

# Define conditional colors (Red if cost increases, Green if decreases)
# You can stick to one color if you prefer (e.g., color='skyblue')
colors = ['#d62728' if x > 0 else '#2ca02c' for x in df_plot['Change (%)']]

ax = sns.barplot(
    data=df_plot,
    x='Zone',
    y='Change (%)',
    palette=colors,
    edgecolor='black'
)

# --- 5. Formatting ---
plt.title('Relative Change in OPEX (IEM vs Status Quo)')
plt.ylabel('Change in Cost')
plt.xlabel('')

# Add a zero line
plt.axhline(0, color='black', linewidth=1.5)

# Format Y-axis as percentages (e.g., "5%")
ax.yaxis.set_major_formatter(mtick.PercentFormatter())

# Add value labels on top of bars
for i, v in enumerate(df_plot['Change (%)']):
    # Position text slightly above or below bar depending on sign
    offset = 0.5 if v >= 0 else -1.5
    ax.text(i, v + offset, f"{v:+.1f}%", ha='center', fontweight='bold', fontsize=12)

plt.grid(True, axis='y', linestyle='--', alpha=0.3)
plt.tight_layout()

plt.savefig(snakemake.output[1])


''' # Code below to present absolute results (bad in terms of scaling)
# --- 4. Combine for Plotting ---
# We create a new DataFrame suitable for Seaborn (Long Format)
# Structure: | Region | Scenario | Opex |
df_plot = pd.DataFrame({
    'Status Quo': agg_sq,
    'IEM': agg_iem
}).reset_index().melt(id_vars='index', var_name='Scenario', value_name='Opex [€]')

df_plot.rename(columns={'index': 'Zone'}, inplace=True)


plt.figure(figsize=(10, 6))
sns.set_context("talk")

# Create a grouped bar chart
sns.barplot(
    data=df_plot,
    x='Zone',
    y='Opex [M€]',
    hue='Scenario',
    palette='Set2',
    edgecolor='black'
)

plt.title('Total OPEX Comparison: GB vs Rest of EU')
plt.ylabel('Operational Expenditure [€]')
plt.xlabel('') # 'Region' is obvious, so we can hide the label
plt.grid(True, axis='y', linestyle='--', alpha=0.3)
plt.tight_layout()

# plt.savefig('opex_comparison_gb_eu.png')
plt.show()
'''


