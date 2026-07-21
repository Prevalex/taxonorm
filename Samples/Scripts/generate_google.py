from taxonorm.writer import export_taxonomy
from taxonorm.reader import import_taxonomy
from taxonorm.common import IpStyle, LpStyle
from taxonorm.model import Taxonomy
from taxonorm.utils import  get_style_from_hints as hinter
from taxonorm.pathfinder import FULL_3L_LP_I_NS_XLSX, google_tmp_dir, setup_tmp_folder

from pathlib import Path

LEAF_KEYS = ['uk_UA', 'ru_RU', 'en_US']
ALL_LANG_FILE = Path('EN_UK_RU.xlsx')

def cvt(v):
    if v is None:
        return None
    else:
        try:
            return int(v)
        except ValueError:
            return str(v)

cvt_dict = {'*':cvt}

source = FULL_3L_LP_I_NS_XLSX

out_path = google_tmp_dir
setup_tmp_folder(out_path)

ip_h_k_t = IpStyle(header=True, keys=True, tabbed=True)
ip_name = '_'.join(ip_h_k_t.hints)

ip_nh_nk_nt = IpStyle(header=False, keys=False, tabbed=False)
ip_en_name  = '_'.join(ip_nh_nk_nt.hints)

lp_normal = LpStyle(header=False, ids=True, sparse=False)
lp_name = '_'.join(lp_normal.hints)

lp_sparse = LpStyle(header=False, ids=True, sparse=True)
lps_name = '_'.join(lp_sparse.hints)

ip_all_xlsx = out_path / Path(f'{ip_name}_uk_ru_en.xlsx')
ip_all_csv  = out_path / Path(f'{ip_name}_uk_ru_en.csv')

ip_en_xlsx = out_path / Path(f'{ip_en_name}_en.xlsx')
ip_en_csv  = out_path / Path(f'{ip_en_name}_en.csv')

lp_csv_uk = out_path / Path(f'{lp_name}_uk.csv')
lp_csv_ru = out_path / Path(f'{lp_name}_ru.csv')
lp_csv_en = out_path / Path(f'{lp_name}_en.csv')

lps_csv_uk = out_path / Path(f'{lps_name}_uk.csv')
lps_csv_ru = out_path / Path(f'{lps_name}_ru.csv')
lps_csv_en = out_path / Path(f'{lps_name}_en.csv')

print('Importing EN')
tx_en = import_taxonomy(source, sheet='EN', cvt_dict=cvt_dict, leaf_keys=('en_US',))
print('Done\n')

print('Importing RU')
tx_ru = import_taxonomy(source, sheet='RU', cvt_dict=cvt_dict, leaf_keys=('ru_RU',))
print('Done\n')

print('Importing UK')
tx_uk = import_taxonomy(source, sheet='UK', cvt_dict=cvt_dict, leaf_keys=('uk_UA',))
print('Done\n')

tx_all_lang = Taxonomy()

for uk, ru, en in zip(
    tx_uk.iter_branches(), tx_ru.iter_branches(), tx_en.iter_branches()
):
    # создаем (собираем) словарь листьев из трех IP таксономий, содержащихся в листах xlsx
    if uk.path == ru.path == en.path:

        leaves = {}
        leaves |= en.leaves
        leaves |= ru.leaves
        leaves |= uk.leaves

        tx_all_lang.add_branch(en.path, leaves)
    else:
        raise ValueError('WTF?!')

print(f'Saving to {ip_en_xlsx}')
export_taxonomy(tx_en, ip_en_xlsx, styler=ip_nh_nk_nt, key_order=LEAF_KEYS)

print(f'Saving to {ip_en_csv}')
export_taxonomy(tx_en, ip_en_csv, styler=ip_nh_nk_nt, key_order=LEAF_KEYS)

print(f'Saving to {ip_all_xlsx}')
export_taxonomy(tx_all_lang, ip_all_xlsx, styler=ip_h_k_t, key_order=LEAF_KEYS)

print(f'Saving to {ip_all_csv}')
export_taxonomy(tx_all_lang, ip_all_csv, styler=ip_h_k_t, key_order=LEAF_KEYS)

print(f'Saving to {lp_csv_en}')
export_taxonomy(tx_all_lang, lp_csv_en, styler=lp_normal, leaf_key='en_US')

print(f'Saving to {lp_csv_uk}')
export_taxonomy(tx_all_lang, lp_csv_uk, styler=lp_normal, leaf_key='uk_UA')

print(f'Saving to {lp_csv_ru}')
export_taxonomy(tx_all_lang, lp_csv_ru, styler=lp_normal, leaf_key='ru_RU')

print(f'Saving to {lps_csv_en}')
export_taxonomy(tx_all_lang, lps_csv_en, styler=lp_sparse, leaf_key='en_US')

print(f'Saving to {lps_csv_uk}')
export_taxonomy(tx_all_lang, lps_csv_uk, styler=lp_sparse, leaf_key='uk_UA')

print(f'Saving to {lps_csv_ru}')
export_taxonomy(tx_all_lang, lps_csv_ru, styler=lp_sparse, leaf_key='ru_RU')

## COMPARE TO CHECK ###

def tx_compare(file:Path, data_tx:Taxonomy, leaf_keys):
    print(f'\n>>>: Importing from {file}')
    style = hinter(file.stem)

    file_tx = import_taxonomy(file, styler=style, cvt_dict=cvt_dict, leaf_keys=leaf_keys)

    if file_tx != data_tx:
        print(f'Err: Taxonomy from {file} do not match source taxonomy'
               '\nShow to compare:')

        counter = 0
        err_count = 0

        for src, dst in zip(data_tx.iter_branches(), file_tx.iter_branches()):
            if src != dst:
                err_count += 1
                print(f'src#{counter}: {src}')
                print(f'dst#{counter}: {dst}')
                print()
                if err_count > 10:
                    break
            counter += 1
    else:
        print(f'Ok!: Taxonomy from {file} match source taxonomy')

tx_compare(ip_all_csv, tx_all_lang, leaf_keys=LEAF_KEYS)
tx_compare(ip_all_xlsx, tx_all_lang, leaf_keys=LEAF_KEYS)
tx_compare(ip_en_csv, tx_en, leaf_keys=['en_US'])
tx_compare(ip_en_xlsx, tx_en, leaf_keys=['en_US'])
