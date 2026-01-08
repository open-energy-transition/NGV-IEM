import pypsa
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd
import matplotlib.ticker as mtick # For nice % formatting

# Load networks from two scenarios
n_sq = pypsa.Network(snakemake.input.network_status_quo)
n_iem = pypsa.Network(snakemake.input.network_iem)

#n_sq = pypsa.Network("/Users/tpa/MyProjects/NGV-IEM/resources/base_s_all_lluk__2030.nc")
#n_iem = pypsa.Network("/Users/tpa/MyProjects/NGV-IEM/resources/base_s_all___2030.nc")


# TO DO better define the countries (in accordance with TYNDP)
list_of_zones = n_sq.buses[n_sq.buses["carrier"] == 'AC']
#list_of_zones = n_status_quo.loads[n_status_quo.loads.carrier == "electricity"]

# Dictionary to store results
change_consumer_surplus_dict = {}

for zone in list_of_zones.index:

    ac_balance_per_bus_sq = n_sq.statistics.energy_balance(bus_carrier="AC", groupby=["bus", "name", "carrier"], groupby_time = False)
    ac_balance_per_bus_iem = n_iem.statistics.energy_balance(bus_carrier="AC", groupby=["bus", "name", "carrier"], groupby_time = False)

    ac_balance_sq = ac_balance_per_bus_sq.xs(zone, level=1)
    ac_balance_iem = ac_balance_per_bus_iem.xs(zone, level=1)

    ac_demand_sq = ac_balance_sq[ac_balance_sq < 0]
    ac_demand_iem = ac_balance_iem[ac_balance_iem < 0]

    excluded_carriers = ["DC", "DC_OH", "battery charger"]
    ac_demand_sq = ac_demand_sq[~ac_demand_sq.index.get_level_values("carrier").isin(excluded_carriers)]
    ac_demand_iem = ac_demand_iem[~ac_demand_iem.index.get_level_values("carrier").isin(excluded_carriers)]

    zonal_demand_status_quo = - ac_demand_sq.sum(axis = 0)
    zonal_demand_iem = - ac_demand_iem.sum()

    # Get zonal prices in each scenario
    zonal_price_status_quo = n_sq.buses_t.marginal_price[zone]
    zonal_price_iem = n_iem.buses_t.marginal_price[zone]

    # Compute change in consumer surplus: Use status_quo as reference --> positive change = prices at iem are lower (benefit for consumers)
    consumer_surplus_change = zonal_price_status_quo*zonal_demand_status_quo - zonal_price_iem*zonal_demand_iem

    consumer_surplus_change_total = consumer_surplus_change.sum(axis = 0)

    # Save to dictionary
    change_consumer_surplus_dict[zone] = consumer_surplus_change_total

# Convert to dataframe for easy viewing / plotting
consumer_surplus_change_df = pd.DataFrame.from_dict(change_consumer_surplus_dict, orient="index", columns=["Change in Total Annual Consumer Surplus [M€]"])
consumer_surplus_change_df = consumer_surplus_change_df/1e6 # convert to Millions

consumer_surplus_change_df.to_csv(snakemake.output[0], index=True)


# --- 1. Setup ---
# Your specific list of zones
zones_of_interest = ['GB00', 'BE00', 'DE00', 'DKW1','FR00', 'GBNI', 'IE00', 'NL00', 'NOS0']

target_zone = 'GB00'
#neighbor_label = 'GB Neighbors'
rest_eu_label = 'Rest of EU'
total_label = 'Total System'

# Derive the neighbor list
neighbor_zones = [z for z in zones_of_interest if z != target_zone]

# Ensure we grab the numeric column (assuming it's the first one)
col_name = consumer_surplus_change_df.columns[0]

# Get Target Value
if target_zone in consumer_surplus_change_df.index:
    val_target = consumer_surplus_change_df.loc[target_zone, col_name]
else:
    val_target = 0

# Get Neighbors Sum
# .reindex() selects only the neighbor rows; sum() adds up their changes
#val_neighbors = consumer_surplus_change_df.reindex(neighbor_zones)[col_name].sum()
val_rest_eu = consumer_surplus_change_df.drop(index=target_zone, errors='ignore')[col_name].sum()

# We sum the entire column to get the system-wide change
val_total = consumer_surplus_change_df[col_name].sum()

# Create Plotting DataFrame
df_plot = pd.DataFrame({
    'Zone': [target_zone, rest_eu_label, total_label],
    'Change [M€]': [val_target, val_rest_eu, val_total]
})

# --- 4. Plotting ---
plt.figure(figsize=(8, 6))
sns.set_context("talk")

# COLOR LOGIC:
# For Consumer Surplus, Positive Change is GOOD (Green), Negative is BAD (Red)
#colors = ['#2ca02c' if x > 0 else '#d62728' for x in df_plot['Change [M€]']]
colors = ['#9FE0E8' if x > 0 else '#FBDEBD' for x in df_plot['Change [M€]']]

#N-side colours
# #00ACC2 = blue
# #F4A74F = yellow/orange
# #8CBB13 = green
# #535F6B = pink
# #D63487 = dark grey

ax = sns.barplot(
    data=df_plot,
    x='Zone',
    y='Change [M€]',
    palette=colors,
    edgecolor='black'
)

# --- 5. Formatting ---
plt.title('Change in Consumer Surplus (IEM vs Status Quo)')
plt.ylabel('Change in Surplus [M€]')
plt.xlabel('')
plt.axhline(0, color='black', linewidth=1.5)

''''
# Add value labels (Scale to Millions for readability if needed)
for i, v in enumerate(df_plot['Change [M€]']):
    offset = (max(df_plot['Change [M€]']) - min(df_plot['Change [M€]'])) * 0.05
    offset = offset if v >= 0 else -offset

    # Format: € +1.5M (Assuming values are raw Euros, dividing by 1e6 for display)
    # Adjust the /1e6 based on your actual data magnitude!
    label_text = f"{v :+.1f} M€"

    ax.text(i, v + offset, label_text, ha='center', fontweight='bold', fontsize=12)
'''

plt.grid(True, axis='y', linestyle='--', alpha=0.3)
plt.tight_layout()
plt.savefig(snakemake.output[1])