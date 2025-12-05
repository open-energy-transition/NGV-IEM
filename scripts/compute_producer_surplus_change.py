
import pandas as pd



df_status_quo = pd.read_csv(snakemake.input.status_quo, index_col=0)  # Series: index=interconnections
df_iem = pd.read_csv(snakemake.input.iem, index_col=0)



df_diff = df_status_quo - df_iem  #using status quo as reference

df_diff.to_csv(snakemake.output[0])