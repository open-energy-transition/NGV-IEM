import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
#plt.style.use('Users/tpa/MyProjects/NGV-IEM/nside_colourmap/nside-main.mplstyle')

nside_colours = ['#00ACC2', '#F4A74F', '#8CBB13', '#535F6B', '#D63487']

#targetdir = '/Users/tpa/MyProjects/NGV-IEM/results/draft_report/tables/congestion_income_metrics_status_quo.csv'
#targetdir2 = '/Users/tpa/MyProjects/NGV-IEM/results/draft_report/tables/congestion_income_metrics_iem.csv'

#df_sq = pd.read_csv(targetdir, index_col=0)
#df_iem = pd.read_csv(targetdir2, index_col=0)

df_sq = pd.read_csv(snakemake.input.metrics_sq, index_col=0)
df_iem = pd.read_csv(snakemake.input.metrics_iem, index_col=0)

P_old = df_sq['Average Price Difference [Euros/MWh]']
Q_old = df_sq['Total exchanged volume [MW]']

P_new = df_iem['Average Price Difference [Euros/MWh]']
Q_new = df_iem['Total exchanged volume [MW]']

# 3. Calculate The Variance Decomposition
# Delta Volume = (Change in Flow) * Old Price
vol_effect = (Q_new - Q_old) * P_old

# Delta Price = (Change in Price) * New Flow
price_effect = (P_new - P_old) * Q_new

# Total Change (The sum of the two effects)
total_change = vol_effect + price_effect

# 4. Prepare DataFrame for Plotting
df_plot = pd.DataFrame({
    'Volume Effect': vol_effect,
    'Price Effect': price_effect,
    'Net Change': total_change
})

# Sort by Net Change so the most significant interconnectors are on the left
# You can also filter here (e.g., .head(15)) to keep the plot readable
df_plot = df_plot.sort_values('Net Change', ascending=False)  # .iloc[:15]

# Create a new list for the index
new_labels = []

for i, s in enumerate(df_plot.index):
    if s == "GB00-GBNI":
        new_labels.append("GB-NIR")  # The Exception
    else:
        new_labels.append(s[:2] + "-" + s[5:7]) # The Rule

# Assign the list back to the dataframe
df_plot.index = new_labels

# 5. Plotting
sns.set_context("talk")
fig, ax = plt.subplots(figsize=(14, 8))

# Create the Stacked Bar Chart for the Effects
# We plot Volume and Price effects.
# Note: If one is + and one is -, they will start from 0 and go in opposite directions
df_plot[['Volume Effect', 'Price Effect']].plot(
    kind='bar',
    stacked=True,
    ax=ax,
    color=nside_colours,  # Blue for Vol, Orange for Price
    width=0.8,
    alpha=1
)

# Add the "Net Change" marker (The black diamond)
# This shows the actual final result after the two effects battle it out
x_coords = range(len(df_plot))
ax.scatter(x_coords, df_plot['Net Change'],
           color='black', marker='D', s=50, label='Total Net Change', zorder=10)

# 6. Styling
#plt.title('Decomposition of Congestion Income Change\n(Explicit vs Implicit)', pad=20)
plt.ylabel('Change in Average Congestion Income [€/h]')
plt.xlabel('Interconnection')

# Add a horizontal line at 0
plt.axhline(0, color='black', linewidth=1)

plt.legend()
plt.grid(True, axis='y', linestyle='--', alpha=0.3)
plt.tight_layout()
plt.savefig(snakemake.output[0])

