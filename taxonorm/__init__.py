"""Public package API for taxonorm."""

__author__ = 'Allex'
__email__ = 'prevalex@gmail.com'
__version__ = '0.1.1'

from .parser import parse_taxonomy
from .sniffer import guess_style
from .writer import export_taxonomy
from .reader import import_taxonomy
from .serializer import serialize_taxonomy
from .model import Taxonomy, TaxonomyBranch, TaxonomyNode
from .viewer import (
    render_text_tree,
    save_text_tree,
    to_rich_tree,
    view_live_html_tree,
    view_live_text_tree,
    view_text_tree,
)
from .common import IpStyle, LpStyle
from .chunks import restore_unique_ip_chunks, split_to_unique_ip_chunks
from .adapters import from_bigtree, to_bigtree, to_networkx
from .errors import TxInputValidationError
from .stylers.style_lp_ni import renumber_taxonomy_ids
from .input_validation import (
    ValidationIssue,
    ValidationReport,
    validate_input,
    validate_taxonomy,
)

__all__ = [
    "Taxonomy",
    "TaxonomyBranch",
    "TaxonomyNode",
    "IpStyle",
    "LpStyle",
    "ValidationIssue",
    "ValidationReport",
    "TxInputValidationError",
    "renumber_taxonomy_ids",
    "restore_unique_ip_chunks",
    "split_to_unique_ip_chunks",
    "from_bigtree",
    "to_bigtree",
    "to_networkx",
    "validate_input",
    "validate_taxonomy",
    "parse_taxonomy",
    "guess_style",
    "export_taxonomy",
    "import_taxonomy",
    "serialize_taxonomy",
    "render_text_tree",
    "to_rich_tree",
    "save_text_tree",
    "view_text_tree",
    "view_live_text_tree",
    "view_live_html_tree",
]
