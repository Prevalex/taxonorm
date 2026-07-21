#!python
from pathlib import Path
import json

from colorama import Fore, just_fix_windows_console
from taxonorm.utils import get_style_from_hints
from taxonorm import import_taxonomy, export_taxonomy
from taxonorm.pathfinder import setup_tmp_folder, patterns_tmp_dir, BRIEF_3L_IP_H_K_T_XLSX, variants_tmp_dir

just_fix_windows_console()  # colorama activation
red = Fore.LIGHTRED_EX
green = Fore.LIGHTGREEN_EX
cyan = Fore.LIGHTCYAN_EX
reset = Fore.RESET
just_fix_windows_console()  # colorama activation
yellow = Fore.LIGHTYELLOW_EX

RAISE_EXCEPTIONS = False

LEAF_KEYS = ['en_US','uk_UA','ru_RU']
TITLES = ['taxonorm', '0.1.0', 'Sample', 'variants']

EXTENSIONS = ['xls','xlsx','csv']
TAXONOMY = 'BRIEF_3L.json'

pattern = BRIEF_3L_IP_H_K_T_XLSX

out_path = variants_tmp_dir

setup_tmp_folder(out_path)

taxonomy_file  = patterns_tmp_dir / TAXONOMY

groups = []

def cvt(v):
    if v is None:
        return None
    else:
        try:
            return int(v)
        except ValueError:
            return str(v)

cvt_dict = {'*':cvt}


def save_pydata_to_json_file(data, filename):
    Path(filename).write_text(
        json.dumps(data, ensure_ascii=False, indent=4),
        encoding="utf-8",
    )

for header in 'H', 'NH':
    for keys in 'K', 'NK':
        for tabbed in 'T', 'NT':
            group = "_".join(('IP', header, keys, tabbed))
            groups.append(group)

for header in 'H', 'NH':
    for ids in 'I', 'NI':
        for sparse in 'S', 'NS':
            group = "_".join(('LP', header, ids, sparse))
            groups.append(group)

styler = get_style_from_hints(pattern.stem)

taxonomy = import_taxonomy(pattern, leaf_keys=LEAF_KEYS, styler=styler, cvt_dict=cvt_dict)
save_pydata_to_json_file(taxonomy.to_branches(), taxonomy_file)

grp_count = 0
var_count = 0

print(f'{yellow}\nGenerating sample variants in {out_path}{reset}')
print(f'{yellow}Template to be used:  {pattern}{reset}')

for group in groups:
    grp_count += 1
    for ext in EXTENSIONS:
        var_count += 1
        file = out_path / Path(f'{group}.{ext}')
        styler = get_style_from_hints(group)

        print(f'grp {grp_count}; var {var_count}: {group}.{ext} with styler={styler}')

        export_taxonomy(taxonomy, file, styler=styler, leaf_key=LEAF_KEYS[0], headers=TITLES)

assert grp_count*3 == var_count, "Число вариантов не равно числу групп * 3, где 3 = число форматов файлов"

print(f'{yellow}\nGenerated sample variants saved to {out_path}{reset}')
print(f'{yellow}Used template: {pattern}{reset}')

