import pypsa
import pandas as pd


#-------- Load solved network -----#
n_sq = pypsa.Network(snakemake.input.network_status_quo)
n_iem = pypsa.Network(snakemake.input.network_iem)

def get_total_capex(n):
    """
    Calculates the sum of all annualized investment costs
    (Generators, Storage, Transmission Lines, Links).
    """
    # groupby=False gives detailed list, .sum() aggregates everything to one number
    return n.statistics.capex(groupby=False).sum()

capex_sq = get_total_capex(n_sq) /1e6
capex_iem = get_total_capex(n_iem) /1e6

diff = capex_iem - capex_sq

# 4. Create Comparison DataFrame
df_results = pd.DataFrame({
    "Scenario": ["Status Quo", "IEM", "Difference (IEM-SQ)"],
    "Total_CAPEX_M_EUR": [capex_sq, capex_iem, diff]
})


df_results.set_index("Scenario", inplace=True)
df_results.to_csv(snakemake.output[0])