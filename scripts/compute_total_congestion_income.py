import pypsa
import pandas as pd


#-------- Load solved network -----#
n = pypsa.Network(snakemake.input[0])

#targetdir = 'resources/base_s_all___2030.nc'
#n = pypsa.Network(targetdir)

# Filter or zonal interconnections
zonal_interconnections = n.links.query("carrier == 'DC'")
link_names = zonal_interconnections.index

# Get the power flow in the links
flows = n.links_t.p0[link_names]

# Get price difference in the connected zones
list_bus0 = zonal_interconnections.bus0
list_bus1 = zonal_interconnections.bus1

all_prices = n.buses_t.marginal_price

prices_at_bus0 = all_prices[list_bus0]
prices_at_bus0.columns = link_names

prices_at_bus1 = all_prices[list_bus1]
prices_at_bus1.columns = link_names

# Use convention: bus1 - bus0 to ensure positive congestion income when we have intuitive flows (flow is always positive)
price_difference = prices_at_bus1 - prices_at_bus0

congestion_income = flows * price_difference

# Get annual congestion income per link
annual_congestion_income = congestion_income.sum()

# Get total system annual congestion income
total_system_congestion_income = annual_congestion_income.sum()

# Filter congestion income of GB interconnections
GB_ZONE = "GB00"

links_gb = zonal_interconnections[
    (zonal_interconnections.bus0 == GB_ZONE) |
    (zonal_interconnections.bus1 == GB_ZONE)
]

annual_congestion_income_gb = annual_congestion_income[links_gb.index]
total_gb_congestion_income = annual_congestion_income_gb.sum()

# Store results
data = {
    "Scope": ["Total System", "Great Britain (GB Connected)"],
    "Annual_Congestion_Rent_EUR": [total_system_congestion_income, total_gb_congestion_income],
}

df_congestion_summary = pd.DataFrame(data)

# Optional: Set 'Scope' as the index for a cleaner look
df_congestion_summary.set_index("Scope", inplace=True)

# Save results in output
df_congestion_summary.to_csv(snakemake.output[0], index=True)