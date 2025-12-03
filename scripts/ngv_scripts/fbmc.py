# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
# SPDX-FileCopyrightText: Open Energy Transition gGmbH
#
# SPDX-License-Identifier: MIT

import logging

import numpy as np
import pandas as pd
import xarray as xr

PTDF_PATH = 'data/fbmc/FB-Domain-CORE_Merged.xlsx'
PTDF_PATH_NORDIC = 'data/fbmc/FB domains/FB-Domain-NORDIC_ERAA2024.xlsx'
RAM_YEAR = 2030
WEATHER_YEAR = 2009
SNAPSHOT = 1

def load_ptdf_and_ram_matrices(ptdf_path=PTDF_PATH, ram_year=RAM_YEAR):
	"""
	Loads the PTDF matrix (weights for each flow through each line/link)
	and the RAM vector that defines the max sum of weighted flows in the network
	"""
	ptdf = pd.read_excel(ptdf_path, header=[0,1], sheet_name=f"PTDF")
	ptdf = ptdf.set_index(ptdf.columns.values[:3].tolist())

	ram = pd.read_excel(ptdf_path, sheet_name=f'RAM_{ram_year}', skiprows=3, index_col=0)
	# ram.fillna(np.inf, inplace=True)
	# not sure if we want to use Ukraine?
	ptdf.drop([col for col in ptdf.columns if 'UA' in col], axis=1, inplace=True)

	# # use the sum of the two GB-FR weights
	# ptdf = ptdf.T.groupby(ptdf.columns.str[:9]).sum().T

	return ptdf['PTDF*_AHC,SZ'].droplevel(2), ram

def get_weather_assignments(ptdf_path=PTDF_PATH, weather_year=WEATHER_YEAR, timestep=SNAPSHOT):
	weather_assignments = pd.read_excel(ptdf_path, sheet_name=f"FB Domain Assignment")
	weather_assignments = weather_assignments[f"CY_{weather_year}"]

	return weather_assignments.iloc[::timestep]

def add_fbmc_constraints(n):
	ptdf, ram = load_ptdf_and_ram_matrices()

	pypsa_ptdf_map = {
			'GB00':'UK00',
	    	'DEOH002':'DEKF', # uses Hub, for Kriegers Flak (KF) offshore wind park
	    	'DKW1':'DKKF',
	    	'NOS0':'NOS2'
	    	}

	flow_map = {}
	all_ptdf_cols = ptdf.columns.tolist()
	for column in all_ptdf_cols:
	    # parse the bus names
	    buses = [column[:4], column[5:9]]
	    for k, v in pypsa_ptdf_map.items():
	    	buses = [k if bus == v else bus for bus in buses]
	    idx = n.links[n.links.carrier.str.contains('DC')][n.links.bus0.str.contains(buses[0])][n.links.bus1.str.contains(buses[1])].index.values
	    
	    flow_map.update({column:idx})

	wa = get_weather_assignments()

	seasons = wa.unique()
	# get all indices for hours that align with each weather season
	# breakpoint()
	wa_map = {season:wa[wa==season].index for season in seasons}

	flow_vector = [n.model['Link-p'].sel(Link=flow_map[k]) for k in all_ptdf_cols]

	for season in seasons:
		# in the 2023 merged data not all seasons have the same number of CNECs for some reason
		rhs = ram[str(season)].dropna()
		
		for hr in wa_map[season]:
			# is there a more elegant way to deal with a ValueError? for some reason ptdf.loc * [flow for flow] is failing to do matrix mult
			flow_col = [flow[hr] for flow in flow_vector]

			link_names = ptdf.loc[season].reset_index(drop=True).columns
			flow_vars_series = pd.Series(flow_col, index=link_names)

			

			lhs_series = ptdf.loc[season].reset_index(drop=True).dot(flow_vars_series)
			# In Pdb:
			# 1. Get the list of index tuples
			old_index_values = lhs_series.index.tolist()

			# 2. Extract the second element (the CNEC_ID) from each tuple
			cnec_id_values = [idx[1] if isinstance(idx, tuple) else idx for idx in old_index_values]
			
			# 3. Apply the simple, single-level index back to the Series
			lhs_series.index = cnec_id_values
			rhs_aligned = rhs.reindex(lhs_series.index)
			rhs_aligned.index = cnec_id_values # Use the same list of CNEC_IDs


			lhs_xarray = xr.DataArray(lhs_series)
			rhs_xarray = xr.DataArray(rhs_aligned)
			breakpoint()
			n.model.add_constraints(lhs <= rhs, name=f"PTDF-Link-{season}-{hr}")