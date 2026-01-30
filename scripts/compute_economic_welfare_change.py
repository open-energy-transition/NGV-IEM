import pandas as pd


df_cong_inc = pd.read_csv(snakemake.input.cong_inc, index_col=0)
df_prod_sur = pd.read_csv(snakemake.input.prod_sur, index_col=0)
df_cons_sur = pd.read_csv(snakemake.input.cons_sur, index_col=0)
df_opex = pd.read_csv(snakemake.input.opex, index_col=0)

#df_cong_inc = pd.read_csv("/Users/tpa/MyProjects/NGV-IEM/results/draft_report/tables/comparison_total_congestion_income_2030.csv", index_col=0)
#df_prod_sur = pd.read_csv("/Users/tpa/MyProjects/NGV-IEM/results/draft_report/tables/comparison_producer_surplus_2030.csv", index_col=0)
#df_cons_sur = pd.read_csv("/Users/tpa/MyProjects/NGV-IEM/results/draft_report/tables/comparison_consumer_surplus_2030.csv", index_col=0)
#df_opex = pd.read_csv("/Users/tpa/MyProjects/NGV-IEM/results/draft_report/tables/comparison_total_opex_2030.csv", index_col=0)


tot_cong_inc = df_cong_inc.loc["Total System", "Annual_Congestion_Rent_EUR"]/1e6  # convert to Million Euros
tot_prod_sur = df_prod_sur.sum().sum()
tot_cons_sur = df_cons_sur.sum().sum()
tot_opex = df_opex.sum().sum()

tot_economic_welfare_change = tot_cong_inc + tot_prod_sur + tot_cons_sur

alternative_economic_welfare_change = -df_opex.sum().sum()


data = {
    "Approach": ["Welfare change", " OPEX change"],
    "Economic Welfare change": [tot_economic_welfare_change, alternative_economic_welfare_change],
}

df_congestion_summary = pd.DataFrame(data)

# Optional: Set 'Scope' as the index for a cleaner look
df_congestion_summary.set_index("Approach", inplace=True)

# Save results in output
df_congestion_summary.to_csv(snakemake.output[0], index=True)



