# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
# SPDX-FileCopyrightText: Open Energy Transition gGmbH
#
# SPDX-License-Identifier: MIT

import logging

import numpy as np
import pandas as pd

PTDF_PATH = 'data/fbmc/FB domains/FB-Domain-CORE_Full_ERAA2024.xlsx'
YEAR = 2026

def load_ptdf_and_ram_matrices(ptdf_path=PTDF_PATH, year=YEAR):
	ptdf = pd.read_excel(ptdf_path, header=[0,1], sheet_name=f"PTDF_{year}")
	ptdf = ptdf.set_index(ptdf.columns.values[:3].tolist())

	ram = pd.read_excel(ptdf_path, sheet_name=f'RAM_{year}', skiprows=1, index_col=0)
	return ptdf['PTDF*_AHC,SZ'].droplevel(2), ram

def add_fbmc_constraints(n):
	ptdf, ram = load_ptdf_and_ram_matrices()

	flow_map = {}
	for column in ptdf.columns.tolist() + ptdf_nordic.columns.tolist():
	    flow_type = 'Line-s'
	    buses = [column[:2], column[5:7]]
	    buses = ['GB' if bus == 'UK' else bus for bus in buses]
	    idx = n.lines[n.lines.bus0.str.contains(buses[0])][n.lines.bus1.str.contains(buses[1])].index.values
	    if len(idx) == 0:
	        idx = n.lines[n.lines.bus0.str.contains(buses[1])][n.lines.bus1.str.contains(buses[0])].index.values

	    if len(idx) == 0:
	        idx = n.links[n.links.carrier.str.contains('DC')][n.links.bus0.str.contains(buses[0])][n.links.bus1.str.contains(buses[1])].index.values
	        if len(idx) > 0:
	            cnec_type = 'Link-p'

	    # array of the flows through each component of the ptdf (columns)
	    # calls each link/line by name (e.g. Link = 'relation/whatever')
	    flow_vector += [n.model[cnec_type].sel(**{cnec_type[:-2]:idx[:1]})]

	    # obsolete?
	    # flow_map.update({column: {'type':flow_type, 'name':idx[:1],}})


	for cnec in ptdf.loc['summer1'].index.get_level_values(0):
		# only using summer1 as the RAM limit, probably need to build by iterating through the season changes
		rhs = ram['summer1']
		# does this kind of multiplication work?
		lhs = ptdf[cnec] * flow_vector

		n.model.add_constraints(lhs <= rhs, name=f"PTDF-Link")