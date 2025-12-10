import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Global style settings
sns.set_context("talk", font_scale=1.1)


def generate_relative_change_plot(file_sq, file_iem, metric_name, output_filename):
    # 1. Load Data
    df_sq = pd.read_csv(file_sq, index_col=0)
    df_iem = pd.read_csv(file_iem, index_col=0)

    # 2. Calculate Relative Change (%)
    # Formula: (New - Old) / Old * 100
    # Replace 0s with NaN to avoid division by zero errors
    df_pct = ((df_iem - df_sq) / df_sq.replace(0, np.nan)) * 100

    # Clean infinities
    df_pct = df_pct.replace([np.inf, -np.inf], np.nan)

    # 3. Construct the Dynamic Label
    # This creates labels like "Relative Change in Net Flow [%]"
    y_label_str = f"Relative Change in {metric_name} [%]"

    # 4. Melt using the dynamic label
    df_long = df_pct.melt(var_name='Interconnection',
                          value_name=y_label_str)

    # 5. Renaming Logic
    original_names = df_sq.columns
    rename_map = {}
    for i, s in enumerate(original_names):
        short_name = s[:2] + "-" + s[5:7]
        rename_map[s] = short_name

    if len(original_names) > 4:
        rename_map[original_names[4]] = "GB-NIR"

    df_long['Interconnection'] = df_long['Interconnection'].map(rename_map)

    # 6. Plotting
    plt.figure(figsize=(14, 7))

    sns.boxplot(
        data=df_long,
        x='Interconnection',
        y=y_label_str,  # <--- Uses the specific label
        showfliers=False,
        color='#ff7f0e'
    )

    # Zero Line
    plt.axhline(0, color='black', linestyle='--', linewidth=1.5, alpha=0.8)

    # Optional: Limits (Adjust if necessary)
    plt.ylim(-200, 200)

    # Customization
    plt.xlabel('Interconnection', fontsize=20, fontweight='bold')
    plt.ylabel(y_label_str, fontsize=16, fontweight='bold')  # <--- Dynamic Axis Label

    # Dynamic Title
    plt.title(f'Relative Difference in {metric_name}\n(IEM vs Status Quo)', fontsize=18, pad=15)

    plt.xticks(rotation=45)
    plt.tight_layout()

    plt.savefig(output_filename)
    plt.close()


# --- MAIN EXECUTION BLOCK ---

datasets = [
    (
        snakemake.input.ci_sq,
        snakemake.input.ci_iem,
        'Congestion Income',  # <--- This string is now used in Title & Axis
        snakemake.output.plot_ci_diff
    ),
    (
        snakemake.input.nf_sq,
        snakemake.input.nf_iem,
        'Net Flow',  # <--- Becomes "Relative Change in Net Flow [%]"
        snakemake.output.plot_nf_diff
    ),
    (
        snakemake.input.pd_sq,
        snakemake.input.pd_iem,
        'Price Difference',  # <--- Becomes "Relative Change in Price Difference [%]"
        snakemake.output.plot_pd_diff
    ),
]

for f_sq, f_iem, metric, out in datasets:
    generate_relative_change_plot(f_sq, f_iem, metric, out)