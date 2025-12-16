import pypsa
import pandas as pd



#-------- Load solved network -----#
n = pypsa.Network(snakemake.input[0])


list_of_zones = n.buses[n.buses["carrier"] == 'AC']

zonal_prices_dict = {}
zonal_demand_dict = {}

for zone in list_of_zones.index:
    # Get zonal price
    zonal_price = n.buses_t.marginal_price[zone]
    zonal_prices_dict[zone] = zonal_price

    # Get zonal load
    zonal_load = n.loads[n.loads.index == zone].index
    zonal_demand = n.loads_t.p[zonal_load].sum(axis=1)
    zonal_demand_dict[zone] = zonal_demand


zonal_price_df = pd.DataFrame.from_dict(zonal_prices_dict, orient="index", columns=["Zonal Price [€/MWh]"])
zonal_demand_df = pd.DataFrame.from_dict(zonal_demand_dict, orient="index", columns= ["Zonal Demand [MWh]"])

zonal_price_df.to_csv(snakemake.output[0], index=False)
zonal_demand_df.to_csv(snakemake.output[1], index=False)
