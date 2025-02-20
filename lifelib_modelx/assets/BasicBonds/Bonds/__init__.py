"""The model_point Space in the :mod:`~assets.BasicBonds` model.



.. rubric:: Parameters and References

(In all the sample code below,
the global variable ``Bonds`` refers to the
:mod:`~assets.BasicBonds.Bonds` space.)

Attributes:

    ql: The `QuantLib <https://www.quantlib.org/>`_ module.

    date_init: Valuation date as a string in the form of 'YYYY-MM-DD'.


    date_end: Projection end date as a string in the form of 'YYYY-MM-DD'.

    zero_curve: Zero curve at the valuation date as a pandas Series
        indexed with strings indicating various durations.
        This data is used by :func:`riskfree_curve` to create
        QuantLib's ZeroCurve object::

            >>> Bonds.zero_curve

            Duration
            1M     0.0004
            2M     0.0015
            3M     0.0026
            6M     0.0057
            1Y     0.0091
            2Y     0.0136
            3Y     0.0161
            5Y     0.0182
            7Y     0.0192
            10Y    0.0194
            20Y    0.0231
            30Y    0.0225
            Name: Rate, dtype: float64

        The data is saved as an Excel file named "zero_curve.xlsx" in the
        model.

    bond_data: Bond data as a pandas DataFrame.
        By default, a sample table generated by the
        *generate_bond_data.ipynb* notebook included in the library::

            >>> Bonds.bond_data

                     settlement_days  face_value issue_date  ...  tenor coupon_rate z_spread
            bond_id                                          ...
            1                      0      235000 2017-12-12  ...     1Y        0.07   0.0304
            2                      0      324000 2021-11-29  ...     1Y        0.08   0.0304
            3                      0      799000 2017-02-03  ...     6M        0.03   0.0155
            4                      0      679000 2017-11-19  ...     1Y        0.08   0.0229
            5                      0      397000 2018-07-01  ...     6M        0.06   0.0142
                             ...         ...        ...  ...    ...         ...      ...
            996                    0      560000 2019-02-16  ...     1Y        0.06   0.0261
            997                    0      161000 2020-03-12  ...     6M        0.05   0.0199
            998                    0      375000 2019-05-05  ...     1Y        0.03   0.0138
            999                    0      498000 2019-02-21  ...     1Y        0.03   0.0230
            1000                   0      438000 2019-03-14  ...     1Y        0.06   0.0256

            [1000 rows x 8 columns]

        The column names and their data types are as follows::

            >>> Bonds.bond_data.dtypes

            settlement_days             int64
            face_value                  int64
            issue_date         datetime64[ns]
            bond_term                   int64
            maturity_date      datetime64[ns]
            tenor                      object
            coupon_rate               float64
            z_spread                  float64
            dtype: object

        The data is saved as an Excel file named "bond_data.xlsx" in the
        model.


"""

from modelx.serialize.jsonvalues import *

_formula = None

_bases = []

_allow_none = None

_spaces = []

# ---------------------------------------------------------------------------
# Cells

def cashflows(bond_id):
    """Returns the cashflows of the selected bond.

    Returns the cashflows of the selected bond as a list.
    Each element of the list is the total
    cashflows falling in each projection period defined by :func:`date_`.
    """

    result = [0] * step_size()
    leg = fixed_rate_bond(bond_id).cashflows()
    i = 0   # cashflow index

    for t in range(step_size()):

        while i < len(leg):

            if i > 0:
                # Check if cashflow dates are in order.
                assert leg[i-1].date() <= leg[i].date()

            if date_(t) <= leg[i].date() < date_(t+1):
                result[t] += leg[i].amount()

            elif date_(t+1) <= leg[i].date():
                break

            i += 1


    return result


def cashflows_total():
    """Returns the aggregated cashflows of the entire bond portfolio.

    Takes the sum of :func:`cashflows` across ``bond_id`` and
    returns as a list the aggregated cashflows of all the bonds
    in :attr:`bond_data`.
    """

    result = [0] * step_size()
    for t in range(step_size()):
        for i in bond_data.index:
            result[t] += cashflows(i)[t]

    return result


def date_(i):
    """Date at each projection step

    Defines projection time steps by returning QuantLib's `Date`_ object
    that corresponds to the value of the integer index ``i``.
    By default, ``date_(i)`` starts from the valuation date specified
    by :attr:`date_init`, and increments annually.

    .. _Date:
       https://www.quantlib.org/reference/class_quant_lib_1_1_date.html

    """
    if i == 0:
        return ql.Date(date_init, "%Y-%m-%d")

    else:
        return date_(i-1) + ql.Period('1Y')


def fixed_rate_bond(bond_id):
    """Returns QuantLib’s `FixedRateBond`_ object

    Create QuantLib’s `FixedRateBond`_ object
    representing a bond specified by the given bond ID.
    The bond object is created from the attributes in :attr:`bond_data`
    and :func:`schedule`.

    A pricing engine for the bond object is created as a `DiscountingBondEngine`_ object
    from :func:`riskfree_curve` and the ``z_spread`` attribute in :attr:`bond_data`,
    and associated with the bond object through a `ZeroSpreadedTermStructure`_ object.

    .. _FixedRateBond:
       https://www.quantlib.org/reference/class_quant_lib_1_1_fixed_rate_bond.html

    .. _DiscountingBondEngine:
       https://quantlib-python-docs.readthedocs.io/en/latest/pricing_engines/bonds.html

    .. _ZeroSpreadedTermStructure:
       https://www.quantlib.org/reference/class_quant_lib_1_1_zero_spreaded_term_structure.html

    """

    settlement_days = bond_data.loc[bond_id]['settlement_days']
    face_value = bond_data.loc[bond_id]['face_value']
    coupons = [bond_data.loc[bond_id]['coupon_rate']]

    bond = ql.FixedRateBond(
        int(settlement_days), 
        float(face_value), 
        schedule(bond_id),
        coupons, 
        ql.Actual360(), # DayCount
        ql.Unadjusted)

    spread = bond_data.loc[bond_id]['z_spread']
    spread = ql.QuoteHandle(ql.SimpleQuote(spread))
    disc_curve = ql.ZeroSpreadedTermStructure(
        ql.YieldTermStructureHandle(riskfree_curve()), spread,
        ql.Compounded, ql.Annual)

    # Set discount curve
    bondEngine = ql.DiscountingBondEngine(
        ql.YieldTermStructureHandle(disc_curve))
    bond.setPricingEngine(bondEngine)

    return bond


def redemptions(bond_id):
    """Returns cashflows of redemptions

    For the specified bond, returns a list of redemptions cashflows.
    Since the redemption cashflow occurs only once,
    all but one element are zero.
    """

    result = [0] * step_size()
    leg = fixed_rate_bond(bond_id).redemptions()
    i = 0   # cashflow index

    for t in range(step_size()):

        while i < len(leg):

            if date_(t) <= leg[i].date() < date_(t+1):
                result[t] += leg[i].amount()

            elif date_(t+1) <= leg[i].date():
                break

            i += 1

    return result


def redemptions_total():
    """Returns all redemption cashflows

    Returns a list of redemptions of all the bonds in :attr:`bond_data`.
    """

    result = [0] * step_size()
    for t in range(step_size()):
        for i in bond_data.index:
            result[t] += redemptions(i)[t]

    return result


def riskfree_curve():
    """Returns `ZeroCurve`_ object

    Creates QuantLib's `ZeroCurve`_ object from :attr:`zero_curve` and returns it.
    The `ZeroCurve`_ object is used by :func:`fixed_rate_bond` to
    construct a discount curve for calculating the market value of the specified bond.

    .. _ZeroCurve:
       https://www.quantlib.org/reference/group__yieldtermstructures.html

    """
    ql.Settings.instance().evaluationDate = date_(0)

    spot_dates = [date_(0)] + list(date_(0) + ql.Period(dur) for dur in zero_curve.index)
    spot_rates = [0] + list(zero_curve)

    return ql.ZeroCurve(
        spot_dates,
        spot_rates, 
        ql.Actual360(),                                 # dayCount
        ql.UnitedStates(ql.UnitedStates.Settlement),    # calendar
        ql.Linear(),                                    # Interpolator
        ql.Compounded,                                  # compounding
        ql.Annual                                       # frequency
        )


def schedule(bond_id):
    """Returns a `Schedule`_ object

    Create QuantLib's `Schedule`_ object for the specified bond and returns it.
    The returned `Schedule`_ object is used to by :func:`fixed_rate_bond`
    to construct `FixedRateBond`_ object.

    .. _Schedule:
       https://www.quantlib.org/reference/class_quant_lib_1_1_schedule.html

    .. _FixedRateBond:
       https://www.quantlib.org/reference/class_quant_lib_1_1_fixed_rate_bond.html


    """
    d = bond_data.loc[bond_id]['issue_date']
    issue_date = ql.Date(d.day, d.month, d.year)

    d = bond_data.loc[bond_id]['maturity_date']
    maturity_date = ql.Date(d.day, d.month, d.year)

    tenor  = ql.Period(
        ql.Semiannual if bond_data.loc[bond_id]['tenor'] == '6Y' else ql.Annual)


    return ql.Schedule(
        issue_date, 
        maturity_date, 
        tenor, 
        ql.UnitedStates(ql.UnitedStates.Settlement),    # calendar
        ql.Unadjusted,                                  # convention
        ql.Unadjusted ,                 # terminationDateConvention
        ql.DateGeneration.Backward,     # rule
        False   # endOfMonth
        )


def step_size():
    """Returns the number of time steps

    Calculates the number of time steps from :attr:`date_end`
    and :func:`date_` ren returns it.
    """
    d_end = ql.Date(date_end, "%Y-%m-%d")

    t = 0
    while True:
        if date_(t) < d_end:
            t += 1
        else:
            return t


def z_spread_recalc(bond_id):
    """Calculate Z-spread

    For the bond specified by ``bond_id``,
    Calculate the Z-spread of the bond specified by ``bond_id`` from
    the bond's market value and :func:`riskfree_curve`.
    This is for testing that the calculated Z-spread matches the input in :attr:`bond_data`.
    """
    return ql.BondFunctions.zSpread(
        fixed_rate_bond(bond_id), 
        fixed_rate_bond(bond_id).cleanPrice(), 
        riskfree_curve(),
        ql.Thirty360(), ql.Compounded, ql.Annual)


def market_values():
    """Returns the market values of the entire bonds

    Calculates and Returns a list of the market values of :func:`fixed_rate_bond`
    for all bonds input in :attr:`bond_data`.
    """

    bond = fixed_rate_bond

    return list(
        bond(i).notional() * bond(i).cleanPrice() / 100 
        for i in bond_data.index)


# ---------------------------------------------------------------------------
# References

date_end = "2053-01-01"

date_init = "2022-01-01"

bond_data = ("DataSpec", 2323236992288, 2323228088304)

ql = ("Module", "QuantLib")

zero_curve = ("DataSpec", 2323237349888, 2323227835552)