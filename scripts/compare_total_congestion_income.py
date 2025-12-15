import pandas as pd


df_ex = pd.read_csv(snakemake.input.ci_sq, index_col=0)
df_iem = pd.read_csv(snakemake.input.ci_iem, index_col=0)

df_diff = df_iem - df_ex

df_diff.to_csv(snakemake.output[0])


