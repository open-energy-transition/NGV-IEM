# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
# SPDX-FileCopyrightText: Open Energy Transition gGmbH
#
# SPDX-License-Identifier: MIT

import logging

import numpy as np
import pandas as pd

PTDF_PATH = 'data/fbmc/FB domains/FB-Domain-CORE_Full_ERAA2024.xlsx'
PTDF_PATH_NORDIC = 'data/fbmc/FB domains/FB-Domain-NORDIC_ERAA2024.xlsx'
YEAR = 2026
SNAPSHOT = 6
WEATHER_SCENARIO = 'WS1'

def load_ptdf_and_ram_matrices(ptdf_path=PTDF_PATH, ptdf_path_nordic=PTDF_PATH_NORDIC, year=YEAR):
	"""
	Loads the PTDF matrix (weights for each flow through each line/link)
	and the RAM vector that defines the max sum of weighted flows in the network
	"""
	ptdf = pd.read_excel(ptdf_path, header=[0,1], sheet_name=f"PTDF_{year}")
	ptdf_nordic = pd.read_excel(ptdf_path_nordic, header=[0,1], sheet_name=f'PTDF_{year}')
	ptdf = ptdf.set_index(ptdf.columns.values[:3].tolist())

	ram = pd.read_excel(ptdf_path, sheet_name=f'RAM_{year}', skiprows=1, index_col=0)

	# not sure if we want to use Ukraine?
	ptdf.drop([col for col in ptdf.columns if 'UA' in col], axis=1, inplace=True)

	# # use the sum of the two GB-FR weights
	# ptdf = ptdf.T.groupby(ptdf.columns.str[:9]).sum().T

	return ptdf['PTDF*_AHC,SZ'].droplevel(2), ptdf_nordic['PTDF*_AHC,SZ'], ram

def get_weather_assignments(ptdf_path=PTDF_PATH, year=YEAR):
	weather_assignments = pd.read_excel(ptdf_path, sheet_name=f"FB Domain Assignment")
	weather_assignments = weather_assignments[weather_assignments.Year == year]

	return weather_assignments.iloc[::SNAPSHOT][WEATHER_SCENARIO]

def add_fbmc_constraints(n):
	ptdf, ptdf_nordic, ram = load_ptdf_and_ram_matrices()

	pypsa_ptdf_map = {
			'GB00':'UK00',
	    	'DEOH002':'DEKF', # uses Hub, for Kriegers Flak (KF) offshore wind park
	    	'DKW1':'DKKF',
	    	'NOS0':'NOS2'
	    	}

	flow_map = {}
	all_ptdf_cols = ptdf.columns.tolist() + ptdf_nordic.columns.tolist()
	for column in all_ptdf_cols:
	    # parse the bus names
	    buses = [column[:4], column[5:9]]
	    for k, v in pypsa_ptdf_map.items():
	    	buses = [k if bus == v else bus for bus in buses]
	    idx = n.links[n.links.carrier.str.contains('DC')][n.links.bus0.str.contains(buses[0])][n.links.bus1.str.contains(buses[1])].index.values
	    
	    flow_map.update({column:idx})

	wa = get_weather_assignments()
	wa_nordic = get_weather_assignments(ptdf_path=PTDF_PATH_NORDIC)

	seasons = wa.unique()
	# get all indices for hours that align with each weather season
	wa_map = {season:wa[wa==season].index for season in seasons}
	wa_map.update({season:wa_nordic[wa_nordic==season].index for season in seasons})

	flow_vector = [n.model['Link-p'].sel(Link=flow_map[k]) for k in all_ptdf_cols]

	for season in seasons:
		for cnec in ptdf.loc[season].index.get_level_values(0):
			rhs = ram[season]
			
			for hr in wa_map[season]:
				lhs = ptdf.loc[season] * np.array([flow[hr] for flow in flow_vector]) 

				n.model.add_constraints(lhs <= rhs, name=f"PTDF-Link-{season}-{hr}")