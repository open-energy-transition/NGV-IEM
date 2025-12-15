import pypsa
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.ticker as mtick # Helper for % formatting


#-------- Load solved networks -----#
targetdir = '/Users/tpa/MyProjects/NGV-IEM/resources/base_s_all___2030.nc'
targetdir2 = '/Users/tpa/MyProjects/NGV-IEM/resources/base_s_all_lluk__2030.nc'
n_im = pypsa.Network(targetdir)
n_ex = pypsa.Network(targetdir2)


#------- Filter GB interconnections----------#

GB_ZONE = "GB00"

zonal_interconnections = n_ex.links.query("carrier == 'DC'")

links_gb = zonal_interconnections[
    (zonal_interconnections.bus0 == GB_ZONE) |   # Q: do we include GBNI (Northern Ireland) links with other neighbors as well?
    (zonal_interconnections.bus1 == GB_ZONE)
].index


# Get dispatches for relevant links
links_d_ex = n_ex.components.links.dynamic
flows_ex = links_d_ex["p0"][links_gb]

links_d_im = n_im.components.links.dynamic
flows_im = links_d_im["p0"][links_gb]

capacities_ex = n_ex.links.loc[links_gb, "p_nom_opt"]
capacities_im = n_im.links.loc[links_gb, "p_nom_opt"]

relative_flows_ex = flows_ex.div(capacities_ex)
relative_flows_im = flows_im.div(capacities_im)

tot_flows_im = flows_im.sum(axis = 0)
tot_flows_ex = flows_ex.sum(axis = 0)

relative_difference = (tot_flows_ex - tot_flows_im)/ tot_flows_im *100 # important the sign convention!

average_difference = relative_difference

plt.figure(figsize=(14, 10))
sns.set_context("talk") # Makes fonts and lines larger for reports

# Define Colors: Green for Increase, Red for Decrease
# (You can change these to your specific Hex codes if you want)
my_colors = ['#2ca02c' if x >= 0 else '#d62728' for x in average_difference]

# --- 3. Create the Plot ---
ax = sns.barplot(
    x=average_difference.index,
    y=average_difference,
    palette=my_colors,
    edgecolor='black', # Adds a border to make bars pop
    saturation=1       # Ensures exact color usage
)


# --- 4. Customization ---
# Add a zero line
plt.axhline(0, color='black', linewidth=1.5)

# Format Y-axis as Percentages
ax.yaxis.set_major_formatter(mtick.PercentFormatter())

# Labels and Titles
plt.title('Relative Change in Net Flows (Implicit vs Explicit)', pad=20, fontweight='bold')
plt.xlabel('Interconnector', fontweight='bold')
plt.ylabel('Change in Flow', fontweight='bold')

# Rotate x-labels if you have many interconnectors
plt.xticks(rotation=45)

plt.tight_layout()
# plt.savefig('flow_difference.png')
plt.show()
