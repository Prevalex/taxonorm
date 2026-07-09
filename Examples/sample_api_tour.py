#!python
"""A compact tour through the smaller pieces of the public API."""

from __future__ import annotations

from taxonorm import (
    IpStyle,
    LpStyle,
    Taxonomy,
    TxInputValidationError,
    guess_style,
    import_taxonomy,
    renumber_taxonomy_ids,
    serialize_taxonomy,
    validate_taxonomy,
)
from taxonorm.errors import TaxonormError

from sample_common import LEAF_KEYS, SAMPLE_IP_H_K_T, as_int_when_possible


manual = Taxonomy.from_branches(
    [
        [1, {"en_US": "Household appliances", "uk_UA": "Побутова техніка"}],
        [1, 11, {"en_US": "Climate technology", "uk_UA": "Кліматична техніка"}],
        [1, 11, 21, {"en_US": "Household fans", "uk_UA": "Вентилятори побутові"}],
    ]
)
print(manual.to_branches())

lp_rows = [
    [1, "Household appliances"],
    [11, "Household appliances", "Climate technology"],
    [21, "Household appliances", "Climate technology", "Household fans"],
]
style = guess_style(lp_rows, leaf_keys=["en_US"])
print(style)
parsed = import_taxonomy(
    lp_rows,
    styler=style,
    leaf_keys=["en_US"],
)
print(parsed.to_branches())

report = validate_taxonomy(parsed)
print(report.valid, report.warnings)

taxonomy = import_taxonomy(
    SAMPLE_IP_H_K_T,
    styler=IpStyle(header=True, keys=True, tabbed=True),
    leaf_keys=LEAF_KEYS,
    cvt_dict={"*": as_int_when_possible},
)
serialized = serialize_taxonomy(
    taxonomy,
    styler=LpStyle(header=True, ids=True, sparse=False),
    leaf_key="en_US",
    headers=["id", "category"],
)
print(serialized[:4])

round_tripped = Taxonomy.from_branches(taxonomy.to_branches())
print(round_tripped == taxonomy)

renumbered = renumber_taxonomy_ids(taxonomy, slack=0, round_to=1, start_from=100)
print(renumbered.to_branches()[:3])

try:
    import_taxonomy(
        [[[], "", "", "Broken", "Зламано"]],
        styler=IpStyle(header=False, keys=False, tabbed=True),
        leaf_keys=["en_US", "uk_UA"],
    )
except TxInputValidationError as error:
    print(error.report.errors[0].code)
except TaxonormError as error:
    print(error.to_dict())
