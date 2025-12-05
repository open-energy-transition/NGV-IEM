import pypsa
import pandas as pd


# Load networks from two scenarios
n_status_quo = pypsa.Network(snakemake.input.network_status_quo)
n_iem = pypsa.Network(snakemake.input.network_iem)


# TO DO better define the countries (in accordance with TYNDP)
list_of_zones = n_status_quo.buses[n_status_quo.buses["carrier"] == 'AC']

# Dictionary to store results
change_consumer_surplus_dict = {}

for zone in list_of_zones.index:

    # Determine loads connected to zone (Probably always 1 load per zone)
    zonal_loads_status_quo = n_status_quo.loads[n_status_quo.loads.index == zone].index
    zonal_loads_iem = n_iem.loads[n_iem.loads.index == zone].index

    # Get electricity demand of zone for each scenario (Probably same in both)
    zonal_demand_status_quo = n_status_quo.loads_t.p[zonal_loads_status_quo].sum(axis = 1)
    zonal_demand_iem = n_iem.loads_t.p[zonal_loads_iem].sum(axis = 1)

    # Get zonal prices in each scenario
    zonal_price_status_quo = n_status_quo.buses_t.marginal_price[zone]
    zonal_price_iem = n_iem.buses_t.marginal_price[zone]

    # Compute producer surplus of selected zone (timeseries and the total annual)
    consumer_surplus_change = zonal_price_status_quo*zonal_demand_status_quo - zonal_price_iem*zonal_demand_iem

    consumer_surplus_change_total = consumer_surplus_change.sum(axis = 0)

    # Save to dictionary
    change_consumer_surplus_dict[zone] = consumer_surplus_change_total

# Convert to dataframe for easy viewing / plotting
consumer_surplus_change_df = pd.DataFrame.from_dict(change_consumer_surplus_dict, orient="index", columns=["Total Annual Consumer Surplus [€]"])

consumer_surplus_change_df.to_csv(snakemake.output[0], index=True)



