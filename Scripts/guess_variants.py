#!python
from typing import Any
from pathlib import Path
from collections.abc import Hashable
from alib.tables import read_llist_from_file

from colorama import Fore, just_fix_windows_console
from taxonorm.utils import get_style_from_hints
from taxonorm.sniffer import guess_style
from taxonorm.pathfinder import briefs_dir

just_fix_windows_console()  # colorama activation
red = Fore.LIGHTRED_EX
green = Fore.LIGHTGREEN_EX
cyan = Fore.LIGHTCYAN_EX
yellow = Fore.LIGHTYELLOW_EX
reset = Fore.RESET

RAISE_EXCEPTIONS = False

cvt = {'*': lambda x: (str(int(x)) if isinstance(x, (int, float)) else x)}  # str->str, 1 -> '1'-> '1', 1.0 -> '1'

def high_diff(s1: str, s2: str) -> str:
    """
    Сравнивает две строки из четырёх тегов.

    Совпадающие теги из s2 окрашиваются зелёным,
    отличающиеся — красным.
    Разделители '_' окрашиваются зелёным.
    """
    tags1 = s1.split("_")
    tags2 = s2.split("_")

    if len(tags1) != 4 or len(tags2) != 4:
        raise ValueError("Каждая строка должна содержать ровно 4 тега")

    result = ""

    colored1 = []
    colored2 = []

    for tag1, tag2 in zip(tags1, tags2):

        high_tag1 = (Fore.CYAN if tag1 == tag2 else Fore.LIGHTCYAN_EX) + tag1
        high_tag2 = (Fore.LIGHTGREEN_EX if tag1 == tag2 else Fore.LIGHTRED_EX) + tag2

        colored1.append(high_tag1)
        colored2.append(high_tag2)

        high_tags1 = f"{Fore.CYAN}_".join(colored1)
        high_tags2 = f"{Fore.CYAN}_".join(colored2)

        result = high_tags1 + Fore.LIGHTRED_EX +' != ' + high_tags2

    #return result + Style.RESET_ALL
    return result + Fore.RESET

def guess_variant(filename: Path | str, *,
                  leaf_keys: list[Hashable]|None = None,
                  cvt_dict: dict | None = None,
                  eol: Any = None,
                  ) -> None:

    if not isinstance(filename, Path):
        filename = Path(filename)

    hint_str = filename.stem

    source_file = briefs_dir / filename

    tx_data = read_llist_from_file(source_file, cvt_dict=cvt_dict, eol=eol, skip_empty=True)

    g_style = guess_style(tx_data, leaf_keys=leaf_keys)
    h_style = get_style_from_hints(hint_str)

    hint_flags = "_".join(h_style.hints)
    guess_flags = "_".join(g_style.hints)


    if hint_flags == guess_flags:
        print(f"{filename.name}: {Fore.LIGHTGREEN_EX}{hint_flags} == {guess_flags}{Fore.RESET}")
    else:
        #print(f"{filename.name}: {Fore.CYAN}{hint_flags}{Fore.LIGHTRED_EX} != {high_diff(hint_flags, guess_flags)}")
        print(f"{filename.name}: {high_diff(hint_flags, guess_flags)}")

print(f'{yellow}\nTrying to guess style of sample variants from: {briefs_dir}\n{reset}')

for csv in briefs_dir.glob('*.csv'):
    group = csv.stem
    print(f'{Fore.LIGHTCYAN_EX}Guess: {group}{Fore.RESET}')

    for file in briefs_dir.glob(f'{group}.*'):
        ext = file.suffix.strip('.').lower()
        guess_variant(file, cvt_dict=cvt, leaf_keys=['en_US', 'uk_UA'])
    print()

print(f'{yellow}\nSample variants folder was: {briefs_dir}{reset}')
