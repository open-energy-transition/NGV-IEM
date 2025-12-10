# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
# SPDX-FileCopyrightText: Open Energy Transition gGmbH
#
# SPDX-License-Identifier: MIT

import logging
import re

import pandas as pd
import pypsa

logger = logging.getLogger(__name__)


def load_ptdf(
    fp: str,
    ptdf_type: str,
    sheet_name: str = "PTDF",
    drop_columns_regex: list[str] = [r".*UA.*"],
) -> pd.DataFrame:
    """
    Load PTDF matrix from Excel file.

    PTDF matrix contains the weights for each flow through each
    line/link, by each critical network element component (CNEC).

    Parameters
    ----------
    fp : str
        File path to the Excel file containing the PTDF matrix.
    ptdf_type : str
        Type of PTDF matrix to load. Corresponds to the sheet column names in the Excel file.
        Options for ERAA2023 are "PTDF_SZ", "PTDF*_AHC,SZ" or "PTDF_EvFB".
    sheet_name : str, optional
        Name of the sheet in the Excel file to read the PTDF matrix from.
        Default is "PTDF".
    drop_columns_regex : list[str], optional
        List of regex patterns to identify columns to drop from the PTDF matrix.
        Default is [r".*UA.*"] to drop columns related to Ukraine.
    """

    ptdf: pd.DataFrame = pd.read_excel(fp, header=[0, 1], sheet_name=sheet_name)
    ptdf = ptdf.rename(
        columns={
            "FB_ID": "FB Domain",
            "CNEC_ID": "CNEC_ID",
        }
    )

    # Select the right columns and drop multiindex level
    ptdf = ptdf.loc[
        :,
        [
            (col[0], col[1])
            for col in ptdf.columns.values
            if col[0] in ["Type", ptdf_type]
        ],
    ]
    ptdf = ptdf.droplevel(0, axis=1)

    # Replacement of not-needed columns based on regex patterns
    drop_columns = []
    for regex in drop_columns_regex:
        drop_columns.extend([col for col in ptdf.columns if re.match(regex, col)])
    ptdf = ptdf.drop(columns=drop_columns)

    # Rename columns headers as the PTDF data uses slightly different bus naming than the TYNDP model
    bus_renaming = {
        "GB00": "UK00",
        "DEOH002": "DEKF",  # TODO Check again, DEKF exists in open-TYNDP and in PTDF org data and DEOH002 does not; # uses Hub, for Kriegers Flak (KF) offshore wind park
    }

    ptdf = ptdf.rename(
        columns={
            old_col: old_col.replace(org_bus, new_bus)
            for new_bus, org_bus in bus_renaming.items()
            for old_col in ptdf.columns
            if org_bus in old_col
        }
    )

    # Turn into long format with MultiIndex
    ptdf = ptdf.melt(
        id_vars=["FB Domain", "CNEC_ID"],
        var_name="line",
        value_name="PTDF",
    )

    # Format specific to PTDF type
    if ptdf_type == "PTDF*_AHC,SZ":
        # Split "line" into "from" and "to" bus columns
        ptdf["from"] = ptdf["line"].str.split("-").str[0].str[:4]
        ptdf["to"] = ptdf["line"].str.split("-").str[1].str[:4]

        # Reorder columns
        ptdf = ptdf[["FB Domain", "CNEC_ID", "from", "to", "line", "PTDF"]]
    elif ptdf_type == "PTDF_SZ":
        # columns are per bidding zone already
        ptdf = ptdf.rename(columns={"line": "bidding_zone"})
    elif ptdf_type == "PTDF_EvFB":
        ptdf = ptdf.rename(columns={"line": "virtual_zone"})
    else:
        raise ValueError(f"PTDF type '{ptdf_type}' not recognized.")

    return ptdf


def load_ram(fp: str, sheet_name: str = "RAM_2030") -> pd.DataFrame:
    """
    Load RAM matrix from Excel file.

    RAM matrix defines the remaining available margin per CNEC.

    Parameters
    ----------
    fp : str
        File path to the Excel file containing the RAM matrix.
    sheet_name : str, optional
        Name of the sheet in the Excel file to read the RAM matrix from.
        Default is "RAM_2030" for 2030's RAM values.
    """
    ram = pd.read_excel(fp, sheet_name=sheet_name, skiprows=3)
    ram = ram.melt(id_vars=["CNEC_ID"], var_name="FB Domain", value_name="RAM")

    ram = ram.astype({"FB Domain": int})

    return ram


def load_weather_assignments(
    fp: str,
    sheet_name: str = "FB Domain Assignment",
    snapshots: pd.DatetimeIndex = None,
) -> pd.Series:
    """
    Load weather assignments between FB domains and weather year/timestep from Excel file.

    The RAM values are provided for different weather situations (seasons).
    The mapping between hours of the year and weather year to the RAM values
    is stored separately in the weather assignments.
    This function loads the correct weather assignments for the specified year.

    Parameters
    ----------
    fp : str
        File path to the Excel file containing the weather assignments.
    sheet_name : str, optional
        Name of the sheet in the Excel file to read the weather assignments from.
        Default is "FB Domain Assignment".
    snapshots : pd.DatetimeIndex, optional
        DatetimeIndex of snapshots to filter the weather assignments to.
        If None, all snapshots are returned. Default is None.

    Returns
    -------
    pd.Series
       Series containing the weather assignments for the specified year and of the specified timestep.
    """

    weather_assignments: pd.DataFrame = pd.read_excel(fp, sheet_name=sheet_name)

    # Drop unnecessary columns
    weather_assignments = weather_assignments.drop(columns=["Year"])

    # Rename columns from "CY_<YYYY>" to "<YYYY>" for easier access
    weather_assignments = weather_assignments.rename(
        columns={
            col: col.replace("CY_", "")
            for col in weather_assignments.columns
            if col.startswith("CY_")
        }
    )

    # Turn weather year columns into rows
    weather_assignments = weather_assignments.melt(
        id_vars=["Time_step", "Month", "Day", "Hour"],
        var_name="Year",
        value_name="FB Domain",
    )

    # Counting of hours starts at 1, adjust to start at 0 to create proper datetime index
    weather_assignments["Hour"] = weather_assignments["Hour"] - 1

    # Turn columns into datetime index
    weather_assignments["snapshot"] = pd.to_datetime(
        weather_assignments[["Year", "Month", "Day", "Hour"]]
    )
    weather_assignments = weather_assignments.set_index("snapshot")

    if not snapshots.empty:
        # Select requested timesteps only
        weather_assignments = weather_assignments.loc[snapshots]

    return weather_assignments["FB Domain"]


def add_fbmc_constraints(n: pypsa.Network, fp: str, ram_year: int = 2030) -> None:
    """
    Add the FBMC constraints to the pypsa.Network model.

    Function is currently tailored towards the PTDF matrix and RAM values from ERAA2023,
    can be downloaded from https://eepublicdownloads.blob.core.windows.net/public-cdn-container/clean-documents/sdc-documents/ERAA/2023/FB-Domain-CORE_Merged.xlsx .

    Parameters
    ----------
    n : pypsa.Network
        The pypsa.Network object to which the FBMC constraints will be added.
    fp : str, optional
        File path to the Excel file containing the FBMC data.
        Needs to contain the PTDF matrix, RAM matrix, and weather assignments.
    """

    ram = load_ram(fp, sheet_name=f"RAM_{ram_year}")
    wa = load_weather_assignments(fp, snapshots=n.snapshots)

    # Map RAM values to weather seasons
    ram_snapshoted = (
        wa.to_frame()
        .reset_index()
        .merge(
            ram,
            left_on=["FB Domain"],
            right_on=["FB Domain"],
            how="left",
        )
    )

    # ----------------------------------
    # First part of the FBMC constraint:
    # Flows into and out of CORE bidding zones
    # ----------------------------------

    # load PTDF
    ptdf = load_ptdf(fp, ptdf_type="PTDF_SZ")

    # get flow through links in CORE bidding zones
    
    core_buses = ["AT", # do we need to include buses for offshore DC connections?
        "BE", # probably a neater way to integrate johannes's region map
        "CZ",
        "DE",
        "FR",
        "HR",
        "HU",
        "NL",
        "PL",
        "RO",
        "SK",
        "SI"]

    links = (
        n.components.links.static.query("`carrier`.str.startswith('DC')")[
            ["bus0", "bus1"]
        ]
        .reset_index()
        .rename(columns={"name": "link_name"})
    )
    links_c2c = links[links.bus0.str[:2].isin(core_buses) & links.bus1.str[:2].isin(core_buses)] # core to core buses
    links_c2c['bus0_country'] = links_c2c.bus0.str[:2]
    links_c2c['bus1_country'] = links_c2c.bus1.str[:2]
    links_c2c = links_c2c[links_c2c.bus1_country != links_c2c.bus0_country] # no buses within 1 country

    ptdf['bidding_zone_country'] = ptdf['bidding_zone'].str[:2]

    foo = ptdf.merge(links_c2c, left_on='bidding_zone_country', right_on='bus0_country')
    bar = ptdf.merge(links_c2c, left_on='bidding_zone_country', right_on='bus1_country')
    ptdf = pd.concat([foo, bar])

	# go from FB Domains to snapshots
    ptdf_snapshoted = (
        wa.to_frame()
        .reset_index()
        .merge(
            ptdf,
            left_on=[
                "FB Domain",
            ],
            right_on=[
                "FB Domain",
            ],
            how="left",
        )
    )
	# do the fancy multiplication
    
    ds = (
        ptdf_snapshoted.drop_duplicates(subset=["CNEC_ID", "snapshot", "link_name"])  # Why necessary?
        .set_index(["CNEC_ID", "snapshot", "link_name"])["PTDF"]
        .to_xarray()
    )
    ds = ds.rename({"link_name": "name"})
    
    # Casting to xarray creates NaN values, need to fill those entries with 0
    ds = ds.fillna(0)
    breakpoint()

    lhs_1 = ds * n.model["Link-p"].sel(name=ds["name"])
    # Group by snapshot and CNEC_ID to sum up all contributions to each CNEC at each snapshot
    lhs_1 = lhs_1.sum(dim="name")

    # # add additional constraint for the sum of net positions (NP) to be 0 in CORE bidding zones
    ds = ds.drop_dims('CNEC_ID') # not necessary for flow balance
    nps = ds * n.model["Link-p"].sel(name=ds["name"])
    nps = nps.sum(dim="name")
    n.model.add_constraints(nps == 0, name="net-position-balance")
    # # TODO

    # -----------------------------------
    # Second part of the FBMC constraint:
    # loading from HVDC lines between CORE and outside of CORE
    # -----------------------------------
    ptdf = load_ptdf(fp, ptdf_type="PTDF*_AHC,SZ")

    # Map pypsa.Network links that are related to DC and their names (index) to PTDF line names where bus0=from and bus1=to
    links = (
        n.components.links.static.query("`carrier`.str.startswith('DC')")[
            ["bus0", "bus1"]
        ]
        .reset_index()
        .rename(columns={"name": "link_name"})
    )
    ptdf = ptdf.merge(
        links, left_on=["from", "to"], right_on=["bus0", "bus1"], how="left"
    )

    # Map PTDF values to seasonal values for RAM
    ptdf_snapshoted = (
        wa.to_frame()
        .reset_index()
        .merge(
            ptdf,
            left_on=[
                "FB Domain",
            ],
            right_on=[
                "FB Domain",
            ],
            how="left",
        )
    )

    ds = (
        ptdf_snapshoted.dropna(subset=["link_name"])  # Why necessary?)
        .drop_duplicates(subset=["CNEC_ID", "snapshot", "link_name"])  # Why necessary?
        .set_index(["CNEC_ID", "snapshot", "link_name"])["PTDF"]
        .to_xarray()
    )
    ds = ds.rename({"link_name": "name"})

    # Casting to xarray creates NaN values, need to fill those entries with 0
    ds = ds.fillna(0)

    lhs_2 = ds * n.model["Link-p"].sel(name=ds["name"])
    # Group by snapshot and CNEC_ID to sum up all contributions to each CNEC at each snapshot
    lhs_2 = lhs_2.sum(dim="name")

    # -----------------------------------
    # Third part of the FBMC constraint:
    # loading from HVDC lines within CORE region bidding zones
    # -----------------------------------

    # Load PTDF
    ptdf = load_ptdf(fp, ptdf_type="PTDF_EvFB")

    # Map PTDF to seasonal values for RAM
    ptdf_snapshoted = (
        wa.to_frame()
        .reset_index()
        .merge(
            ptdf,
            on=[
                "FB Domain",
            ],
            how="left",
        )
    )

    # TODO
    # lhs_3 = ...

    rhs = ram_snapshoted.set_index(["CNEC_ID", "snapshot"])["RAM"].to_xarray().fillna(0)

    # Enable lhs_1 and lhs_3 when implemented
    n.model.add_constraints(
        lhs_1 +
        lhs_2
        # + lhs_3
        <= rhs,
        name="PTDF-RAM-constraints",
    )


def modify_network_for_fbmc(n: pypsa.Network) -> pypsa.Network:
    """
    Modify the pypsa.Network for the FBMC implementation.

    The methodology follows the description in ERAA2023.
    This function modified the network and adds additional components that are necessary for the
    evolved FBMC implementation.
    It also assigns some helpful, additional attributes to existing components like buses and links.

    Parameters
    ----------
    n : pypsa.Network
        The pypsa.Network object to be modified for FBMC implementation.

    Returns
    -------
    pypsa.Network
        The modified pypsa.Network object with FBMC implementation.
    """

    # ---------------------------------------------------
    # Add the buses and links required for the Evolved FB
    # ---------------------------------------------------
    logger.info("Adding FBMC evolved FB buses and links to the network.")
    n.add(
        "Bus",
        name="EvFBA1",
    )
    n.add(
        "Bus",
        name="EvFBA2",
    )
    n.add(
        "Bus",
        name="EvFBA3",
    )

    # links between the evolved FB buses
    # capacities from PTDF file, "EvFB_capacities" sheet
    n.add(
        "Link",
        name="EvFBA1-EvFBA2",
        bus0="EvFBA1",
        bus1="EvFBA2",
        p_nom=1e3,
        efficiency=1.0,
        p_min_pu=-1.0,
        p_max_pu=1.0,
    )
    n.add(
        "Link",
        name="EvFBA2-EvFBA3",
        bus0="EvFBA2",
        bus1="EvFBA3",
        p_nom=1e3,
        efficiency=1.0,
        p_min_pu=-1.0,
        p_max_pu=1.0,
    )
    n.add(
        "Link",
        name="EvFBA3-EvFBA1",
        bus0="EvFBA3",
        bus1="EvFBA1",
        p_nom=1e3,
        efficiency=1.0,
        p_min_pu=-1.0,
        p_max_pu=1.0,
    )

    # ----------------------------------------------------
    # Add details on which FBMC region each bus belongs to
    # ----------------------------------------------------
    fbmc_region_mapping = {
        "AT00": "CORE",
        "BE00": "CORE",
        "CZ00": "CORE",
        "DE00": "CORE",
        "FR00": "CORE",
        "HR00": "CORE",
        "HU00": "CORE",
        "NL00": "CORE",
        "PL00": "CORE",
        "RO00": "CORE",
        "SK00": "CORE",
        "SI00": "CORE",
        "EvFBA1": "ALEGRO",
        "EvFBA2": "ALEGRO",
        "EvFBA3": "ALEGRO",
    }

    for bus, region in fbmc_region_mapping.items():
        n.buses.loc[bus, "FBMC_region"] = region

    # Assign links an attribute to indicate which parts of the PTDF they are relevant for
    logger.info("Assigning PTDF types to network links for FBMC implementation.")
    # 1. PTDF_SZ for intra-CORE flows
    core_buses = n.components.buses.static.query("FBMC_region == 'CORE'").index.tolist()
    idx = n.components.links.static[
        (n.components.links.static["bus0"].isin(core_buses))
        & (n.components.links.static["bus1"].isin(core_buses))
    ].index
    n.links.loc[idx, "PTDF_type"] = "PTDF_SZ"
    n.links.loc[idx, "FBMC_zone"] = "CORE"

    # 2. PTDF*_AHC,SZ for flows between CORE and outside of CORE
    idx = n.components.links.static[
        (
            (n.components.links.static["bus0"].isin(core_buses))
            ^ (n.components.links.static["bus1"].isin(core_buses))
        )
        & (n.components.links.static["carrier"].isin(["DC", "DC_OH", "AC"]))
    ].index
    n.links.loc[idx, "PTDF_type"] = "PTDF*_AHC,SZ"
    n.links.loc[idx, "FBMC_zone"] = "CORE-Outside"

    # 3. PTDF_EvFB for flows related to the evolved FB
    idx = n.components.links.static.filter(
        regex=r"^EvFBA\d-EvFBA\d$", axis="index"
    ).index
    n.links.loc[idx, "PTDF_type"] = "PTDF_EvFB"
    n.links.loc[idx, "virtual_zone"] = "ALEGRO"

    return n
