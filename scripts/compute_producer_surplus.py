import pypsa
import pandas as pd


#-------- Load solved network -----#
targetdir = '/Users/tpa/MyProjects/NGV-IEM/resources/base_s_all_lluk__2030.nc'
n = pypsa.Network(targetdir)
#n = pypsa.Network(snakemake.input[0])

# TO DO better define the countries (in accordance with TYNDP)
list_of_zones = n.buses[n.buses["carrier"] == 'AC']

# Dictionary to store results
producer_surplus_dict = {}

for zone in list_of_zones.index:
    # Get power output of generators in selected zone (timeseries)
    gens_zone = n.generators[n.generators.bus == zone].index

    if len(gens_zone) == 0:
        # Skip zones with no generators
        continue

    p = n.generators_t.p[gens_zone]

    zonal_price = n.buses_t.marginal_price[zone]

    # Compute producers' revenue in selected zone

    revenue = zonal_price * p.sum(axis = 1)
    revenue_per_gen = p.mul(zonal_price, axis=0)
    revenue_per_zone = revenue_per_gen.sum(axis=1)

    # Calculate electricity supply cost in selected zone
    mc = n.generators.loc[gens_zone, "marginal_cost"]
    supply_costs_per_gen = p * mc
    supply_costs_per_zone = supply_costs_per_gen.sum(axis = 1)

    # Compute producer surplus of selected zone (timeseries and the total annual)
    producer_surplus_ts = revenue_per_zone - supply_costs_per_zone

    producer_surplus_total = producer_surplus_ts.sum(axis = 0)

    # Save to dictionary
    producer_surplus_dict[zone] = producer_surplus_total

# Convert to dataframe for easy viewing / plotting
producer_surplus_df = pd.DataFrame.from_dict(producer_surplus_dict, orient="index", columns=["Total Annual Producer Surplus [€]"])

producer_surplus_df.to_csv(snakemake.output[0], index=True)


