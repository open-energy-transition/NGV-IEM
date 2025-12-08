# SPDX-FileCopyrightText: Contributors to PyPSA-Eur <https://github.com/pypsa/pypsa-eur>
# SPDX-FileCopyrightText: Open Energy Transition gGmbH
#
# SPDX-License-Identifier: MIT

import re

import pandas as pd
import pypsa

PTDF_PATH = "data/ngv_iem/FB-Domain-CORE_Merged.xlsx"
RAM_YEAR = 2030

def load_ptdf(
    fp: str, sheet_name: str = "PTDF", drop_columns_regex: list[str] = [r".*UA.*"]
) -> pd.DataFrame:
    """
    Load PTDF matrix from Excel file.

    PTDF matrix contains the weights for each flow through each
    line/link, by each critical network element component (CNEC).

    Parameters
    ----------
    fp : str
        File path to the Excel file containing the PTDF matrix.
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
            if col[0] in ["Type", "PTDF*_AHC,SZ"]
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

    # Split "line" into "from" and "to" bus columns
    ptdf["from"] = ptdf["line"].str.split("-").str[0].str[:4]
    ptdf["to"] = ptdf["line"].str.split("-").str[1].str[:4]

    # Reorder columns
    ptdf = ptdf[["FB Domain", "CNEC_ID", "from", "to", "line", "PTDF"]]

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


def add_fbmc_constraints(n: pypsa.Network, fp: str = PTDF_PATH) -> None:
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

    ptdf = load_ptdf(fp)
    ram = load_ram(fp, sheet_name=f"RAM_{RAM_YEAR}")
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

    lhs = ds * n.model["Link-p"].sel(name=ds["name"])
    # Group by snapshot and CNEC_ID to sum up all contributions to each CNEC at each snapshot
    lhs = lhs.sum(dim="name")

    rhs = ram_snapshoted.set_index(["CNEC_ID", "snapshot"])["RAM"].to_xarray().fillna(0)

    n.model.add_constraints(lhs <= rhs, name="PTDF-RAM-constraints")
