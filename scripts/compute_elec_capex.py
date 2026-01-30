import pypsa
import pandas as pd


targetdir = '/Users/tpa/MyProjects/NGV-IEM/resources/base_s_all___2030.nc'
targetdir2 = '/Users/tpa/MyProjects/NGV-IEM/resources/base_s_all_lluk__2030.nc'


n_sq = pypsa.Network(targetdir2)
n_iem = pypsa.Network(targetdir)


raw_capex_sq = n_sq.statistics.capex()
raw_capex_iem = n_iem.statistics.capex()

ac_balance_sq = n_sq.statistics.energy_balance(bus_carrier="AC")  #could include AC_OH as well
ac_suppliers_sq = ac_balance_sq[ac_balance_sq > 0]

ac_balance_iem = n_iem.statistics.energy_balance(bus_carrier="AC")  #could include AC_OH as well
ac_suppliers_iem = ac_balance_iem[ac_balance_iem > 0]

clean_index_sq = ac_suppliers_sq.index.droplevel(2)
clean_index_iem = ac_suppliers_iem.index.droplevel(2)

current_items_sq = clean_index_sq.tolist()
current_items_iem = clean_index_iem.tolist()

manual_additions = [
    ('Generator', 'uranium'),
    ('Generator', 'gas'),
    ('Generator', 'coal'),
    ('Generator', 'lignite'),
    ('Generator', 'oil primary'),
]

final_list_sq = list(set(current_items_sq + manual_additions))
final_list_iem = list(set(current_items_iem + manual_additions))

final_index_sq = pd.MultiIndex.from_tuples(
    final_list_sq,
    names=['component', 'name'] # Use 'name' to match raw_capex structure
)

final_index_iem = pd.MultiIndex.from_tuples(
    final_list_iem,
    names=['component', 'name'] # Use 'name' to match raw_capex structure
)

# Now filter
elec_sector_capex_sq = raw_capex_sq[raw_capex_sq.index.isin(final_index_sq)]
elec_sector_capex_iem = raw_capex_iem[raw_capex_iem.index.isin(final_index_iem)]


diff = elec_sector_capex_iem - elec_sector_capex_sq
relative = diff.sum()/ elec_sector_capex_sq.sum()*100

print(elec_sector_capex_sq.sum())
print(elec_sector_capex_iem.sum())
print(diff.sum())
print(relative.sum())
