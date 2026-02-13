# SPDX-FileCopyrightText: Contributors to NGV-IEM project
#
# SPDX-License-Identifier: MIT
"""
Extract results from uncertainty scenarios and consolidates them.

Consolidation yields single values for all interconnections, to be used for restricting flows exogenously.
"""

import logging

import pandas as pd
import pypsa

from scripts._helpers import (
    configure_logging,
    set_scenario_config,
)

logger = logging.getLogger(__name__)


if __name__ == "__main__":
    if "snakemake" not in globals():
        from scripts._helpers import mock_snakemake

        snakemake = mock_snakemake(
            "extract_uncertainty_results",
            clusters="all",
            sector_opts="",
            planning_horizons=2030,
            configfiles="config/config.ngv.yaml",
        )
    configure_logging(snakemake)
    set_scenario_config(snakemake)

    dispatches = []
    for n_fp in snakemake.input.networks:
        n = pypsa.Network(n_fp)

        # Extract all relevant links, DC and DC_OH (offshore hubs),
        # that are connected with one port to GB and the other port to another country (not GB)
        connection_types = snakemake.params["explicit_allocation"]["connection_types"]
        from_to_bus = snakemake.params["explicit_allocation"]["to_from"]

        links_s = n.components.links.static
        relevant_links = links_s.loc[
            (links_s["carrier"].isin(connection_types))
            & (
                (links_s["bus0"].str.startswith(from_to_bus))
                ^ (links_s["bus1"].str.startswith(from_to_bus))
            )
        ].index

        # Get dispatches for relevant links
        links_d = n.components.links.dynamic
        links_d = links_d["p0"][relevant_links]

        dispatches.append(links_d)

    # Consolidate the results of the different scenarios by averaging
    # TODO: Need to rethink method of aggregation
    combined = pd.concat(dispatches, axis=1)
    consolidated = combined.T.groupby(level=0).mean().T

    # Calculate line limits on a p.u. basis relative to the capacity of each link
    capacities = n.links.loc[consolidated.columns, "p_nom_opt"]
    consolidated = consolidated.div(capacities, axis=1)

    # Set small values that are close to 0 (negative and positive) to 0
    consolidated = consolidated.where(lambda x: x.abs() > 1e-4, 0)

    # In case of 0 capacity, set to 0 to avoid NaN values
    consolidated = consolidated.fillna(0)

    # Save to CSV
    consolidated.to_csv(snakemake.output["line_limits"])
