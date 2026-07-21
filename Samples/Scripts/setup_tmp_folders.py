#!

from taxonorm.pathfinder import variants_tmp_dir, google_tmp_dir, patterns_tmp_dir, setup_tmp_folder

temp_list = [variants_tmp_dir, google_tmp_dir, patterns_tmp_dir]
temp_names = ["temp", "tmp", "Temp", "Tmp"]

for temp_folder in temp_list:
    if temp_folder.name in temp_names:
        setup_tmp_folder(temp_folder)



