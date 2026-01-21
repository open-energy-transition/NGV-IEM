from typing import Callable, Any, Optional, Dict
import pypsa
import pandas as pd
from functools import wraps
from dataclasses import dataclass

MAP_NON_RENEWABLES = {
    "lignite": False,
    "coal": False,
    "oil-heavy": False,
    "oil-light": False,
    "oil-shale": False,
    "nuclear": False,
    "co2": False,
    "Open-Cycle Gas": False,
    "gas-ccgt": False,
    "gas-ccgt-ccs": False,
    "gas-ccgt-conv": False,
    "gas-ccgt-ocgt": False,
    "h2-ccgt": False,
    "h2-fuel-cell": False,
    "H2": False,
}
EXPLICIT_BORDERS = ["BE00", "DE00", "DKW1", "FR00", "NL00"]
# border_map = {idx: next((b for b in borders if b in idx)) for idx in netflow_diff.index.get_level_values(1)}
# flow_diff["border"] = flow_diff.index.get_level_values(1).map(border_map)
# flow_diff = flow_diff.groupby("border").sum()


class NetworkSelector:

    def __init__(self, n_tf: pypsa.Network, n_sq: pypsa.Network, n_iem: pypsa.Network):
        self.n_tf = n_tf  # trader forecast (with forecast errors)
        self.n_sq = n_sq  # status quo (cross-border GB flows constrained by tf flows)
        self.n_iem = n_iem  # iem scenario (implicit coupling)

    def get_sq(self) -> pypsa.Network:
        return self.n_sq

    def get_iem(self) -> pypsa.Network:
        return self.n_iem

    def get_tf(self) -> pypsa.Network:
        return self.n_tf

    def get_iem_and_sq(self) -> tuple[pypsa.Network, pypsa.Network]:
        return self.n_iem, self.n_sq


def metric(func: Callable[..., Any]):
    """Decorator that turns a (self, network)->value method into a property returning
    a bound metric object with .sq(), .iem(), .tf(), .diff() and callable behavior.

    Chosen usage (clear and unambiguous):
      - results.revenue.iem(**kwargs)        # pass kwargs to underlying n.statistics.* call
      - results.revenue(n, **kwargs)         # compute metric for explicit network n with kwargs
    Not supported:
      - results.revenue(**kwargs)            # ambiguous: kwargs without explicit network

    This keeps configuration explicit (kwargs provided where the computation happens).
    """

    @property
    @wraps(func)
    def _prop(instance: "ResultsComputer"):
        # bound function (n, **kwargs) -> func(instance, n, **kwargs)
        def bound_fn(n: pypsa.Network, **kwargs):
            return func(instance, n, **kwargs)

        class _BM:
            def __init__(self, rc: "ResultsComputer", f: Callable[[pypsa.Network, Any], Any],
                         saved_kwargs: Optional[Dict] = None):
                self._rc = rc
                self._f = f
                # saved_kwargs is not used by external callers in this design, but keep for internal convenience
                self._saved_kwargs = dict(saved_kwargs) if saved_kwargs else {}

            def sq(self, **kwargs):
                return self._rc._sq(lambda n: self._f(n, **kwargs))

            def iem(self, **kwargs):
                return self._rc._iem(lambda n: self._f(n, **kwargs))

            def tf(self, **kwargs):
                return self._rc._tf(lambda n: self._f(n, **kwargs))

            def diff(self, **kwargs):
                return self._rc._diff(lambda n: self._f(n, **kwargs))

            def compare(self, **kwargs):
                return self._rc._compare(lambda n: self._f(n, **kwargs))

            def __call__(self, *args, **kwargs):
                # Allowed: called with a Network (optionally with kwargs) -> compute and return result
                if args:
                    n = args[0]
                    combined = self._combine(kwargs)
                    return self._f(n, **combined)
                # Disallow: kwargs without a Network -> ambiguous usage
                if kwargs:
                    raise TypeError(
                        "Passing kwargs to the metric property without a Network is not supported. "
                        "Use .iem(**kwargs) / .sq(**kwargs) / .tf(**kwargs) or call the metric with a Network: "
                        "results.revenue(n, **kwargs)"
                    )
                # No args/kwargs -> return self (no-op), allowing chaining like results.revenue.iem()
                return self

        return _BM(instance, bound_fn)

    return _prop


class ResultsComputer:
    """Compact results computer: expose metrics by decorating methods with @metric.

    Example:
      @metric
      def revenue(self, n):
          return n.statistics.revenue()

    Callers can use: res.revenue.iem(**kwargs), res.revenue.diff(), res.revenue.sq(), res.revenue(n, **kwargs)
    """

    def __init__(self, n_tf: pypsa.Network, n_sq: pypsa.Network, n_iem: pypsa.Network):
        self.ns = NetworkSelector(n_tf=n_tf, n_sq=n_sq, n_iem=n_iem)

    # small helpers used by the bound-metric object
    def _sq(self, func: Callable[[pypsa.Network], Any]):
        return func(self.ns.get_sq())

    def _iem(self, func: Callable[[pypsa.Network], Any]):
        return func(self.ns.get_iem())

    def _tf(self, func: Callable[[pypsa.Network], Any]):
        return func(self.ns.get_tf())

    def _diff(self, func: Callable[[pypsa.Network], Any]):
        n_iem, n_sq = self.ns.get_iem_and_sq()
        return func(n_iem) - func(n_sq)

    def _compare(self, func: Callable[[pypsa.Network], Any]):
        return pd.concat({
            'iem': self._iem(func),
            'sq': self._sq(func),
            'diff': self._diff(func),
            'tf': self._tf(func)
        }, axis=1)

    @metric
    def revenue(self, n: pypsa.Network, **kwargs):
        """PyPSA.statistics - Total component revenues for a network."""
        return n.statistics.revenue(**kwargs)

    @metric
    def prices(self, n: pypsa.Network, **kwargs):
        """PyPSA.statistics - Average price difference across all interconnectors for a network."""
        return n.statistics.prices(**kwargs)

    @metric
    def curtailment(self, n: pypsa.Network, **kwargs):
        """PyPSA.statistics - Total curtailment of renewable generation for a network."""
        return n.statistics.curtailment(**kwargs)

    @metric
    def system_cost(self, n: pypsa.Network, **kwargs):
        """PyPSA.statistics - Total system cost for a network."""
        return n.statistics.system_cost(**kwargs)

    @metric
    def capex(self, n: pypsa.Network, **kwargs):
        """PyPSA.statistics - Total system cost for a network."""
        return n.statistics.capex(**kwargs)

    @metric
    def opex(self, n: pypsa.Network, **kwargs):
        """PyPSA.statistics - Total system cost for a network."""
        return n.statistics.opex(**kwargs)

    @metric
    def energy_balance(self, n: pypsa.Network, **kwargs):
        """PyPSA.statistics - Energy balance for a network."""
        return n.statistics.energy_balance(**kwargs)

    @metric
    def capacity_factor(self, n: pypsa.Network, **kwargs):
        """PyPSA.statistics - Capacity factor for a network."""
        return n.statistics.capacity_factor(**kwargs)

    @metric
    def market_value(self, n: pypsa.Network, **kwargs):
        """PyPSA.statistics - Market value for a network."""
        return n.statistics.market_value(**kwargs)

    @metric
    def supply(self, n: pypsa.Network, **kwargs):
        """PyPSA.statistics - Supply for a network."""
        return n.statistics.supply(**kwargs)

    @metric
    def withdrawal(self, n: pypsa.Network, **kwargs):
        """PyPSA.statistics - Withdrawal for a network."""
        return n.statistics.withdrawal(**kwargs)

    @metric
    def transmission(self, n: pypsa.Network, **kwargs):
        """PyPSA.statistics - Transmission statistics for a network."""
        return n.statistics.transmission(**kwargs)

    @metric
    def consumer_surplus(self, n: pypsa.Network, **kwargs):  # TODO: groupby carrier for an easier way of filtering DC and DC_OH
        """Compute consumer surplus for a network."""
        energy_injection = n.statistics.energy_balance(bus_carrier=["AC", "AC_OH"], groupby=["name", "bus"], groupby_time=False)
        if "filter_GB" in kwargs and kwargs["filter_GB"]:
            gb_ac_buses = n_iem.components.buses.df.query("country=='GB' and carrier in ['AC', 'AC_OH']").index
            energy_injection = energy_injection.loc[:, :, gb_ac_buses]
        prices = n.statistics.prices(groupby_time=False)
        dc_links_to_exclude = n.links[n.links.carrier.isin(["DC", "DC_OH"])].index
        consumer_indices = energy_injection[energy_injection.sum(axis=1) < 0].index
        energy_injection = energy_injection.loc[consumer_indices].drop(dc_links_to_exclude, level=1)
        consumer_surplus = energy_injection.mul(prices, level=2)
        return consumer_surplus  # results negative because this is consumer cost (WTP is not priced)

    @metric
    def producer_surplus(self, n: pypsa.Network, **kwargs):
        """Compute consumer surplus for a network."""
        energy_injection = n.statistics.energy_balance(bus_carrier=["AC", "AC_OH"], groupby=["name", "bus"], groupby_time=False)
        if "filter_GB" in kwargs and kwargs["filter_GB"]:
            gb_ac_buses = n_iem.components.buses.df.query("country=='GB' and carrier in ['AC', 'AC_OH']").index
            energy_injection = energy_injection.loc[:, :, gb_ac_buses]
        producer_name_bus = energy_injection[energy_injection.sum(axis=1) > 0].index
        # producer surplus = (revenue - fuel_costs - CO2_costs) - opex
        carrier_cashflows = n.statistics.revenue(groupby=["name", "bus"], at_port=True, groupby_time=False).loc[:, producer_name_bus.get_level_values(1), :]
        opex = n.statistics.opex(groupby=["name", "bus"], groupby_time=False).loc[:, producer_name_bus.get_level_values(1), :]
        dc_links_to_exclude = n.links[n.links.carrier.isin(["DC", "DC_OH"])].index
        producer_surplus = carrier_cashflows.sub(opex, fill_value=0).drop(dc_links_to_exclude, level=1)
        return producer_surplus

    @metric
    def congestion_income(self, n: pypsa.Network, **kwargs):
        """Compute total congestion income for a network."""
        interconnectors = n.links[n.links.carrier.isin(["DC", "DC_OH"])]
        flows = n.links_t.p0[interconnectors.index].T
        prices = n.statistics.prices(groupby_time=False)
        revenues = flows.mul(prices.loc[interconnectors.bus1].values - prices.loc[interconnectors.bus0].values, axis=0)
        if "filter_GB" in kwargs:
            if kwargs["filter_GB"]==True:
                explicit_gb_ics = flows.index.str.contains("GB00")
            elif kwargs["filter_GB"]=="only_explicit":
                explicit_gb_ics = flows.index.str.contains("GB00") & flows.index.str.contains("|".join(EXPLICIT_BORDERS))
            return revenues[explicit_gb_ics].sum(axis=1)
        else:
            return revenues.sum(axis=1)

    @metric
    def co2_emissions(self, n: pypsa.Network, **kwargs):
        """Compute total CO2 emissions for a network."""
        all_co2_balances = n.statistics.energy_balance(bus_carrier=["co2"], #, "co2 stored", "co2 sequestered"], #stored and sequestered are not necessary.
                                                       groupby=["name", "bus_carrier"])

        if "filter_GB" in kwargs and kwargs["filter_GB"]:
            components_in_ac = n.statistics.energy_balance(bus_carrier=["AC", "AC_OH"], groupby=["name", "country"]).xs(
                "GB", level=2).index.get_level_values(1)
        else:
            components_in_ac = n.statistics.energy_balance(bus_carrier=["AC", "AC_OH"], groupby=["name"]).index.get_level_values(1)

        co2_emitting_components_in_ac = components_in_ac.intersection(all_co2_balances.index.get_level_values(1))

        # select GB AC components
        agg = all_co2_balances.loc[:, co2_emitting_components_in_ac].groupby("bus_carrier").sum()

        return agg

    @metric
    def share_of_renewables(self, n: pypsa.Network, **kwargs):
        """Compute share of renewables in total generation for a network."""
        supply = n.statistics.supply(bus_carrier=["AC", "AC_OH"], groupby=["carrier", "country"])
        if "filter_GB" in kwargs and kwargs["filter_GB"]:
            supply = supply.xs("GB", level=2)
        supply = supply.reset_index()
        supply["is_renewable"] = supply["carrier"].map(MAP_NON_RENEWABLES)
        supply["is_renewable"] = supply["is_renewable"].fillna(True)
        share_renewables = supply.groupby("is_renewable").sum()[0][True] / supply.groupby("is_renewable").sum()[0].sum()
        return pd.Series(share_renewables)


def sort_into_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Sort a MultiIndex DataFrame into columns based on a specified level order."""
    return df.T.unstack(level=0).swaplevel(0, 1, axis=1).sort_index(axis=1)


if __name__ == "__main__":
    import pypsa
    import pandas as pd

    nc = pypsa.NetworkCollection(
        pd.Series(
            {
                "2030 - SQ": "20260116_1301/networks/base_s_all_lluk__2030.nc",
                "2030 - IEM": "20260116_1301/networks/base_s_all___2030_no_ce.nc",
                "2030 - TF": "20260116_1301/trader-forecast/base_s_all___2030.nc",
                "2040 - SQ": "20260116_1301/networks/base_s_all_lluk__2040.nc",
                "2040 - IEM": "20260116_1301/networks/base_s_all___2040_no_ce.nc",
                "2040 - TF": "20260116_1301/trader-forecast/base_s_all___2040.nc",
            }
        )
    )


    results = {}
    consumer_surplus = {}
    producer_surplus = {}
    congestion_income = {}
    consumer_surplus_gb = {}
    producer_surplus_gb = {}
    congestion_income_gb = {}
    congestion_income_gb_only_explicit_borders = {}
    congestion_income_gb_diff_with_capture_rate = {}
    welfare = {}
    welfare_gb = {}
    co2_emissions = {}
    co2_emissions_gb = {}
    share_of_renewables = {}
    share_of_renewables_gb = {}

    for year in [2030, 2040]:

        n_trader = nc[f"{year} - TF"]
        n_sq = nc[f"{year} - SQ"]
        n_iem = nc[f"{year} - IEM"]

        results[year] = ResultsComputer(n_trader, n_sq, n_iem)

        consumer_surplus[year] = sort_into_columns(results[year].consumer_surplus.compare()).sum().groupby(level=3).sum()/1e6
        producer_surplus[year] = sort_into_columns(results[year].producer_surplus.compare()).sum().groupby(level=3).sum()/1e6
        congestion_income[year] = results[year].congestion_income.compare().sum()/1e6

        consumer_surplus_gb[year] = sort_into_columns(results[year].consumer_surplus.compare(filter_GB=True)).sum().groupby(level=3).sum()/1e6
        producer_surplus_gb[year] = sort_into_columns(results[year].producer_surplus.compare(filter_GB=True)).sum().groupby(level=3).sum()/1e6
        congestion_income_gb[year] = results[year].congestion_income.compare(filter_GB=True).sum()/1e6
        congestion_income_gb_only_explicit_borders[year] = results[year].congestion_income.compare(filter_GB="only_explicit").sum()/1e6

        capture_rate = 0.85
        congestion_income_gb_diff_with_capture_rate[year] = congestion_income_gb_only_explicit_borders[year]["iem"] - congestion_income_gb_only_explicit_borders[year]["sq"] * capture_rate

        welfare[year] = consumer_surplus[year] + producer_surplus[year] + congestion_income[year]
        welfare_gb[year] = consumer_surplus_gb[year] + producer_surplus_gb[year] + congestion_income_gb[year] / 2

        co2_emissions[year] = results[year].co2_emissions.compare().sum()/1e6  # convert to Million tonnes
        co2_emissions_gb[year] = results[year].co2_emissions.compare(filter_GB=True).sum()/1e6

        share_of_renewables[year] = results[year].share_of_renewables.compare()
        share_of_renewables_gb[year] = results[year].share_of_renewables.compare(filter_GB=True)

    print()