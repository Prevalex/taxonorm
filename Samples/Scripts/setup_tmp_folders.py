#!

from taxonorm.pathfinder import temp_dir, variants_tmp_dir, google_tmp_dir, patterns_tmp_dir, setup_folder

temp_list = [temp_dir, variants_tmp_dir, google_tmp_dir, patterns_tmp_dir]
temp_names = ["temp", "tmp", "Temp", "Tmp"]

for temp_folder in temp_list:
    if temp_folder.name in temp_names:
        setup_folder(temp_folder)



