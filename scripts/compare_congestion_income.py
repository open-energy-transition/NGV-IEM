import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

#N-side colours
# #00ACC2 = blue
# #F4A74F = yellow/orange
# #8CBB13 = green
# #535F6B = pink
# #D63487 = dark grey

nside_colours = ['#00ACC2', '#F4A74F', '#8CBB13', '#535F6B', '#D63487']
my_palette = {
    "Explicit": "#00ACC2",  # Blue
    "Implicit": "#F4A74F"   # Orange/Yellow
}

def generate_comparison_plot(file_explicit, file_implicit, y_axis_label, output_filename=None):

    # Load Data
    df_ex = pd.read_csv(file_explicit, index_col=0)
    df_im = pd.read_csv(file_implicit, index_col=0)

    # Tag Scenarios
    df_ex['Scenario'] = 'Explicit'
    df_im['Scenario'] = 'Implicit'

    # Combine and Melt
    df_combined = pd.concat([df_ex, df_im])

    # Use the passed y_axis_label as the value_name
    df_long = df_combined.melt(id_vars=['Scenario'],
                               var_name='Interconnection',
                               value_name=y_axis_label)

    # Dynamic Renaming Logic
    original_names = df_ex.columns.drop('Scenario')
    rename_map = {}

    for i, s in enumerate(original_names):
        short_name = s[:2] + "-" + s[5:7]
        rename_map[s] = short_name

    name_at_index_4 = original_names[4]
    rename_map[name_at_index_4] = "GB-NIR"

    df_long['Interconnection'] = df_long['Interconnection'].map(rename_map)

    # Plotting
    plt.figure(figsize=(14, 7))

    sns.boxplot(
        data=df_long,
        x='Interconnection',
        y=y_axis_label,  # CHANGE 2: Tell seaborn to look for the new column name
        hue='Scenario',
        showfliers=True,
        palette=my_palette,
        saturation=1,
    )

    # Customization

    plt.xlabel('Interconnection', fontsize=20, fontweight='bold')
    plt.ylabel(y_axis_label, fontsize=20, fontweight='bold')
    #plt.legend(title='Scenario', fontsize=20, title_fontsize=20)
    leg = plt.legend(title='Scenario', fontsize=20, title_fontsize=20)

    # 2. Make the Title bold
    leg.get_title().set_fontweight('bold')

    # 3. Make the Entries (Explicit/Implicit) bold
    for text in leg.get_texts():
        text.set_fontweight('bold')


    #plt.tick_params(axis='both', which='major', labelsize=20)
    plt.xticks(fontsize=20, fontweight='bold')
    # Set Y-axis ticks (Numbers) to Size 16 and Bold
    plt.yticks(fontsize=20, fontweight='bold')
    plt.tight_layout()


    plt.savefig(output_filename)

# --- MAIN EXECUTION BLOCK ---

# Structure: (File1, File2, Y_Label, Output_Path)
datasets = [
    (
        snakemake.input.ci_sq,
        snakemake.input.ci_iem,
        'Congestion Income [€/h]',
        snakemake.output.plot_ci
    ),
    (
        snakemake.input.nf_sq,
        snakemake.input.nf_iem,
        'Net Flow [MWh]',
        snakemake.output.plot_nf
    ),
    (
        snakemake.input.pd_sq,
        snakemake.input.pd_iem,
        'Price difference [€/MWh]',
        snakemake.output.plot_pd
    ),
]

# Loop through them
for f1, f2, ylabel, out in datasets:
    generate_comparison_plot(f1, f2, ylabel, out)