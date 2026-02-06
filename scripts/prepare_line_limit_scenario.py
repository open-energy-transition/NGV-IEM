# SPDX-FileCopyrightText: Contributors to NGV-IEM project
#
# SPDX-License-Identifier: MIT
"""
Uses an already solved network and prepares it for uncertainty analysis by:
* Copying optimised capacities (`p_nom_opt`, `e_nom_opt`, ...) to nominal capacities (`p_nom`, `e_nom`, ...)
* Setting capacity extendable flags to False
* Modifying the network according to the uncertainty scenario, e.g., changing the demand or availability of renewables
"""

import logging

import numpy as np
import pandas as pd
import pypsa

from scripts._helpers import (
    configure_logging,
    set_scenario_config,
    update_config_from_wildcards,
)

logger = logging.getLogger(__name__)


def add_electrolysis_constraints(n):
    """Enforce the electrolysis dispatch to the optimal dispatch found in the solved network."""
    electrolysis_i = n.links[n.links.carrier == "H2 Electrolysis"].index
    n.links_t.p_set.loc[:, electrolysis_i] = n.links_t.p0.loc[:, electrolysis_i]
    return n


def remove_components_added_in_solve_network_py(n: pypsa.Network) -> pypsa.Network:
    """Removes components that were added in solve_network.py; we're planing on running this network through the same step again and want to avoid adding the components again."""

    logger.info("Removing components added in solve_network.py")

    # These components are not always part of the network, so
    # we check for their existence first
    if "co2_sequestration_limit" in n.global_constraints.index:
        n.remove(
            class_name="GlobalConstraint",
            name="co2_sequestration_limit",
        )

    if "load" in n.carriers.index:
        n.remove(
            class_name="Carrier",
            name="load",
        )
        gens_i = n.generators.query("`name`.str.endswith(' load')").index
        n.remove(
            class_name="Generator",
            name=gens_i,
        )

    if "curtailment" in n.carriers.index:
        n.remove(
            class_name="Carrier",
            name="curtailment",
        )
        gens_i = n.generators.query("`name`.str.endswith(' curtailment')").index
        n.remove(
            class_name="Generator",
            name=gens_i,
        )

    return n


def restrict_elec_flows(n: pypsa.Network, line_limits_fp: str) -> pypsa.Network:
    """
    Restrict electricity flows based on pre-calculated hourly line limits from and to GB.

    Restrictions are put in place by limiting `p_min_pu` and `p_max_pu` of each line connected to GB.

    Parameters
    ----------
    n : pypsa.Network
        PyPSA network instance
    line_limits_fp : str
        File path to CSV containing line limits

    Returns
    -------
    pypsa.Network
        PyPSA network instance with restricted line flows
    """
    logger.info(
        "Restricting electricity flows based on line limits from uncertainty scenarios."
    )
    line_limits = pd.read_csv(line_limits_fp, index_col=0, parse_dates=True)
    line_p_max_pu = n.components.links.dynamic["p_max_pu"]
    line_p_min_pu = n.components.links.dynamic["p_min_pu"]

    # Ensure that all lines for which line limits are provided exist in the network
    # (If not, then we are using the wrong input either for the network or the line limits)
    missing_lines = line_limits.columns.difference(n.components.links.static.index)
    if not missing_lines.empty:
        raise ValueError(
            f"The following lines from the line limits file are missing in the network: {missing_lines.tolist()}"
        )

    # Remove existing restrictions that are also part of the `line_limits` if there are any
    # This is not problematic, as the new restrictions are build upon the old restrictions,
    # i.e. the most restrictive limits will apply
    existing_restricted_links = line_limits.columns.intersection(line_p_max_pu.columns)
    if any(existing_restricted_links):
        logger.info(
            f"Removing existing link flow restrictions for GB-connected lines: {existing_restricted_links.tolist()}"
        )
        line_p_max_pu = line_p_max_pu.drop(columns=existing_restricted_links)
        line_p_min_pu = line_p_min_pu.drop(columns=existing_restricted_links)

    # Add new restrictions
    n.components.links.dynamic["p_max_pu"] = pd.concat(
        [line_p_max_pu, line_limits * 1.05], axis="columns"
    )
    n.components.links.dynamic["p_min_pu"] = pd.concat(
        [line_p_min_pu, line_limits * 0.95], axis="columns"
    )

    return n


def restrict_elec_flows_v2(
    n: pypsa.Network,
    line_limits_fp: str,
    explicitly_allocated_lines: list[str],
    lower_bound: float = 0.95,
    upper_bound: float = 1.05,
) -> pypsa.Network:
    """
    Restrict electricity flows based on pre-calculated hourly per-unit line limits for certain links.

    The flows are restricted to an envelope defined by the lower and upper bound multipliers applied to p_min_pu and p_max_pu.

    Parameters
    ----------
    n : pypsa.Network
        PyPSA network instance
    line_limits_fp : str
        File path to CSV containing line limits
    explicitly_allocated_lines : list[str]
        List of regex patterns to match the lines for which the limits should be applied.
        Only these lines matching this pattern will be restricted.
        For each pattern at least one match must be found in the line limits file.
    lower_bound : float
        Lower bound multiplier to apply to the line limits (default: 0.95).
    upper_bound : float
        Upper bound multiplier to apply to the line limits (default: 1.05).
    """

    # Only read the first row, as all rows are identical and we only need the column names
    line_limits = pd.read_csv(
        line_limits_fp,
        index_col=0,
        parse_dates=True,
        nrows=1,
    )

    # Match the existing columns against the configured list
    # using regex match patterns
    matched_columns: list[str] = []
    matches_count: dict[str, int] = {}
    for regex_pattern in explicitly_allocated_lines:
        matches = line_limits.columns[line_limits.columns.str.match(regex_pattern)]
        matched_columns.extend(matches)
        matches_count[regex_pattern] = len(matches)

    # Check that each regex pattern matched at least one column
    for regex_pattern, count in matches_count.items():
        if count == 0:
            raise ValueError(
                f"The line regex pattern '{regex_pattern}' did not match any columns in the line limits file. Please check the pattern and the column names in the file."
            )

    # Load the file again, but only with the matched columns + snapshot column
    line_limits = pd.read_csv(
        line_limits_fp,
        index_col=0,
        parse_dates=True,
        usecols=["snapshot"] + matched_columns,
    )
    links_i = line_limits.columns

    logger.info(
        "Restricting electricity flows based on line limits from uncertainty scenarios for the following explicitly allocated lines: "
        + ", ".join(links_i)
    )
    n.components.links.dynamic["p_min_pu"].loc[line_limits.index, links_i] = np.clip(
        lower_bound * line_limits, 0, 1
    )
    n.components.links.dynamic["p_max_pu"].loc[line_limits.index, links_i] = np.clip(
        upper_bound * line_limits, 0, 1
    )
    return n


def extend_primary_fuel_sources(n):
    primary_fuel_sources = [
        "EU lignite",
        "EU coal",
        "EU oil primary",
        "EU uranium",
        "EU gas",
    ]
    n.generators.loc[primary_fuel_sources, "p_nom_extendable"] = True
    return n


# %%
if __name__ == "__main__":
    if "snakemake" not in globals():
        from scripts._helpers import mock_snakemake

        snakemake = mock_snakemake(
            "prepare_sector_network_myopic_line_limited",
            opts="",
            clusters="all",
            configfiles="config/config.ngv.yaml",
            sector_opts="",
            planning_horizons="2030",
        )
    configure_logging(snakemake)
    set_scenario_config(snakemake)
    update_config_from_wildcards(snakemake.config, snakemake.wildcards)

    n = pypsa.Network(snakemake.input["network"])

    n.optimize.fix_optimal_capacities()
    n = remove_components_added_in_solve_network_py(n)
    n = add_electrolysis_constraints(n)
    n = extend_primary_fuel_sources(n)
    n = restrict_elec_flows_v2(
        n,
        line_limits_fp=snakemake.input["line_limits"],
        explicitly_allocated_lines=snakemake.params["explicitly_allocated_lines"],
        lower_bound=0.95,
        upper_bound=1.05,
    )
    n.name = f"{n.name} status_quo"
    n.export_to_netcdf(snakemake.output["network"])
