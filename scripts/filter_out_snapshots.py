import pypsa

import_dir_sq = "/Users/tpa/MyProjects/NGV-IEM/resources/base_s_all_lluk__2030-rerun.nc"
import_dir_iem = "/Users/tpa/MyProjects/NGV-IEM/resources/base_s_all___2030-rerun.nc"


n_sq = pypsa.Network(import_dir_sq)
n_iem = pypsa.Network(import_dir_iem)

def get_snapshots(n, carrier, threshold):

    # Determine snapshots to be dropped based on IEM scenario
    buses_name = n.buses[n.buses.carrier==carrier].index
    prices_b = n.buses_t.marginal_price[buses_name].apply(lambda col: col.mask(col>threshold))
    to_drop = n.snapshots[prices_b.isna().sum(axis=1)!=0]

    return  to_drop

def get_new_network_weighted(n, to_drop):
    # Drop the snapshots in the input network
    n.set_snapshots(n.snapshots.drop(to_drop))
    return n

to_drop = get_snapshots(n_iem, carrier = "low voltage", threshold = 4000)

n_sq_new  = get_new_network_weighted(n_sq, to_drop)
n_iem_new = get_new_network_weighted(n_iem, to_drop)

output_path_sq = '/Users/tpa/MyProjects/NGV-IEM/resources/base_s_all_lluk__2030-rerun-modified-low.nc'
n_sq_new.export_to_netcdf(output_path_sq)

output_path_iem = '/Users/tpa/MyProjects/NGV-IEM/resources/base_s_all___2030-rerun-modified-low.nc'
n_iem_new.export_to_netcdf(output_path_iem)



