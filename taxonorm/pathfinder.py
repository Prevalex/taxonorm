#

"""This is a temporary module designed to simplify obtaining paths to library folders and files"""

from pathlib import Path

project_dir = Path(__file__).resolve().parent.parent

examples_dir              = project_dir / 'Examples'
tests_dir                 = project_dir / 'Tests'
temp_dir                  = project_dir / 'Temp'

samples_dir               = project_dir / 'Samples'
scripts_dir               = project_dir / 'Samples' / 'Scripts'

variants_dir              = project_dir / 'Samples' / 'Variants'
shorts_dir                = project_dir / 'Samples' / 'Variants' / 'Shorts'
chunks_dir                = project_dir / 'Samples' / 'Variants' / 'Chunks'
briefs_dir                = project_dir / 'Samples' / 'Variants' / 'Briefs'
variants_tmp_dir          = project_dir / 'Samples' / 'Variants' / 'tmp'

google_dir                = project_dir / 'Samples' / 'Google'
google_orig_dir           = project_dir / 'Samples' / 'Google' / 'Original'
google_aio_dir            = project_dir / 'Samples' / 'Google' / 'Original' / 'All-In-One'
google_gen_dir            = project_dir / 'Samples' / 'Google' / 'Generated'
google_tmp_dir            = project_dir / 'Samples' / 'Google' / 'tmp'

patterns_dir              = project_dir / 'Samples' / 'Patterns'
patterns_tmp_dir          = project_dir / 'Samples' / 'Patterns' / 'tmp'

BRIEF_3L_JSON             = project_dir / 'Samples' / 'Patterns' / 'BRIEF_3L.json'
BRIEF_3L_IP_H_K_T_XLSX    = project_dir / 'Samples' / 'Patterns' / 'BRIEF_3L_IP_H_K_T.xlsx'

BRIEF_EN_JSON             = project_dir / 'Samples' / 'Patterns' / 'BRIEF_EN.json'
BRIEF_EN_LP_NH_I_NS_XLSX  = project_dir / 'Samples' / 'Patterns' / 'BRIEF_FT_EN_LP_NH_I_NS.xlsx'
BRIEF_EN_LP_NH_NI_NS_XLSX = project_dir / 'Samples' / 'Patterns' / 'BRIEF_FT_EN_LP_NH_NI_NS.xlsx'

FULL_3L_LP_I_NS_XLSX      = project_dir / 'Samples' / 'Patterns' / 'FULL_3L_LP_I_NS.xlsx'

SHORT_2L_NU_AP_XLSX       = project_dir / 'Samples' / 'Patterns' / 'SHORT_2L_NU_AP.xlsx'
SHORT_2L_NU_IP_H_K_T_XLSX = project_dir / 'Samples' / 'Patterns' / 'SHORT_2L_NU_IP_H_K_T.xlsx'
SHORT_2L_U_IP_H_K_T_XLSX  = project_dir / 'Samples' / 'Patterns' / 'SHORT_2L_U_IP_H_K_T.xlsx'


def setup_folder(folder: Path | str) -> None:

    if isinstance(folder, str):
        folder = Path(folder)

    if not folder.exists():
        folder.mkdir()
    else:
        for item in folder.iterdir():
            if item.is_file():
                item.unlink()