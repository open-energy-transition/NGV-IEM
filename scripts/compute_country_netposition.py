import pypsa
import pandas as pd



#-------- Load solved network -----#
n = pypsa.Network(snakemake.input[0])


list_of_zones = n.buses[n.buses["carrier"] == 'AC']

netposition_dict = {}


for zone in list_of_zones.index:
    netposition = n.statistics.energy_balance(bus_carrier="AC", groupby=["bus", "carrier"], groupby_time=False).xs(
        zone, level=1).loc["Link", "DC"]

    netposition_dict[zone] = netposition


netposition_df = pd.DataFrame(netposition_dict)
total_netposition_df = netposition_df.sum(axis=0).T
total_netposition_df.to_csv(snakemake.output[0], index=True)