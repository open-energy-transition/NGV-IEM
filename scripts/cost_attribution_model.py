import pypsa
import pandas as pd

targetdir = '/Users/tpa/MyProjects/NGV-IEM/resources/base_s_all_lluk__2030.nc'

n = pypsa.Network(targetdir)

# Extract raw opex of the system (to include both fuel generators and links generators)
raw_opex = n.statistics.opex()

# Filter all electricity suppliers using the energy_balance
ac_balance = n.statistics.energy_balance(bus_carrier="AC")
ac_suppliers = ac_balance[ac_balance > 0]
clean_index_sq = ac_suppliers.index.droplevel(2)

# Convert to list, so that we can loop over all technologies
ac_suppliers_list = clean_index_sq.tolist()

results = []

for component_type, technology in ac_suppliers_list:  #component type = Generator, Link etc. technology = carrier of component (e.g. gas-ocgt, oil-light etc.)

    # A. Get the Direct Cost (VOM)
    # ----------------------------
    try:
        direct_opex = raw_opex.loc[(component_type, technology)]
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

            # Find total supply of primary fuel
            fuel_balance = n.statistics.energy_balance(bus_carrier=input_bus_carrier)
            fuel_supply = fuel_balance[fuel_balance > 0].sum() # should we calculate it based solely on the supply from the EU gas generator maybe?
            technology_consumption = - fuel_balance.loc[(component_type, technology, input_bus_carrier)] #change of sign, because the technology consumes fuel
            # Find share of technology in the consumption of the primary fuel
            technology_share = technology_consumption / fuel_supply

            # Get total primary fuel OPEX
            total_fuel_cost = raw_opex.loc[("Generator", primary_source)] # here we would need to add the cost of producing gas from biomgas etc.

            # Get total fuel cost of technology
            indirect_opex = technology_share * total_fuel_cost

            # Calculate total opex of technology
            total_opex = direct_opex + indirect_opex

        # OIL TECHNOLOGIES
        elif technology in ["oil-heavy", "oil-light", "oil-shale"]:
            input_bus_carrier = "oil"
            primary_source = "oil primary"

            # Find total supply of primary fuel
            fuel_balance = n.statistics.energy_balance(bus_carrier=input_bus_carrier)
            fuel_supply = fuel_balance[fuel_balance > 0].sum()
            technology_consumption = - fuel_balance.loc[(component_type, technology, input_bus_carrier)]  # change of sign, because the technology consumes fuel
            # Find share of technology in the consumption of the primary fuel
            technology_share = technology_consumption / fuel_supply

            # Specifically for the oil, we need to convert to primary oil
            # Get total primary fuel OPEX
            total_fuel_cost = raw_opex.loc[("Generator", primary_source)] # here we would need to add the cost of producing oil from biomass etc.

            # Get total fuel cost of technology
            indirect_opex = technology_share * total_fuel_cost

            # Calculate total opex of technology
            total_opex = direct_opex + indirect_opex

        # REST OF TECHNOLOGIES (ALL FUEL USED FOR PRODUCTION OF ELECTRICITY)
        elif technology in ["nuclear", "coal", "lignite"]:

            # Map technology to fuel carrier
            if technology == "nuclear":
                input_bus_carrier = "uranium"

            elif technology == "coal":
                input_bus_carrier = "coal"  # or "hard coal"

            elif technology == "lignite":
                input_bus_carrier= "lignite"

            technology_share = 1
            total_fuel_cost = raw_opex.loc[("Generator", input_bus_carrier)]
            indirect_opex = technology_share * total_fuel_cost

    # Update Total
    total_opex = direct_opex + indirect_opex

    # --- C. Store Result ---
    results.append({
        "Component": component_type,
        "Technology": technology,
        "Fuel_Source": input_bus_carrier,
        "Direct_OPEX_MEUR": direct_opex / 1e6,
        "Indirect_Fuel_OPEX_MEUR": indirect_opex / 1e6,
        "Fuel_Share_Pct": technology_share * 100,
        "Total_Supply_Cost_MEUR": total_opex / 1e6
    })

# 4. Create DataFrame and Display
df_results = pd.DataFrame(results)
