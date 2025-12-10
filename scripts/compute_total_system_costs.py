import pypsa
import pandas as pd


#-------- Load solved network -----#
n = pypsa.Network(snakemake.input[0])

# Filter only the electricity related zonal buses (countries)
list_of_zones = n.buses[n.buses["carrier"] == 'AC'].index

# --- CREATE THE BUS MAPPER ---
# Maps Component Name -> Electricity Bus
bus_mapper = pd.concat([
    n.generators.bus,          # Generators -> bus
    n.links.bus1,              # Links -> bus1 (Output bus)
    n.storage_units.bus,       # Hydro -> bus
    n.stores.bus               # Stores -> bus
])

raw_opex = n.statistics.opex(aggregate_time='sum', groupby=False)
raw_revenue = n.statistics.revenue(aggregate_time='sum', groupby=False)

# --- EXPLICIT MAPPING ---
# Get the list of component names from the OPEX results (Level 1 of MultiIndex)
component_names_opex = raw_opex.index.get_level_values(1)
component_names_revenue = raw_revenue.index.get_level_values(1)

# Map these names to their buses using our mapper
mapped_buses_opex = component_names_opex.map(bus_mapper)
mapped_buses_revenue = component_names_revenue.map(bus_mapper)

# Group by this new list of buses
opex_by_bus = raw_opex.groupby(mapped_buses_opex).sum()
revenue_by_bus = raw_revenue.groupby(mapped_buses_revenue).sum()

df_economics = pd.DataFrame({
    "Producer Revenue [M€]": revenue_by_bus,
    "OPEX [M€]": opex_by_bus
})

df_economics['Producer Surplus [M€]'] = df_economics["Producer Revenue [M€]"] - df_economics["OPEX [M€]"]

# Perform the filtering based on the selected zones
result = df_economics.reindex(list_of_zones).fillna(0)
result = result / 1e6  # convert to millions

result = result.drop(columns = ["Producer Revenue [M€]", "Producer Surplus [M€]"])

result.to_csv(snakemake.output[0], index = True)

