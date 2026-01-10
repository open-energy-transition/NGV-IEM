import pypsa
import pandas as pd


#-------- Load solved network -----#
n = pypsa.Network(snakemake.input[0])

def calculate_zonal_opex(n, zone):

    # Filter all electricity suppliers of the country using the energy_balance
    ac_balance_per_bus = n.statistics.energy_balance(bus_carrier="AC", groupby=["bus", "name", "carrier"])
    ac_balance = ac_balance_per_bus.xs(zone, level=1)
    ac_suppliers = ac_balance[ac_balance > 0]

    # Include the offshore hubs of the zone
    ac_balance_per_bus_offshore = n.statistics.energy_balance(bus_carrier="AC_OH", groupby=["bus", "name", "carrier"])
    ac_balance_offshore = ac_balance_per_bus_offshore[ac_balance_per_bus_offshore.index.get_level_values("bus").str.startswith(zone[0:2])]
    ac_suppliers_offshore = ac_balance_offshore[ac_balance_offshore > 0]

    # Exclude DC links
    excluded_carriers = ["DC", "DC_OH"]
    ac_suppliers = ac_suppliers[~ac_suppliers.index.get_level_values("carrier").isin(excluded_carriers)]
    ac_suppliers_offshore = ac_suppliers_offshore[~ac_suppliers_offshore.index.get_level_values("carrier").isin(excluded_carriers)]
    ac_suppliers_offshore = ac_suppliers_offshore.droplevel("bus")

    all_suppliers_data = pd.concat([ac_suppliers, ac_suppliers_offshore])

    # Convert to list, so that we can loop over all components
    ac_suppliers_list = ac_suppliers.index.tolist()
    ac_suppliers_list_offshore = ac_suppliers_offshore.index.tolist()

    ac_suppliers_full_list = ac_suppliers_list_offshore + ac_suppliers_list

    # Extract raw opex of the system (to include both fuel generators and links generators)
    raw_opex = n.statistics.opex()
    raw_opex_detailed = n.statistics.opex(groupby = False)

    # Get CO2 price
    co2_price = - n.stores[n.stores.carrier == "co2"].marginal_cost.mean()

    results = []

    for component_type, name, technology in ac_suppliers_full_list:  #component type = Generator, Link etc. technology = carrier of component (e.g. gas-ocgt, oil-light etc.)


        # Get energy output of each generation technology

        energy_output = all_suppliers_data.loc[(component_type, name, technology)]
        # A. Get the Direct Cost (VOM)
        # ----------------------------
        try:
            direct_opex = raw_opex_detailed.loc[(component_type, name)]
        except KeyError:
            direct_opex = 0.0

        # Initialize variables for this iteration
        indirect_opex = 0.0
        total_opex = direct_opex  # Start with VOM
        input_bus_carrier = "None"
        technology_share = 0.0
        co2_cost = 0.0
        co2_emissions_total = 0.0

        # B. Calculate Indirect Cost (Fuel cost) - ONLY FOR LINKS
        # --------------------------------------------------
        if component_type == "Link":

            # Get CO2 emissions and CO2 cost
            bus2 = n.links.at[name, "bus2"]

            if isinstance(bus2, str) and "co2" in bus2.lower():
                try:
                    co2_emissions_total = -(n.links_t.p2[name].sum())
                    co2_cost = co2_emissions_total * co2_price

                except KeyError:
                    co2_emissions_total = 0.0
                    co2_cost = 0.0

            # GAS TECHNOLOGIES
            if technology in ["gas-ccgt", "gas-ocgt", "gas-ccgt-ccs", "gas-conv", "Open-Cycle Gas"]:
                input_bus_carrier = "gas"
                primary_source = "gas"
                second_primary_source = "biogas"

                # Find total supply of primary fuel
                fuel_balance = n.statistics.energy_balance(bus_carrier=input_bus_carrier, groupby=["name", "carrier"])
                fuel_supply = fuel_balance[fuel_balance > 0].sum()

                # Find share of technology in the consumption of the primary fuel
                technology_share = - fuel_balance.loc[(component_type, name, technology)] / fuel_supply

                # Find amount of CO2 absorbed because of biogas-to-gas process
                process_name = n.links.query("carrier == 'biogas to gas'").index.tolist()[0]
                co2_absorbed = n.links_t.p2[process_name].sum()
                co2_benefits = co2_price * co2_absorbed

                # Get total primary fuel OPEX --> Should include Sabatier process and cost of H2?, but minor impact
                total_fuel_cost = (raw_opex.loc[("Generator", primary_source)]  # fuel cost of EU gas
                                   + raw_opex.loc[("Generator", second_primary_source)]  # fuel cost of EU biogas
                                   + raw_opex.loc[("Link", "biogas to gas")]  # opex of conversion from biogas to gas
                                   - co2_benefits)          # reduction of opex because of co2 absorption in biogas to gas process

                # Get total fuel cost of technology
                indirect_opex = technology_share * total_fuel_cost

                # Calculate total opex of technology
                #total_opex = direct_opex + indirect_opex

            # OIL TECHNOLOGIES
            elif technology in ["oil-heavy", "oil-light", "oil-shale"]:
                input_bus_carrier = "oil"
                primary_source = "oil primary"
                second_primary_source = "solid biomass"

                # Find total supply of primary fuel
                fuel_balance = n.statistics.energy_balance(bus_carrier=input_bus_carrier, groupby=["name", "carrier"])
                fuel_supply = fuel_balance[fuel_balance > 0].sum()

                # Find share of technology in the consumption of the primary fuel
                technology_share = - fuel_balance.loc[(component_type, name, technology)] / fuel_supply

                # Find amount of CO2 absorbed because of biomass to liquid (CC) processes
                process_name_1 = n.links.query("carrier == 'biomass to liquid'").index.tolist()[0]
                process_name_2 = n.links.query("carrier == 'biomass to liquid CC'").index.tolist()[0]
                co2_absorbed_1 = n.links_t.p2[process_name_1].sum()
                co2_absorbed_2 = n.links_t.p2[process_name_2].sum()
                co2_benefits = co2_price * (co2_absorbed_1 + co2_absorbed_2)

                # Find amount of CO2 emitted because of oil refining
                process_name_3 = n.links.query("carrier == 'oil refining'").index.tolist()[0]
                co2_emitted = - n.links_t.p2[process_name_3].sum()
                co2_costs = co2_emitted * co2_price

                # Specifically for the oil, we need to convert to primary oil
                # Get total primary fuel OPEX
                total_fuel_cost = (raw_opex.loc[("Generator", primary_source)]  # fuel cost of EU oil primary
                                   + raw_opex.loc[("Generator", second_primary_source)]  # fuel cost of EU solid biomass
                                   + raw_opex.loc[("Link", "oil refining")]             # opex of conversion from oil primary to oil
                                   + raw_opex.loc[("Link", "biomass to liquid")]        # opex of conversion from biomass to liquid
                                   + raw_opex.loc[("Link", "biomass to liquid CC")]     # opex of conversion from biomass to liquid CC
                                   -  co2_benefits + co2_costs)                         # CO2 costs and benefits from the conversion processes

                # Get total fuel cost of technology
                indirect_opex = technology_share * total_fuel_cost

                # Calculate total opex of technology
                #total_opex = direct_opex + indirect_opex

            # REST OF TECHNOLOGIES (ALL FUEL USED FOR PRODUCTION OF ELECTRICITY)
            elif technology in ["nuclear", "coal", "lignite"]:

                # Map technology to fuel carrier
                if technology == "nuclear":
                    input_bus_carrier = "uranium"

                elif technology == "coal":
                    input_bus_carrier = "coal"  # or "hard coal"

                elif technology == "lignite":
                    input_bus_carrier = "lignite"

                # Find total supply of primary fuel
                fuel_balance = n.statistics.energy_balance(bus_carrier=input_bus_carrier,groupby=["name", "carrier"])
                fuel_supply = fuel_balance[fuel_balance > 0].sum()

                technology_share = - fuel_balance.loc[(component_type, name, technology)] / fuel_supply
                total_fuel_cost = raw_opex.loc[("Generator", input_bus_carrier)]
                indirect_opex = technology_share * total_fuel_cost

            # HYDROGEN TECHNOLOGIES
            elif technology in ["h2-ccgt", "h2-fuel-cell"]:

                input_bus_carrier = "H2"
                #bus0 = zone[0:2] + " H2"
                bus0 = n.links.at[name, "bus0"]
                # Get timeseries of hydrogen consumption of generation unit
                h2_balance_ts = n.statistics.energy_balance(bus_carrier=input_bus_carrier, groupby=["bus", "name", "carrier"], groupby_time= False)
                h2_balance_local = h2_balance_ts.xs(bus0, level=1)
                hydrogen_consumption = - h2_balance_local.loc[(component_type, name, technology)]

                # Alternative way of getting h2 consumption
                #hydrogen_consumption = n.links_t.p0[name]

                # Get timeseries of H2 zonal price
                hydrogen_prices = n.buses_t.marginal_price[bus0]

                # Get fuel cost
                fuel_cost = hydrogen_prices * hydrogen_consumption
                total_fuel_cost = fuel_cost.sum()
                indirect_opex = total_fuel_cost

            # Update Total
            total_opex = direct_opex + indirect_opex + co2_cost

        marginal_cost = (total_opex / energy_output) if energy_output > 1e-6 else 0.0
        co2_cost_per_mwh = (co2_cost/energy_output) if energy_output > 1e-6 else 0.0

        # --- C. Store Result ---
        results.append({
            "Component_Type": component_type,
            "Component": name,
            "Technology": technology,
            "Fuel_Source": input_bus_carrier,
            "Direct_OPEX_MEUR": direct_opex / 1e6,
            "Indirect_Fuel_OPEX_MEUR": indirect_opex / 1e6,
            "Fuel_Share_Pct": technology_share * 100,
            "CO2 emissions [tCO2]": co2_emissions_total,
            "CO2 cost_MEUR": co2_cost/1e6,
            "CO2 cost per MWh": co2_cost_per_mwh,
            "Total_Supply_Cost_MEUR": total_opex / 1e6,
            "Energy_Output_TWh": energy_output/1e6,
            "Marginal Cost_EUR/MWh": marginal_cost,
        })


    # 4. Create DataFrame and Display
    df_granular = pd.DataFrame(results)

    if df_granular.empty:
        return 0.0

    df_aggregated = df_granular.groupby(["Component_Type", "Technology"]).sum(numeric_only=True)

    total_zonal_opex = df_granular["Total_Supply_Cost_MEUR"].sum()

    return total_zonal_opex



def calculate_zonal_revenue(n, zone):

    # Filter all electricity suppliers of the country using the energy_balance
    ac_balance_per_bus = n.statistics.energy_balance(bus_carrier="AC", groupby=["bus", "name", "carrier"])
    ac_balance = ac_balance_per_bus.xs(zone, level=1)
    ac_suppliers = ac_balance[ac_balance > 0]

    # Include the offshore hubs of the zone
    ac_balance_per_bus_offshore = n.statistics.energy_balance(bus_carrier="AC_OH", groupby=["bus", "name", "carrier"])
    ac_balance_offshore = ac_balance_per_bus_offshore[ac_balance_per_bus_offshore.index.get_level_values("bus").str.startswith(zone[0:2])]
    ac_suppliers_offshore = ac_balance_offshore[ac_balance_offshore > 0]

    # Exclude DC links
    excluded_carriers = ["DC", "DC_OH"]
    ac_suppliers = ac_suppliers[~ac_suppliers.index.get_level_values("carrier").isin(excluded_carriers)]
    ac_suppliers_offshore = ac_suppliers_offshore[~ac_suppliers_offshore.index.get_level_values("carrier").isin(excluded_carriers)]
    ac_suppliers_offshore = ac_suppliers_offshore.droplevel("bus")

    all_suppliers_data = pd.concat([ac_suppliers, ac_suppliers_offshore])

    # Convert to list, so that we can loop over all components
    ac_suppliers_list = ac_suppliers.index.tolist()
    ac_suppliers_list_offshore = ac_suppliers_offshore.index.tolist()

    ac_suppliers_full_list = ac_suppliers_list_offshore + ac_suppliers_list

    # Extract raw opex of the system (to include both fuel generators and links generators)
    raw_revenue_detailed = n.statistics.revenue(groupby = False)

    results = []

    for component_type, name, technology in ac_suppliers_full_list:  #component type = Generator, Link etc. technology = carrier of component (e.g. gas-ocgt, oil-light etc.)

        # Get timeseries of power output
        if component_type == "Link":
            power_output_ts = - n.links_t.p1[name]
        elif component_type == "Generator":
            power_output_ts = n.generators_t.p[name]

        # Get total energy output of each generation technology
        energy_output = all_suppliers_data.loc[(component_type, name, technology)]

        # Get revenues of each generation technology
        revenue = raw_revenue_detailed.loc[(component_type, name)]

        # Get zonal price
        zonal_price = n.buses_t.marginal_price[zone]

        # Calculate revenues manually
        revenues_manual = zonal_price * power_output_ts
        revenues_manual_tot = revenues_manual.sum()

        # Calculate revenues per MWh produced
        revenue_per_mwh = (revenue / energy_output) if energy_output > 1e-6 else 0.0

        # --- C. Store Result ---
        results.append({
            "Component_Type": component_type,
            "Component": name,
            "Technology": technology,
            "Total_Revenue_MEUR": revenue / 1e6,
            "Energy_Output_TWh": energy_output / 1e6,
            "Revenue_per_MWh": revenue_per_mwh,
            "Revenue_Manual_MEUR": revenues_manual_tot / 1e6,
        })


    # 4. Create DataFrame and Display
    df_granular = pd.DataFrame(results)

    # In case the zone under study has no AC suppliers and thus no OPEX
    if df_granular.empty:
        return 0.0, 0.0

    df_aggregated = df_granular.groupby(["Component_Type", "Technology"]).sum(numeric_only=True)

    total_zonal_revenue = df_granular["Total_Revenue_MEUR"].sum()
    total_zonal_revenue_manual = df_granular["Revenue_Manual_MEUR"].sum()

    return total_zonal_revenue, total_zonal_revenue_manual



list_of_zones = n.buses[n.buses["carrier"] == 'AC'].index

results_list = []
for zone in list_of_zones:

    zonal_opex = calculate_zonal_opex(n, zone)
    zonal_revenue, zonal_revenue_manual = calculate_zonal_revenue(n, zone)
    zonal_producer_surplus = zonal_revenue_manual - zonal_opex

    results_list.append({
        "Zone": zone,
        "Producer Surplus_MEUR_manual": zonal_producer_surplus,
        "Producer Surplus_MEUR": zonal_revenue
    })

df_results = pd.DataFrame(results_list)
df_results = df_results.set_index("Zone")

df_results.to_csv(snakemake.output[0], index = True)

