import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


if "snakemake" in globals():
    df_imp_sq = pd.read_csv(snakemake.input.imp_sq, index_col=0)
    df_imp_iem = pd.read_csv(snakemake.input.imp_iem, index_col=0)
    df_exp_sq = pd.read_csv(snakemake.input.exp_sq, index_col=0)
    df_exp_iem = pd.read_csv(snakemake.input.exp_iem, index_col=0)
else:
    # For testing purposes
    year = 2030
    df_imp_sq = pd.read_csv(f"../results/draft_report/tables/imports_timeseries_status_quo_{year}.csv", index_col=0)
    df_imp_iem = pd.read_csv(f"../results/draft_report/tables/imports_timeseries_iem_{year}.csv", index_col=0)
    df_exp_sq = pd.read_csv(f"../results/draft_report/tables/exports_timeseries_status_quo_{year}.csv", index_col=0)
    df_exp_iem = pd.read_csv(f"../results/draft_report/tables/exports_timeseries_iem_{year}.csv", index_col=0)

df_imp_diff = df_imp_iem - df_imp_sq
df_exp_diff = df_exp_iem - df_exp_sq

# 5. Plotting Preparation
# Colors: Green for Increase (>0), Red for Decrease (<0)
my_colors = {
    "export": '#2ca02c',
    "import": '#d62728'
}

df_imp_diff["Type"] = "import"
df_exp_diff["Type"] = "export"

col_name = "Traded volume"
df_diff = pd.concat([df_imp_diff, df_exp_diff]).melt(id_vars=["Type"], var_name="Interconnection", value_name=col_name)
df_diff = df_diff.groupby(["Interconnection", "Type"]).sum()

df_imp_sq["Type"] = "import"
df_exp_sq["Type"] = "export"
df_reference = pd.concat([df_imp_sq, df_exp_sq]).melt(id_vars=["Type"], var_name="Interconnection", value_name=col_name)
df_reference = df_reference.groupby(["Interconnection", "Type"]).sum()
df_diff_rel = df_diff / df_reference * 100

# Increase figure width to fit the extra bar
plt.figure(figsize=(15, 8))

ax = sns.barplot(
    data=df_diff,
    x="Interconnection",
    y=col_name,
    hue="Type",
    palette=my_colors
)

# 6. Customization
plt.axhline(0, color='black', linestyle='-', linewidth=1.5)

# Labels
y_label_str = "Change of traded volume [MWh]"
plt.ylabel(y_label_str, fontsize=18, fontweight='bold')
plt.xlabel('Interconnection', fontsize=18, fontweight='bold')

plt.title('Change of GB imports and exports over the year\n(IEM - Status Quo)', fontsize=20, pad=20)

# Add Data Labels with Units
for i, (v, v_rel) in enumerate(zip(df_diff.values, df_diff_rel.values)):
    if pd.isna(v):
        continue

    # Dynamic offset logic
    data_range = df_diff.max() - df_diff.min()
    offset = data_range * 0.02

    pos = v + offset if v >= 0 else v - offset
    va = 'bottom' if v >= 0 else 'top'

    label_text = f"{float(v)/1e3:+.1f} GWh\n({float(v_rel):+.1f} %)"
    ax.text(i/2 - 0.25, pos, label_text, ha='center', va=va, fontweight='bold', fontsize=12)

plt.xticks(rotation=45)
plt.grid(True, axis='y', linestyle='--', alpha=0.3)

plt.savefig(snakemake.output["plot_diff"], dpi=300)