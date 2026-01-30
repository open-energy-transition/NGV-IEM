import pandas as pd
import pypsa


targetdir_sq = "/Users/tpa/MyProjects/NGV-IEM/resources/base_s_all_lluk__2030.nc"
targetdir_iem = "/Users/tpa/MyProjects/NGV-IEM/resources/base_s_all___2030_no_ce.nc"


n_sq = pypsa.Network(targetdir_sq)
n_iem = pypsa.Network(targetdir_iem)


n = n_sq

shedding_generators = n.generators[n.generators.carrier == "load"]

if not shedding_generators.empty:
    # 2. Get the Time Series of Shedding (MW)
    # n.generators_t.p contains the hourly generation
    shedding_ts = n.generators_t.p[shedding_generators.index]
    total_shedding = shedding_ts.sum()

    # Sum across all nodes to get "System Wide Shedding" per hour
    system_shedding_ts = shedding_ts.sum(axis=1)

    # 3. Calculate Metrics
    # Threshold: We look for values > 0.1 MW to avoid floating point noise (0.0000001)
    hours_with_shedding = (system_shedding_ts > 1).sum()
    total_energy_shed = system_shedding_ts.sum()
    max_shedding = system_shedding_ts.max()

    print(f"--- Load Shedding Statistics ---")
    print(f"Number of hours with shedding: {hours_with_shedding} h")
    print(f"Total energy shed:             {total_energy_shed:,.2f} MWh")
    print(f"Max peak shedding:             {max_shedding:,.2f} MW")

    # 4. (Optional) See exactly WHEN it happened
    if hours_with_shedding > 0:
        print("\nTop 5 worst shedding hours:")
        print(system_shedding_ts.sort_values(ascending=False).head(5))

else:
    print("No load shedding generators found in the network.")


n = n_iem


list_of_zones = n.buses[n.buses["carrier"] == 'low voltage'].index
zonal_prices = n.buses_t.marginal_price[list_of_zones]
shedding_price_threshold = 3900

results_list = []
for zone in list_of_zones:
    zonal_prices = n.buses_t.marginal_price[zone]
    hours_of_shedding = (zonal_prices >= shedding_price_threshold).sum()

    results_list.append({
        "Zone": zone,
        "Hours_Load_Shedding": hours_of_shedding,
        "Max_Price": zonal_prices.max()  # Useful to verify if it hit exactly VOLL
    })

df_shedding = pd.DataFrame(results_list)

df_active_shedding = df_shedding[df_shedding["Hours_Load_Shedding"] > 0].sort_values("Hours_Load_Shedding", ascending=False)

