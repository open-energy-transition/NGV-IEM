import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Global style settings
sns.set_context("talk", font_scale=1.1)


def generate_difference_plot(file_sq, file_iem, y_axis_label, output_filename):
    # 1. Load Data
    df_sq = pd.read_csv(file_sq, index_col=0)
    df_iem = pd.read_csv(file_iem, index_col=0)

    # 2. Calculate Difference (IEM - Status Quo)
    # This assumes both dataframes have identical index (Time) and columns (Interconnectors)
    df_diff = df_iem - df_sq

    # 3. Melt the Difference Dataframe
    # We no longer need a 'Scenario' column because we have only one set of values
    df_long = df_diff.melt(var_name='Interconnection',
                           value_name=y_axis_label)

    # 4. Dynamic Renaming Logic (Same as before)
    # We use df_sq.columns just to get the names
    original_names = df_sq.columns
    rename_map = {}

    for i, s in enumerate(original_names):
        short_name = s[:2] + "-" + s[5:7]
        rename_map[s] = short_name

    # Exception for the 5th element (Index 4)
    if len(original_names) > 4:
        name_at_index_4 = original_names[4]
        rename_map[name_at_index_4] = "GB-NIR"

    df_long['Interconnection'] = df_long['Interconnection'].map(rename_map)

    # 5. Plotting
    plt.figure(figsize=(14, 7))

    # Single box per x-tick (no hue needed)
    sns.boxplot(
        data=df_long,
        x='Interconnection',
        y=y_axis_label,
        showfliers=False,
        color='#1f77b4'  # You can pick a neutral color like SteelBlue
    )

    # Add a Zero Line (Critical for difference plots)
    plt.axhline(0, color='black', linestyle='--', linewidth=1.5, alpha=0.8)

    # Customization
    plt.xlabel('Interconnection', fontsize=20, fontweight='bold')
    plt.ylabel(y_axis_label, fontsize=20, fontweight='bold')
    plt.title('Difference (IEM - Status Quo)', fontsize=18, pad=15)

    plt.xticks(rotation=45)  # Often needed if names are long
    plt.tight_layout()

    # Save
    plt.savefig(output_filename)
    plt.close()  # Close memory


# --- MAIN EXECUTION BLOCK ---

datasets = [
    (
        snakemake.input.ci_sq,
        snakemake.input.ci_iem,
        'Change in Congestion Income [€/h]',
        snakemake.output.plot_ci_diff
    ),
    (
        snakemake.input.nf_sq,
        snakemake.input.nf_iem,
        'Change in Net Flow [MWh]',
        snakemake.output.plot_nf_diff
    ),
    (
        snakemake.input.pd_sq,
        snakemake.input.pd_iem,
        'Change in Price Diff [€/MWh]',
        snakemake.output.plot_pd_diff
    ),
]

for f_sq, f_iem, ylabel, out in datasets:
    generate_difference_plot(f_sq, f_iem, ylabel, out)