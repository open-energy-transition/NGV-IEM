import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


df_sq = pd.read_csv(snakemake.input.sq, index_col=0)
df_iem = pd.read_csv(snakemake.input.iem, index_col=0)

df_diff = df_iem - df_sq


df_diff["relative difference [%]"] = df_diff/df_sq*100

df_diff.to_csv(snakemake.output[0])

