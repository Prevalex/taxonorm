#!python
from typing import Any
from pathlib import Path
from collections.abc import Callable
from alib.viewers import plist
from alib.files import read_pydata_from_json_file

from colorama import Fore, just_fix_windows_console

from taxonorm.utils import get_style_from_hints
from taxonorm import Taxonomy, import_taxonomy
from taxonorm.common import IpStyle, tStyler
from taxonorm.pathfinder import BRIEF_3L_JSON, BRIEF_EN_JSON, briefs_dir

RAISE_EXCEPTIONS = False

just_fix_windows_console()  # colorama activation
red = Fore.LIGHTRED_EX
green = Fore.LIGHTGREEN_EX
cyan = Fore.LIGHTCYAN_EX
yellow = Fore.YELLOW
sunny = Fore.LIGHTYELLOW_EX
magenta = Fore.MAGENTA
reset = Fore.RESET

LEAF_KEYS = ['en_US','uk_UA','ru_RU']

pattern_for_ip = BRIEF_3L_JSON
pattern_for_lp = BRIEF_EN_JSON

def cvt(v):
    if v is None:
        return None
    else:
        try:
            return int(v)
        except ValueError:
            return str(v)

cvt_dic = {'*':cvt}

def load_variant(filename: str | Path, *,
                 leaf_keys: list | tuple | None = None,
                 sheet: Any = None,
                 style: tStyler | None = None,
                 cvt_dict: dict | None = None,
                 sort_cvt: Callable | str | None = 'auto',
                 none: bool = True,
                 ):

    if not isinstance(filename, Path):
        filename = Path(filename)

    hint_str = filename.stem

    if style is None:
        styler = get_style_from_hints(hint_str)
    else:
        styler = style

    source = briefs_dir / Path(filename)

    result = import_taxonomy(source,
                                 leaf_keys=leaf_keys,
                                 styler=styler,
                                 sheet=sheet,
                                 cvt_dict=cvt_dict,
                                 sort_cvt=sort_cvt,
                                 none=none,
                                 eol='#')
    return result, styler

def are_same_leaves(tax_a: Taxonomy, tax_b: Taxonomy):
    """try to compare without ids for that case if source is lp-ni taxonomy"""

    serial_x = sorted(
        (tax_a.leaf_path(branch.path, 'en_US') for branch in tax_a.iter_branches()),
        key=repr,
    )
    serial_y = sorted(
        (tax_b.leaf_path(branch.path, 'en_US') for branch in tax_b.iter_branches()),
        key=repr,
    )

    if serial_x == serial_y:
        return True
    else:
        plist(serial_x, serial_y, labels=['X:', 'Y:'], limit=10)
        return False



##################################[ test_parse ] #####################################


data_for_ip = Taxonomy.from_branches(read_pydata_from_json_file(pattern_for_ip))
data_for_lp = Taxonomy.from_branches(read_pydata_from_json_file(pattern_for_lp))

print(f'{sunny}\nParsing sample variants from: {briefs_dir}{reset}')

for csv_file in briefs_dir.glob('*.csv'):
    group = csv_file.stem
    print(f'\n{cyan}Parse: {group}{reset}')

    for file in briefs_dir.glob(f'{group}.csv'):
        ext = file.suffix.strip('.').lower()

        try:
            parsed_data, style = load_variant(file, cvt_dict=cvt_dic, leaf_keys=LEAF_KEYS)

            if isinstance(style, IpStyle):
                tx_data = data_for_ip
            else:
                tx_data = data_for_lp

            if parsed_data != tx_data:
                if are_same_leaves(parsed_data, tx_data):
                    print(f'  {yellow}{file.name}: {green}Match, {magenta}but the ID system is different{reset}')
                else:
                    print(f'  {yellow}{file.name}: {red}Missmatch{reset}')
                    plist(tx_data, parsed_data, labels=['orignl', 'parsed'], limit=10)
            else:
                print(f'  {yellow}{file.name}: {green}Match with same ID system{reset}')
        except NotImplementedError as e:
            print(f'  {yellow}{file.name}: {red}{e}{reset}')

print(f'{sunny}\nSample variants folder was: {briefs_dir}{reset}')
