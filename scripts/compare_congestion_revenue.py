import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns


df_status_quo = pd.read_csv(snakemake.input.ci_sq, index_col=0)
df_ex = pd.read_csv(snakemake.input.ci_ex, index_col=0)
df_iem = pd.read_csv(snakemake.input.ci_iem, index_col=0)

# Tag Scenarios
df_status_quo['Scenario'] = 'Explicit Allocation'
df_ex['Scenario'] = 'Explicit Emulation'
df_iem['Scenario'] = 'Implicit Allocation'

pdList = [df_status_quo, df_ex, df_iem]

# Combine and Melt
df_combined = pd.concat(pdList)

# Use the passed y_axis_label as the value_name
df_long = df_combined.melt(id_vars=['Scenario'],
                           var_name='Interconnection',
                           value_name='Congestion Income [€/h]')

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
    y='Congestion Income [€/h]',  # CHANGE 2: Tell seaborn to look for the new column name
    hue='Scenario',
    showfliers=False,
    palette='Set2'
)

# Customization

plt.xlabel('Interconnection', fontsize=20, fontweight='bold')
plt.ylabel('Congestion Income [€/h]', fontsize=20, fontweight='bold')
plt.legend(title='Scenario', fontsize=20, title_fontsize=20)
plt.tight_layout()


plt.savefig(snakemake.output[0], dpi=300)


