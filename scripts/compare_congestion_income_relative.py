import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import matplotlib.ticker as mtick

# Global style settings
sns.set_context("talk", font_scale=1.1)


def generate_relative_change_plot(file_sq, file_iem, metric_name, output_filename):
    # 1. Load Data
    df_sq = pd.read_csv(file_sq, index_col=0)
    df_iem = pd.read_csv(file_iem, index_col=0)

    # 2. Aggregate: Time Aggregation (Rows)
    if metric_name == "Price Difference":
        # For Prices, we take the average over the year per line
        total_sq = df_sq.mean(axis=0)
        total_iem = df_iem.mean(axis=0)
    else:
        # For Flow/Income, we take the sum over the year per line
        total_sq = df_sq.sum(axis=0)
        total_iem = df_iem.sum(axis=0)

    # --- NEW: Add "Total GB Interconnections" Column ---
    # We must calculate the totals in ABSOLUTE terms first, then calculate the % change
    total_label = "Total GB Interconnections"

    if metric_name == "Price Difference":
        # System Total for Price = Mean of all borders
        agg_sq = total_sq.mean()
        agg_iem = total_iem.mean()
    else:
        # System Total for Flow/Income = Sum of all borders
        agg_sq = total_sq.sum()
        agg_iem = total_iem.sum()

    # Append the aggregated value to the Series
    total_sq[total_label] = agg_sq
    total_iem[total_label] = agg_iem
    # ---------------------------------------------------

    # 3. Calculate Relative Change (%)
    # Formula: (New - Old) / Old * 100
    # Note: If agg_sq is 0 (unlikely for total), this produces inf/nan.
    relative_diff = ((total_iem - total_sq) / total_sq) * 100

    # 4. Renaming Logic
    rename_map = {}
    for s in relative_diff.index:
        # Exception 1: The new Total Label
        if s == total_label:
            rename_map[s] = "Total"

        # Exception 2: Northern Ireland
        elif "GBNI" in s or "GBNR" in s:
            rename_map[s] = "GB-NIR"

        # Standard Rule
        else:
            short_name = s[:2] + "-" + s[5:7]
            rename_map[s] = short_name

    # Rename the index
    relative_diff = relative_diff.rename(index=rename_map)

    # 5. Plotting Preparation
    # Colors: Green for Increase (>0), Red for Decrease (<0)
    my_colors = ['#2ca02c' if x >= 0 else '#d62728' for x in relative_diff.values]

    # Increase figure width to fit the extra bar
    plt.figure(figsize=(15, 8))

    ax = sns.barplot(
        x=relative_diff.index,
        y=relative_diff.values,
        palette=my_colors,
        edgecolor='black',
        saturation=1
    )

    # Zero Line
    plt.axhline(0, color='black', linestyle='--', linewidth=1.5)

    # Customization
    y_label_str = f"Relative Change in {metric_name} [%]"
    plt.xlabel('Interconnection', fontsize=20, fontweight='bold')
    plt.ylabel(y_label_str, fontsize=18, fontweight='bold')

    if metric_name == "Price Difference":
        plt.title(f'Relative Change in Average {metric_name}\n(IEM vs Status Quo)', fontsize=20, pad=20)
    else:
        plt.title(f'Relative Annual Change in {metric_name}\n(IEM vs Status Quo)', fontsize=20, pad=20)

    # Format Y-Axis as Percentages
    ax.yaxis.set_major_formatter(mtick.PercentFormatter())

    # Add Data Labels on bars
    for i, v in enumerate(relative_diff.values):
        if pd.isna(v):
            continue

        # Dynamic offset logic
        data_range = relative_diff.max() - relative_diff.min()
        offset = data_range * 0.02 if data_range != 0 else 1

        pos = v + offset if v >= 0 else v - offset
        va = 'bottom' if v >= 0 else 'top'

        ax.text(i, pos, f"{v:+.1f}%", ha='center', va=va, fontweight='bold', fontsize=12)

    plt.xticks(rotation=45)
    plt.grid(True, axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()

    plt.savefig(output_filename)
    plt.close()


# --- MAIN EXECUTION BLOCK ---

datasets = [
    (
        snakemake.input.ci_sq,
        snakemake.input.ci_iem,
        'Congestion Income',
        snakemake.output.plot_ci_diff
    ),
    (
        snakemake.input.nf_sq,
        snakemake.input.nf_iem,
        'Net Flow',
        snakemake.output.plot_nf_diff
    ),
    (
        snakemake.input.pd_sq,
        snakemake.input.pd_iem,
        'Price Difference',
        snakemake.output.plot_pd_diff
    ),
]

for f_sq, f_iem, metric, out in datasets:
    generate_relative_change_plot(f_sq, f_iem, metric, out)