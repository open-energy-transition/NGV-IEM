import pandas as pd
import pypsa

targetdir_sq = "/Users/tpa/MyProjects/NGV-IEM/resources/base_s_all_lluk__2030.nc"
targetdir_iem = "/Users/tpa/MyProjects/NGV-IEM/resources/base_s_all___2030_no_ce.nc"

n_sq = pypsa.Network(targetdir_sq)
n_iem = pypsa.Network(targetdir_iem)

df_prices_sq = pd.read_csv("/Users/tpa/MyProjects/NGV-IEM/results/draft_report/tables/weighted_average_zonal_prices_status_quo_2030.csv", index_col=0)
df_prices_iem = pd.read_csv("/Users/tpa/MyProjects/NGV-IEM/results/draft_report/tables/weighted_average_zonal_prices_iem_2030.csv", index_col=0)


list_of_zones = n_sq.buses[n_sq.buses["carrier"] == 'AC']

demand_dict_sq = {}
demand_dict_iem = {}

for zone in list_of_zones.index:
    ac_balance_per_bus_sq = n_sq.statistics.energy_balance(bus_carrier="AC", groupby=["bus", "carrier"])
    ac_balance_sq = ac_balance_per_bus_sq.xs(zone, level=1)
    ac_demand_sq = ac_balance_sq[ac_balance_sq < 0].sum()
    demand_dict_sq[zone] = - ac_demand_sq

    ac_balance_per_bus_iem = n_iem.statistics.energy_balance(bus_carrier="AC", groupby=["bus", "carrier"])
    ac_balance_iem = ac_balance_per_bus_iem.xs(zone, level=1)
    ac_demand_iem = ac_balance_iem[ac_balance_iem < 0].sum()
    demand_dict_iem[zone] = - ac_demand_iem

df_demand_sq = pd.DataFrame.from_dict(demand_dict_sq, orient="index")
df_demand_iem = pd.DataFrame.from_dict(demand_dict_iem, orient="index")

weighted_average_price_sq = (df_prices_sq.iloc[:,0] * df_demand_sq.iloc[:,0]).sum() / df_demand_sq.sum()
weighted_average_price_iem = (df_prices_iem.iloc[:,0] * df_demand_iem.iloc[:,0]).sum() / df_demand_iem.sum()


