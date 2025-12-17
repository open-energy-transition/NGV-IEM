import pypsa
import pandas as pd



#-------- Load solved network -----#
n = pypsa.Network(snakemake.input[0])


list_of_zones = n.buses[n.buses["carrier"] == 'AC']

zonal_prices_dict = {}
zonal_demand_dict = {}
weights_dict = {}

for zone in list_of_zones.index:
    # Get zonal price
    zonal_price = n.buses_t.marginal_price[zone]
    zonal_prices_dict[zone] = zonal_price


    # Get zonal load
    #zonal_load = n.loads[n.loads.index == zone].index
    #zonal_demand = n.loads_t.p[zonal_load].sum(axis=1)
    #zonal_demand_dict[zone] = zonal_demand

    # Get timeseries with load of all components connected to zone (it includes exports)
    withdrawal = n.statistics.withdrawal(bus_carrier="AC", groupby=["bus", "carrier"], groupby_time=False).xs(
        zone, level=1)

    total_demand = withdrawal.sum(axis = 0)

    zonal_demand_dict[zone] = total_demand

    # Also, extract weights per snapshot
    weight = total_demand / total_demand.sum()
    weights_dict[zone] = weight


# Convert to DataFrame
zonal_price_df = pd.DataFrame(zonal_prices_dict)
zonal_demand_df = pd.DataFrame(zonal_demand_dict)
weights_df = pd.DataFrame(weights_dict)

average_zonal_price = zonal_price_df.mean()

# Get weighted average zonal price per zone
weighted_average_zonal_price_df = zonal_price_df*weights_df
weighted_average_zonal_price_df = weighted_average_zonal_price_df.sum(axis = 0)

weighted_average_zonal_price_df.to_csv(snakemake.output[0], index=True)
average_zonal_price.to_csv(snakemake.output[1], index=True)
