import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt


# Load Data
df_ex = pd.read_csv(snakemake.input.sq, index_col=0)
df_im = pd.read_csv(snakemake.input.iem, index_col=0)


#targetdir = '/Users/tpa/MyProjects/NGV-IEM/results/draft_report/tables/total_system_costs_status_quo.csv'
#targetdir2 = '/Users/tpa/MyProjects/NGV-IEM/results/draft_report/tables/total_system_costs_iem.csv'

#df_ex = pd.read_csv(targetdir, index_col=0)
#df_im = pd.read_csv(targetdir2, index_col=0)

zones_of_interest = ['GB00', 'BE00', 'DE00', 'DKW1','FR00', 'GBNI', 'IE00', 'NL00', 'NOS0']

df_ex = df_ex[zones_of_interest]
df_im = df_im[zones_of_interest]

# Tag Scenarios
df_ex['Scenario'] = 'Explicit'
df_im['Scenario'] = 'Implicit'

# Combine and Melt
df_combined = pd.concat([df_ex, df_im])

# Use the passed y_axis_label as the value_name
df_long = df_combined.melt(id_vars=['Scenario'],
                           var_name='Interconnection',
                           value_name='Total System Costs [€/h]')


# Plotting
plt.figure(figsize=(14, 7))

sns.boxplot(
    data=df_long,
    x='Interconnection',
    y='Total System Costs [€/h]',  # CHANGE 2: Tell seaborn to look for the new column name
    hue='Scenario',
    showfliers=False,
    palette='Set2'
)

# Customization

plt.xlabel('Country', fontsize=20, fontweight='bold')
plt.ylabel('Total System Costs [€/h]', fontsize=20, fontweight='bold')
plt.legend(title='Scenario', fontsize=20, title_fontsize=20)
plt.tight_layout()

plt.savefig(snakemake.output[0])


