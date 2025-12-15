import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Global style settings
sns.set_context("talk", font_scale=1.1)


def generate_absolute_difference_plot(file_sq, file_iem, metric_name, output_filename, scale_factor=1, unit_label=""):
    # 1. Load Data
    df_sq = pd.read_csv(file_sq, index_col=0)
    df_iem = pd.read_csv(file_iem, index_col=0)

    # 2. Aggregate: Sum over timesteps (axis=0) to get Total Annual Value
    if metric_name == "Price Difference":
        total_sq = df_sq.mean(axis=0)
        total_iem = df_iem.mean(axis=0)
    else:
        total_sq = df_sq.sum(axis=0)
        total_iem = df_iem.sum(axis=0)

    # --- Add "Total GB Interconnections" Column ---
    total_label = "Total GB Interconnections"

    # Calculate the aggregate value across all interconnectors
    if metric_name == "Price Difference":
        # For prices, the "System Total" is the MEAN across all borders
        agg_sq = total_sq.mean()
        agg_iem = total_iem.mean()
    else:
        # For Flow/Income, the "System Total" is the SUM across all borders
        agg_sq = total_sq.sum()
        agg_iem = total_iem.sum()

    # Add this new value to the Series
    total_sq[total_label] = agg_sq
    total_iem[total_label] = agg_iem

    # 3. Calculate Absolute Difference
    # Formula: (IEM - SQ) / Scale Factor
    # Example: If scale_factor is 1e6, we convert Euros to Millions
    abs_diff = (total_iem - total_sq) / scale_factor

    # 4. Renaming Logic
    rename_map = {}
    for s in abs_diff.index:
        # Exception 1: The new Total Label (Keep it as is, or shorten it)
        if s == total_label:
            rename_map[s] = "Total GB"  # Shortening it for the plot

        # Exception 2: Northern Ireland
        elif "GBNI" in s or "GBNR" in s:
            rename_map[s] = "GB-NIR"

        # Standard Rule: Country Codes (e.g. GB00-FR00 -> GB-FR)
        else:
            short_name = s[:2] + "-" + s[5:7]
            rename_map[s] = short_name

    abs_diff = abs_diff.rename(index=rename_map)

    # 5. Plotting Preparation
    # Colors: Green for Increase (>0), Red for Decrease (<0)
    my_colors = ['#2ca02c' if x >= 0 else '#d62728' for x in abs_diff.values]

    # Increase figure width to fit the extra bar
    plt.figure(figsize=(15, 8))

    ax = sns.barplot(
        x=abs_diff.index,
        y=abs_diff.values,
        palette=my_colors,
        edgecolor='black',
        saturation=1
    )

    # 6. Customization
    plt.axhline(0, color='black', linestyle='-', linewidth=1.5)

    # Labels
    y_label_str = f"Change in {metric_name} [{unit_label}]"
    plt.ylabel(y_label_str, fontsize=18, fontweight='bold')
    plt.xlabel('Interconnection', fontsize=18, fontweight='bold')

    if metric_name == "Price Difference":
        plt.title(f'Absolute Change in Average {metric_name}\n(IEM - Status Quo)', fontsize=20, pad=20)
    else:
        plt.title(f'Absolute Annual Change in {metric_name}\n(IEM - Status Quo)', fontsize=20, pad=20)

    # Add Data Labels with Units
    for i, v in enumerate(abs_diff.values):
        if pd.isna(v):
            continue

        # Dynamic offset logic
        data_range = abs_diff.max() - abs_diff.min()
        offset = data_range * 0.02 if data_range != 0 else 1

        pos = v + offset if v >= 0 else v - offset
        va = 'bottom' if v >= 0 else 'top'

        label_text = f"{v:+.1f} {unit_label}"
        ax.text(i, pos, label_text, ha='center', va=va, fontweight='bold', fontsize=12)

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
        snakemake.output.plot_ci_diff,
        1e6,
        'M€'
    ),
    (
        snakemake.input.nf_sq,
        snakemake.input.nf_iem,
        'Net Flow',
        snakemake.output.plot_nf_diff,
        1e3,
        'GWh'
    ),
    (
        snakemake.input.pd_sq,
        snakemake.input.pd_iem,
        'Price Difference',
        snakemake.output.plot_pd_diff,
        1,
        '€/MWh'
    ),
]

for f_sq, f_iem, metric, out, scale, unit in datasets:
    generate_absolute_difference_plot(f_sq, f_iem, metric, out, scale, unit)