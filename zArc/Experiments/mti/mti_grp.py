from alib.csv_io import read_llist_from_csv_file, save_llist_to_csv_file

llist = read_llist_from_csv_file('mti_grp.csv')
save_llist_to_csv_file(llist, 'mti_grp.csv') # for utf-8 BOM

    
nlist = []
for row in llist:
    nlist.append([row[1],row[0],row[2]])

save_llist_to_csv_file(nlist, 'mti_grp_swap.csv')


nlist = []
for row in llist:
    nlist.append([0,row[1],row[0],row[2]])

save_llist_to_csv_file(nlist, 'mti_grp_swap_w_root.csv')

nlist.insert(0, ['root','basecat','subcat','EN','@'])

save_llist_to_csv_file(nlist, 'mti_grp_swap_w_root_h.csv')




