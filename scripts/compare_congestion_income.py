import pandas as pd
import matplotlib.pyplot as plt
import os

from enum import StrEnum


class Scenario(StrEnum):
    STATUS_QUO = Scenario.STATUS_QUO
    IEM = Scenario.IEM



df_status_quo = pd.read_csv(snakemake.input.status_quo, index_col=0)  # Series: index=interconnections
df_iem = pd.read_csv(snakemake.input.iem, index_col=0)


# --- Ensure both scenarios have the same interconnections order ---
intercons = df_status_quo.index
df2 = df_iem.loc[intercons]

bar_df = pd.DataFrame({
    Scenario.STATUS_QUO: df_status_quo["Total annual congestion income [M€]"],
    Scenario.IEM: df_iem["Total annual congestion income [M€]"]
})

# --- Plot ---
fig, ax = plt.subplots(figsize=(10, 6))

bar_width = 0.35
x = range(len(bar_df))

# Bars for Scenario 1
ax.bar([i - bar_width/2 for i in x], bar_df[Scenario.STATUS_QUO], width=bar_width, label=Scenario.STATUS_QUO, )

# Bars for Scenario 2
ax.bar([i + bar_width/2 for i in x], bar_df[Scenario.IEM], width=bar_width, label=Scenario.IEM, )

# Outer bar (Status Quo)
#ax.bar(x, bar_df[Scenario.STATUS_QUO], width=0.5, label=Scenario.STATUS_QUO, color="skyblue")

# Inner bar (IEM) slightly narrower
#ax.bar(x, bar_df[Scenario.IEM], width=0.3, label=Scenario.IEM, color="salmon")

# Labels
short_labels = [s[:2] + "-" + s[5:7] for s in bar_df.index]
short_labels[5] = "GB-GBNR"
ax.set_xticks(x)
#ax.set_xticklabels(bar_df.index, rotation=45, ha="right")
ax.set_xticklabels(short_labels, rotation=45, ha="right")
ax.set_ylabel("Congestion Income (M €)")
ax.set_title("Congestion Income per Interconnection")
ax.legend()
ax.grid(axis="y", linestyle="--", alpha=0.7)

# --- Save figure ---
plt.tight_layout()
plt.savefig(snakemake.output[0], dpi=300)

