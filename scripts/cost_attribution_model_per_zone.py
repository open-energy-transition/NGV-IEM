import pypsa
import pandas as pd

targetdir = '/Users/tpa/MyProjects/NGV-IEM/resources/base_s_all_lluk__2030.nc'

n = pypsa.Network(targetdir)

# Select zone/country
zone = "GB00"


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

        # B. Calculate Indirect Cost (Fuel cost) - ONLY FOR LINKS
        # --------------------------------------------------
        if component_type == "Link":
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

                # Get total primary fuel OPEX --> Should include Sabatier process and cost of H2?, but minor impact
                total_fuel_cost = (raw_opex.loc[("Generator", primary_source)]  # fuel cost of EU gas
                                   + raw_opex.loc[("Generator", second_primary_source)]  # fuel cost of EU biogas
                                   + raw_opex.loc[("Link", "biogas to gas")])  # opex of conversion from biogas to gas

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

                # Specifically for the oil, we need to convert to primary oil
                # Get total primary fuel OPEX
                total_fuel_cost = (raw_opex.loc[("Generator", primary_source)]  # fuel cost of EU oil primary
                                   + raw_opex.loc[("Generator", second_primary_source)]  # fuel cost of EU solid biomass
                                   + raw_opex.loc[("Link", "oil refining")]
                                   + raw_opex.loc[("Link", "biomass to liquid")]
                                   + raw_opex.loc[("Link", "biomass to liquid CC")])

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

            # Update Total
            total_opex = direct_opex + indirect_opex

        marginal_cost = (total_opex / energy_output) if energy_output > 1e-6 else 0.0

        # --- C. Store Result ---
        results.append({
            "Component_Type": component_type,
            "Component": name,
            "Technology": technology,
            "Fuel_Source": input_bus_carrier,
            "Direct_OPEX_MEUR": direct_opex / 1e6,
            "Indirect_Fuel_OPEX_MEUR": indirect_opex / 1e6,
            "Fuel_Share_Pct": technology_share * 100,
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


gb_opex = calculate_zonal_opex(n, zone)

list_of_zones = n.buses[n.buses["carrier"] == 'AC'].index

results_list = []
for zone in list_of_zones:

    zonal_opex = calculate_zonal_opex(n, zone)

    results_list.append({
        "Zone": zone,
        "Total_OPEX_MEUR": zonal_opex
    })

df_results = pd.DataFrame(results_list)