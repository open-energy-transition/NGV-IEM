import pypsa
import pandas as pd



#-------- Load solved network -----#
n = pypsa.Network(snakemake.input[0])

#------- Filter GB interconnections----------#

GB_ZONE = "GB00"

zonal_interconnections = n.links.query("carrier == 'DC'")

links_gb = zonal_interconnections[
    (zonal_interconnections.bus0 == GB_ZONE) |   # Q: do we include GBNI (Northern Ireland) links with other neighbors as well?
    (zonal_interconnections.bus1 == GB_ZONE)
]

#------- Identify neighboring zones-----------#

neighbors = []

for link_name, link in links_gb.iterrows():

    if link.bus0 == GB_ZONE:
        neighbor = link.bus1
        direction = +1   # positive flow means export from GB → neighbor
    else:
        neighbor = link.bus0
        direction = -1   # negative flow means import from neighbor → GB

    neighbors.append((link_name, neighbor, direction))

neighbors_df = pd.DataFrame(neighbors, columns=["link", "neighbor", "sign"])

#--------- Get flow on each interconnector (net GB import/export)----------#

# Flows are stored in:
#   n.links_t.p0 : flow at bus0 (positive = from bus0 → bus1)
#   n.links_t.p1 : flow at bus1 (positive = from bus1 → bus0)

# Standardize flow direction:
# Positive = flow from GB → neighbor
# Negative = flow from neighbor → GB

flow_dict = {}

for link_name, neighbor, sign in neighbors:
    flow = sign * n.links_t.p0[link_name]   # consistent sign convention
    flow_dict[link_name] = flow

flow_df = pd.DataFrame(flow_dict)


#-------Get net flow between zones -----#

groups = {}

for link_name, neighbor, sign in neighbors:
    interconnection = f"{GB_ZONE}-{neighbor}"   # e.g. GB-BE, GB-NL, GB-FR. Note: Has GB always first in order.
    if interconnection not in groups:
        groups[interconnection] = []
    groups[interconnection].append(link_name)

netflow_df = pd.DataFrame({
    interconnection: flow_df[links].sum(axis=1)
    for interconnection, links in groups.items()
})

#------ Calculate average netflow in each interconnection -----#
average_netflow_df = netflow_df.mean(axis=0)

#------ Calculate congestion income per interconnection between bidding zones -------#

prices_df = pd.DataFrame()
income_dict = {}

for interconnection in netflow_df.columns:
    gb_bus, neighbor_bus = interconnection.split("-")    # Interconnections are named with GB always coming first in order

    # GB price
    gb_price = n.buses_t.marginal_price[gb_bus]
    prices_df[gb_bus] = gb_price

    # Neighbor price
    neighbor_price = n.buses_t.marginal_price[neighbor_bus]
    prices_df[neighbor_bus] = neighbor_price

    price_difference = neighbor_price - gb_price # Important: Must be consistent with sign convention on flow (positive if GB exports)
    prices_df[interconnection] = price_difference

    netflow = netflow_df[interconnection]

    # revenue = ΔP × flow (€/MWh × MW / 10e6 = M€/h)
    revenue = price_difference * netflow
    income_dict[interconnection] = revenue

income_df = pd.DataFrame(income_dict)

#----------Calculate average price difference between neighbors -----#
average_price_difference = prices_df[netflow_df.columns].mean(axis=0)

#----------- Calculate the total annual results ----------

annual_income = income_df.sum()
average_income = income_df.mean() #convert to Euros
total_annual_income = annual_income.sum()

final_df = pd.concat([annual_income, average_income, average_price_difference, average_netflow_df], axis = 1)
final_df = final_df.rename(columns={0: "Total annual congestion income [€]", 1: "Average congestion income [€/h]",
                                    2: "Average Price Difference [Euros/MWh]", 3: "Average Netflow [MW]"})
#----------- Export results to table -----------#

final_df.to_csv(snakemake.output[0], index=True)
income_df.to_csv(snakemake.output[1], index=True)
prices_df[netflow_df.columns].to_csv(snakemake.output[2], index=True)
netflow_df.to_csv(snakemake.output[3], index=True)
