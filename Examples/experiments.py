#!python

from colorama import Fore, just_fix_windows_console

from taxonorm.pathfinder import briefs_dir, chunks_dir
from taxonorm import import_taxonomy, IpStyle
from taxonorm.utils import get_style_from_hints

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

VARIANT_FILE = 'IP_H_K_T.csv'
CHUNKS_FILE = 'mti_grp_swap.csv'

variant_file = briefs_dir / VARIANT_FILE
variant_style = get_style_from_hints(variant_file.stem)

chunks_file = chunks_dir / CHUNKS_FILE
chunks_style = IpStyle(header=False, keys=False, tabbed=False)
chunks_leaf_keys = ['en_US']

def cvt(v):
    if v is None:
        return None
    else:
        try:
            return int(v)
        except ValueError:
            return str(v)

cvt_dic = {'*':cvt}

def show(tx):
    print('\n------------------------')
    for branch in tx.iter_branches():
        print(branch.path, branch.leaves)

def view_as_leaves(taxonomy):
    for branch in taxonomy.iter_branches():
        leaves = taxonomy.leaf_path(branch.path,'en_US')
        print(leaves)


taxonomy = import_taxonomy(variant_file, leaf_keys=LEAF_KEYS, styler=variant_style, cvt_dict=cvt_dic)
show(taxonomy)
view_as_leaves(taxonomy)

exit()

taxonomy = import_taxonomy(chunks_file, leaf_keys=chunks_leaf_keys, styler=chunks_style, cvt_dict=cvt_dic,
                           restore_ip_chunks=True)
show(taxonomy)

print(f'{len(taxonomy)=}')

exists = (0, 10, 1707) in taxonomy  # проверка полного пути

node = taxonomy.get_node((0, 10, 1707))
print(node.leaves["en_US"])
print(node.children)

node = taxonomy.get_node((0, 10))
print(node.leaves["en_US"])
print(node.children)

