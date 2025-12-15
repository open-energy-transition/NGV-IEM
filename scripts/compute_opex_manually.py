import pypsa
import pandas as pd

targetdir = '/Users/tpa/MyProjects/NGV-IEM/resources/base_s_all___2030.nc'
n = pypsa.Network(targetdir)

# TO DO better define the countries (in accordance with TYNDP)
list_of_zones = n.buses[n.buses["carrier"] == 'AC']

# Dictionary to store results
total_system_costs_dict = {}

for zone in list_of_zones.index:
    # Get power output of generators in selected zone (timeseries)
    gens_zone = n.generators[n.generators.bus == zone].index

    if len(gens_zone) == 0:
        # Skip zones with no generators
        continue

    p = n.generators_t.p[gens_zone]

    # Calculate electricity supply cost in selected zone
    mc = n.generators.loc[gens_zone, "marginal_cost"]
    supply_costs_per_gen = p * mc
    supply_costs_per_zone = supply_costs_per_gen.sum(axis = 1)

    # Save to dictionary
    total_system_costs_dict[zone] = supply_costs_per_zone

# Convert to dataframe for easy viewing / plotting
total_system_costs_df = pd.DataFrame.from_dict(total_system_costs_dict)

total_system_costs_df.to_csv(snakemake.output[0], index=True)


