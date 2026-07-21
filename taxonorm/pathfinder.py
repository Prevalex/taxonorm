#
"""This is a temporary module designed to make it easier to get paths to library folders and files."""
from pathlib import Path

tmp_names = ['tmp', 'temp', 'Tmp', 'Temp']
project_dir = Path(__file__).resolve().parent.parent

examples_dir              = project_dir / 'Examples'  # readme examples and other examples
tests_dir                 = project_dir / 'Tests'     # pytest test folder
temp_dir                  = project_dir / 'Temp'      # general temp folde

samples_dir               = project_dir / 'Samples'   # taxonomy samples in supported style and format
scripts_dir               = project_dir / 'Samples' / 'Scripts'  # scripts to generate or validate samples

variants_dir              = project_dir / 'Samples' / 'Variants' # supported taxonomy variants
shorts_dir                = project_dir / 'Samples' / 'Variants' / 'Shorts' # very short samples (adapted for learning)
chunks_dir                = project_dir / 'Samples' / 'Variants' / 'Chunks' # chunks samples
briefs_dir                = project_dir / 'Samples' / 'Variants' / 'Briefs' # A simplified versions of real taxonomy
variants_tmp_dir          = project_dir / 'Samples' / 'Variants' / 'tmp'    # Folder for generated sample files

google_dir                = project_dir / 'Samples' / 'Google' # google taxonomy for product categories
google_orig_dir           = project_dir / 'Samples' / 'Google' / 'Original' # original google taxonomy
google_aio_dir            = project_dir / 'Samples' / 'Google' / 'Original' / 'All-In-One' # combined for three langs
google_gen_dir            = project_dir / 'Samples' / 'Google' / 'Generated' # converted to supported format and style
google_tmp_dir            = project_dir / 'Samples' / 'Google' / 'tmp' # Folder for generated files

patterns_dir              = project_dir / 'Samples' / 'Patterns'  # templates for generating options
patterns_tmp_dir          = project_dir / 'Samples' / 'Patterns' / 'tmp' # Folder for generated files


BRIEF_3L_IP_H_K_T_XLSX    = project_dir / 'Samples' / 'Patterns' / 'BRIEF_3L_IP_H_K_T.xlsx' # simplified 3 lang
BRIEF_3L_JSON             = project_dir / 'Samples' / 'Patterns' / 'BRIEF_3L.json' # simplified 3 lang taxonomy model
BRIEF_EN_JSON             = project_dir / 'Samples' / 'Patterns' / 'BRIEF_EN.json' # simplified en lang taxonomy model


BRIEF_EN_LP_NH_I_NS_XLSX  = project_dir / 'Samples' / 'Patterns' / 'BRIEF_FT_EN_LP_NH_I_NS.xlsx' # color formatted
BRIEF_EN_LP_NH_NI_NS_XLSX = project_dir / 'Samples' / 'Patterns' / 'BRIEF_FT_EN_LP_NH_NI_NS.xlsx' # color formatted

FULL_3L_LP_I_NS_XLSX      = project_dir / 'Samples' / 'Patterns' / 'FULL_3L_LP_I_NS.xlsx' # Full Google 3-Lang Taxonomy

SHORT_2L_NU_AP_XLSX       = project_dir / 'Samples' / 'Patterns' / 'SHORT_2L_NU_AP.xlsx'       # 2-lang All Paths Non Unique IDs
SHORT_2L_NU_IP_H_K_T_XLSX = project_dir / 'Samples' / 'Patterns' / 'SHORT_2L_NU_IP_H_K_T.xlsx' # short 2-lang Non Unique IDs
SHORT_2L_U_IP_H_K_T_XLSX  = project_dir / 'Samples' / 'Patterns' / 'SHORT_2L_U_IP_H_K_T.xlsx'  # short 2-lang Unique IDs

def setup_tmp_folder(folder: Path | str) -> None:
    """ creates/clears temporary folders as output folder for generated samples"""

    if isinstance(folder, str):
        folder = Path(folder)

    if folder.name in tmp_names:
        if not folder.exists():
            folder.mkdir()
        else:
            if folder.is_dir():
                for item in folder.iterdir():
                    if item.is_file():
                        item.unlink()
            else:
                print(f'Error: {folder} is a file, not a folder.')
    else:
        print(f'Error: folder name must be from the list: {','.join(tmp_names)}. Received: {folder.name}')
