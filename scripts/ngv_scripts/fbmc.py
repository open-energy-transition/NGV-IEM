# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
# SPDX-FileCopyrightText: Open Energy Transition gGmbH
#
# SPDX-License-Identifier: MIT

import logging

import numpy as np
import pandas as pd

PTDF_PATH = 'data/fbmc/FB domains/FB-Domain-CORE_Full_ERAA2024.xlsx'
YEAR = 2026
SNAPSHOT = 6
WEATHER_SCENARIO = 'WS1'

def load_ptdf_and_ram_matrices(ptdf_path=PTDF_PATH, year=YEAR):
	"""
	Loads the PTDF matrix (weights for each flow through each line/link)
	and the RAM vector that defines the max sum of weighted flows in the network
	"""
	ptdf = pd.read_excel(ptdf_path, header=[0,1], sheet_name=f"PTDF_{year}")
	ptdf = ptdf.set_index(ptdf.columns.values[:3].tolist())

	ram = pd.read_excel(ptdf_path, sheet_name=f'RAM_{year}', skiprows=1, index_col=0)

	ptdf.drop([col for col in ptdf.columns if 'UA' in col], axis=1, inplace=True)

	return ptdf['PTDF*_AHC,SZ'].droplevel(2), ram

def get_weather_assignments(ptdf_path=PTDF_PATH, year=YEAR):
	weather_assignments = pd.read_excel(ptdf_path, sheet_name=f"FB Domain Assignment")
	weather_assignments = weather_assignments[weather_assignments.Year == year]

	return weather_assignments.iloc[::SNAPSHOT][WEATHER_SCENARIO]

def add_fbmc_constraints(n):
	ptdf, ram = load_ptdf_and_ram_matrices()

	flow_map = {}
	for column in ptdf.columns.tolist() + ptdf_nordic.columns.tolist():
	    # parse the bus names
	    buses = [column[:4], column[5:9]]
	    buses = ['GB00' if bus == 'UK00' else bus for bus in buses]
	    buses = ['DEOH002' if bus == 'DEKF' else bus for bus in buses] # uses Hub, for Kriegers Flak (KF) offshore wind park
	    buses = ['NOS0' if bus == 'NOS2' else bus for bus in buses]
	    buses = ['DKW1' if bus == 'DKKF' else bus for bus in buses]
	    idx = n.links[n.links.carrier.str.contains('DC')][n.links.bus0.str.contains(buses[0])][n.links.bus1.str.contains(buses[1])].index.values
	    
	    if len(idx) == 0:
	        idx = n.links[n.links.carrier.str.contains('DC')][n.links.bus0.str.contains(buses[1])][n.links.bus1.str.contains(buses[0])].index.values
	    flow_map.update({column:idx})

	wa = get_weather_assignments()
	seasons = wa.unique()
	# get all indices for hours that align with each weather season
	wa_map = {season:weather_assignments[weather_assignments==season].index for season in seasons}

	for season in seasons:
		for cnec in ptdf.loc[season].index.get_level_values(0):
			rhs = ram[season]
			
			for hr in wa_map[season]:
				lhs = ptdf.loc[season] * np.array([flow[hr] for flow in flow_vector]) 

				n.model.add_constraints(lhs <= rhs, name=f"PTDF-Link-{season}-{hr}")