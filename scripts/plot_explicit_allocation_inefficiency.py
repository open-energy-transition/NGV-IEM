import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

#targetdir = '/Users/tpa/MyProjects/NGV-IEM/results/draft_report/tables/congestion_income_metrics_status_quo.csv'
#targetdir2 = '/Users/tpa/MyProjects/NGV-IEM/results/draft_report/tables/congestion_income_metrics_iem.csv'

#df_sq = pd.read_csv(targetdir, index_col=0)
#df_iem = pd.read_csv(targetdir2, index_col=0)

df_netflow = pd.read_csv(snakemake.input.nf_sq, index_col=0)
df_price_diff = pd.read_csv(snakemake.input.pd_sq, index_col=0)

# Select interconnection
intercon = "GB00-BE00"

# TODO change filtering, to be done based on selected intercon

data = pd.DataFrame({
        'Price Difference [€/MWh]': df_price_diff.iloc[:, 0], # Adjust column selection if needed
        'Flow [MW]': df_netflow.iloc[:, 0],

    })

# 3. Plotting
plt.figure(figsize=(10, 10))  # Square figure is best for parity plots
sns.set_context("talk")

# The Scatter Plot
sns.scatterplot(
    data=data,
    x='Price Difference [€/MWh]',
    y='Flow [MW]',
    s=100,  # Size of dots
    alpha=0.7,  # Transparency (helps if dots overlap)
    edgecolor='black'  # distinct borders
)

