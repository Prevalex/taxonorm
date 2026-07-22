#!python
from pathlib import Path
import json

from colorama import Fore, just_fix_windows_console
from taxonorm.utils import get_style_from_hints
from taxonorm import export_taxonomy, import_taxonomy
from taxonorm.pathfinder import (setup_tmp_folder, variants_tmp_dir, SHORT_2L_NU_IP_H_K_T_XLSX, SHORT_2L_U_IP_H_K_T_XLSX,
                                 patterns_tmp_dir)

just_fix_windows_console()  # colorama activation
red = Fore.LIGHTRED_EX
green = Fore.LIGHTGREEN_EX
cyan = Fore.LIGHTCYAN_EX
reset = Fore.RESET
just_fix_windows_console()  # colorama activation
yellow = Fore.LIGHTYELLOW_EX

RAISE_EXCEPTIONS = False

LEAF_KEYS = ['en_US','uk_UA']
TITLES = ['taxonorm', '0.1.0', 'Sample', 'variants']

nu_pattern = SHORT_2L_NU_IP_H_K_T_XLSX
u_pattern = SHORT_2L_U_IP_H_K_T_XLSX

EXTENSIONS = ['xls','xlsx','csv']
U_TAXONOMY =  'SHORT_2L_U.json'
NU_TAXONOMY = 'SHORT_2L_NU.json'

out_path = variants_tmp_dir
setup_tmp_folder(out_path)

u_taxonomy_file  = patterns_tmp_dir / U_TAXONOMY
nu_taxonomy_file  = patterns_tmp_dir / NU_TAXONOMY

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

styler = get_style_from_hints(nu_pattern.stem)

nu_taxonomy = import_taxonomy(nu_pattern, leaf_keys=LEAF_KEYS, styler=styler, cvt_dict=cvt_dict)
save_pydata_to_json_file(nu_taxonomy.to_branches(), nu_taxonomy_file)

##u_taxonomy = renumber_taxonomy_ids(nu_taxonomy,slack=0.10,round_to=10,start_from=1,)
##export_taxonomy(u_taxonomy, u_pattern, styler=styler)

#-----

u_taxonomy = import_taxonomy(u_pattern, leaf_keys=LEAF_KEYS, styler=styler, cvt_dict=cvt_dict)
save_pydata_to_json_file(u_taxonomy.to_branches(), u_taxonomy_file)

for prefix, taxonomy, pattern in (('U', u_taxonomy, u_pattern), ('NU', nu_taxonomy, nu_pattern)):
    print(f'{yellow}{prefix}:{pattern}{reset}')
    grp_count = 0
    var_count = 0
    print(f'{yellow}\nGenerating short variants in {out_path}{reset}')
    print(f'{yellow}Template to be used:  {pattern}{reset}')
    for group in groups:
        grp_count += 1
        for ext in EXTENSIONS:
            var_count += 1
            file = out_path / Path(f'{prefix}_{group}.{ext}')
            styler = get_style_from_hints(group)

            print(f'grp {grp_count}; var {var_count}: {group}.{ext} with styler={styler}')

            export_taxonomy(taxonomy, file, styler=styler, leaf_key=LEAF_KEYS[0], headers=TITLES)

    assert grp_count*3 == var_count, "Число вариантов не равно числу групп * 3, где 3 = число форматов файлов"

    print(f'{yellow}\nGenerated short variants was saved to {out_path}{reset}')
    print(f'{yellow}Used template: {pattern}{reset}')

