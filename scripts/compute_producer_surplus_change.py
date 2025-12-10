import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.ticker as mtick # For nice % formatting


######### IMPORTANT ############## (scaling issues)
# Should decide if results will be aggregated for whole rest of EU or only the neighbors.
# Should decide if the absolute results will be presented or only the relative change

# Current implementation: GB neighbors and relative change (better scaling?)

# Load Data
df_sq = pd.read_csv(snakemake.input.sq, index_col=0)
df_iem = pd.read_csv(snakemake.input.iem, index_col=0)

# Calculate difference in Producer surplus
df_diff = df_sq - df_iem  #using status quo as reference

df_diff.to_csv(snakemake.output[0])

#targetdir = '/Users/tpa/MyProjects/NGV-IEM/results/draft_report/tables/total_system_costs_status_quo_2030.csv'
#targetdir2 = '/Users/tpa/MyProjects/NGV-IEM/results/draft_report/tables/total_system_costs_iem_2030.csv'

#df_sq = pd.read_csv(targetdir, index_col=0)
#df_iem = pd.read_csv(targetdir2, index_col=0)

# Ensure the column has a consistent name for processing
# (Assuming the first column contains the OPEX data)
opex_col_sq = df_sq.columns[0]
opex_col_iem = df_iem.columns[0]

def aggregate_regions(df, value_col, target_zone='GB00', other_label='Rest of EU'):
    """
    Separates the target zone from the rest and sums the rest.
    """
    # 1. Get the specific zone's value
    if target_zone in df.index:
        target_value = df.loc[target_zone, value_col]
    else:
        target_value = 0  # Handle case where GB00 might be missing
        print(f"Warning: {target_zone} not found in dataframe.")

    # 2. Sum everything else
    # We drop the target zone and sum the remaining rows
    rest_value = df.drop(index=target_zone, errors='ignore')[value_col].sum()

    # 3. Return a clean mini-dataframe
    return pd.Series({
        target_zone: target_value,
        other_label: rest_value
    })

# --- 3. Process Both Scenarios ---
# Create the aggregated data for both
#agg_sq = aggregate_regions(df_sq, opex_col_sq)
#agg_iem = aggregate_regions(df_iem, opex_col_iem)


# Alternative approach: Aggregate only GB neighbors
# Your specific list of zones (includes GB00 + Neighbors)
zones_of_interest = ['GB00', 'BE00', 'DE00', 'DKW1','FR00', 'GBNI', 'IE00', 'NL00', 'NOS0']

# Define who is the "Main" zone and who are the "Neighbors"
target_zone = 'GB00'
neighbor_label = 'GB Neighbors'

# Derive the neighbor list (Everyone in the list EXCEPT GB00)
neighbor_zones = [z for z in zones_of_interest if z != target_zone]


def aggregate_specific_zones(df, value_col, target, neighbors, neighbor_label):
    # 1. Get Target (GB00)
    if target in df.index:
        val_target = df.loc[target, value_col]
    else:
        val_target = 0

    # 2. Get Neighbors
    # We filter the dataframe to only include rows that exist in our 'neighbor_zones' list
    # The .reindex() ensures we don't crash if a neighbor is missing from the CSV (it just puts 0/NaN)
    val_neighbors = df.reindex(neighbors)[value_col].sum()

    return pd.Series({
        target: val_target,
        neighbor_label: val_neighbors
    })


# Apply the function
agg_sq = aggregate_specific_zones(df_sq, opex_col_sq, target_zone, neighbor_zones, neighbor_label)
agg_iem = aggregate_specific_zones(df_iem, opex_col_iem, target_zone, neighbor_zones, neighbor_label)

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
plt.title('Relative Change in Producer Surplus (IEM vs Status Quo)')
plt.ylabel('Change in Euros')
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
