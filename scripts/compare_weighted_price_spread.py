import pypsa
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


if "snakemake" in globals():
    df_sq = pd.read_csv(snakemake.input.sq, index_col=0)
    df_iem = pd.read_csv(snakemake.input.iem, index_col=0)
else:
    # For testing purposes
    targetdir = "../results/draft_report/tables/congestion_income_metrics_status_quo_2030.csv"
    targetdir2 = "../results/draft_report/tables/congestion_income_metrics_iem_2030.csv"
    df_sq = pd.read_csv(targetdir, index_col=0)
    df_iem = pd.read_csv(targetdir2, index_col=0)

col_name = "Average Price Difference [Euros/MWh]"
df_diff = (df_iem[col_name] - df_sq[col_name])
df_diff_rel = df_diff / df_sq[col_name] * 100

# 5. Plotting Preparation
# Colors: Green for Increase (>0), Red for Decrease (<0)
my_colors = ['#2ca02c' if x >= 0 else '#d62728' for x in df_diff.values]

# Increase figure width to fit the extra bar
plt.figure(figsize=(15, 8))

ax = sns.barplot(
    x=df_diff.index,
    y=df_diff.values,
    palette=my_colors,
    edgecolor='black',
    saturation=1
)

# 6. Customization
plt.axhline(0, color='black', linestyle='-', linewidth=1.5)

# Labels
y_label_str = "Change in Weighted Average Price spread [Euros/MWh]"
plt.ylabel(y_label_str, fontsize=18, fontweight='bold')
plt.xlabel('Interconnection', fontsize=18, fontweight='bold')


plt.title('Absolute Change in Weighted Average Price Difference \n(IEM - Status Quo)', fontsize=20, pad=20)


# Add Data Labels with Units
for i, v in enumerate(df_diff.values):
    if pd.isna(v):
        continue

    # Dynamic offset logic
    data_range = df_diff.max() - df_diff.min()
    offset = data_range * 0.02 if data_range != 0 else 1

    pos = v + offset if v >= 0 else v - offset
    va = 'bottom' if v >= 0 else 'top'

    label_text = f"{v:+.1f} Euros/MWh"
    ax.text(i, pos, label_text, ha='center', va=va, fontweight='bold', fontsize=12)

plt.xticks(rotation=45)
plt.grid(True, axis='y', linestyle='--', alpha=0.3)

# add labels with relative change
for i, v in enumerate(df_diff_rel.values):
    if pd.isna(v):
        continue

    # Dynamic offset logic
    data_range = df_diff_rel.max() - df_diff_rel.min()
    offset = data_range * 0.02 if data_range != 0 else 1

    pos = df_diff.values[i] + offset if df_diff.values[i] >= 0 else df_diff.values[i] - offset
    va = 'bottom' if df_diff.values[i] >= 0 else 'top'

    label_text = f"({v:+.1f} %)"
    ax.text(i, pos, label_text, ha='center', va=va, fontweight='bold', fontsize=12, color='blue')

plt.tight_layout()

plt.savefig(snakemake.output[0], dpi=300)