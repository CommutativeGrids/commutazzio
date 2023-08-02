from .simplex_tree import SimplexTree
import numpy as np
from .clfiltration import CLFiltration
from random import randint #inclusive of the upper bound
from bisect import bisect_left
from functools import lru_cache

EPSILON = 1e-10 # for numerical comparison

def random_vertical_removal_points_only(num_pts,ladder_length,max_removal_per_time=None):
    # generate a list of length ladder_length
    # each item is a list of tuples representing points to be removed, indices of points is in range(0,num_pts)
    # an later item shall contain all the simplices of the previous item
    # for example, if ladder_length=3, and num_pts = 10, an output could be
    # [[(0,),(2,)],[(0,),(2,),(5,)],[(0,),(2,),(3,),(5,)]]
    # reverse the generated list and output
    result = []
    removed_points = []
    remained_points = list(range(num_pts))
    if max_removal_per_time is None:
        max_removal_per_time = max(1,int(num_pts/ladder_length))
    for _ in range(ladder_length):
        try:
            num_removed_points = min(\
                randint(1, \
                        min(max_removal_per_time,\
                            max(1,num_pts - len(removed_points))\
                                )\
                        ),\
                        len(remained_points)-1\
                                            )
        except ValueError:
            num_removed_points = 0
            removed_points = removed_points[-1]
        for _ in range(num_removed_points):
            #random sample from remained_points
            removed_point = remained_points.pop(randint(0,len(remained_points)-1))
            removed_points.append(removed_point)
        result.append([tuple([point]) for point in sorted(removed_points)])
    
    return result[::-1]

def pointCloud2Filtration(pts:np.array,vertical_removal_input:list,radii:list,max_simplex_dim:int,method:str='cech'):
    """
    Convert a point cloud to a commutative ladder filtration.
    pts: a numpy array of shape (num_pts, dim)
    vertical_removal_input: a list of list of simplices to be removed, notice that it is the name of the simplices, not the indices of the simplices
    radii: a list of radii
    max_simplex_dim: the maximum simplex dimension to be considered
    method: 'cech' or 'rips' or 'alpha'
    """    
    # create a simplex tree
    # truncation it using radius in radii, get a sc
    # create upper row and lower row
    # add simplices in sc to upper row, at the designated radius
    # add simplices in sc.delete(vertical_removal[i]) to lower row, at the designated radius
    # return necessary infos
    len_radii = len(radii)
    if isinstance(vertical_removal_input[0],(int, np.int64)): #[2,3,4,5,6,7]
        # constant removal
        vertical_removal=[{frozenset({vertex}) for vertex in vertical_removal_input}]*len_radii
        # print(vertical_removal)
    else:
        # vertical_removal_input is a list of list of simplices
        # canonically, vertical_removal is a list of list of simplices
        # each entry of vertical_removal is a list of simplices to be removed, for example [(1,),(2,3)]
        # turn to a list of set of sets
        vertical_removal = [{frozenset(simplex) for simplex in _} for _ in vertical_removal_input]
        assert len(vertical_removal)==len_radii
        # should be decreasing
        # example: [[(2,),(3,),(4,),(5,)],[(2,),(3,),(4,)],[(2,),(3,)]]
        assert all(vertical_removal[i].issuperset(vertical_removal[i+1]) for i in range(len(vertical_removal)-1))
    #check that radii is sorted
    assert all(radii[i]<=radii[i+1] for i in range(len_radii-1))
    print("Creating filtration...", flush=True)
    apexST=SimplexTree()
    apexST.from_point_cloud(pts,method=method,sc_dim_ceil=max_simplex_dim,radius_max=np.max(radii)+EPSILON)

    # define a function which assigns a filtration value to its corresponding x_coord
    @lru_cache(maxsize=None)
    def get_x_coord(fv:float):
        index = bisect_left(radii, fv)
        return index+1
    upper=SimplexTree()
    lower=SimplexTree()
    radius_max = np.max(radii)
    counter = 0
    for simplex,fv in apexST.get_filtration():
        if fv > radius_max:
            continue
        x_coord = get_x_coord(fv)
        upper.insert(simplex,x_coord)
        # this function will not make existing filtration value higher
        # This function inserts the given N-simplex 
        # and its subfaces with the given filtration value (default value is ‘0.0’). 
        # If some of those simplices are already present with a higher filtration value, 
        # their filtration value is lowered.
        # import pdb
        # pdb.set_trace()
        # simplex is a simplex
        # vertical_removal[i] is a list of simplices to be removed
        # if any of the simplices in vertical_removal[i] is a subface of simplex,
        # then do not insert simplex into lower
        for v in vertical_removal[x_coord-1]:
            if v.issubset(simplex):
                break
        else:
            lower.insert(simplex,x_coord)
        counter += 1
        # print progress based on simplex processed and total number of simplices
        # print(f"\rProgress: {100*counter/total_num_simplices:.2f}%", flush=True)
    return CLFiltration(upper=upper,lower=lower,ladder_length=len_radii,h_params=radii,info={'vertical_removal':vertical_removal_input},enable_validation=False)

def pointCloud2Filtration_legacy(pts:np.array,vertical_removal_input:list,radii:list,max_simplex_dim:int,method:str='cech'):
    """
    Convert a point cloud to a commutative ladder filtration.
    pts: a numpy array of shape (num_pts, dim)
    vertical_removal_input: a list of list of simplices to be removed, notice that it is the name of the simplices, not the indices of the simplices
    radii: a list of radii
    max_simplex_dim: the maximum simplex dimension to be considered
    method: 'cech' or 'rips' or 'alpha'
    """    
    # create a simplex tree
    # truncation it using radius in radii, get a sc
    # create upper row and lower row
    # add simplices in sc to upper row, at the designated radius
    # add simplices in sc.delete(vertical_removal[i]) to lower row, at the designated radius
    # return necessary infos
    len_radii = len(radii)
    if isinstance(vertical_removal_input[0],(int, np.int64)): #[2,3,4,5,6,7]
        # constant removal
        vertical_removal=[[(vertex,) for vertex in vertical_removal_input]]*len_radii
        # print(vertical_removal)
    else:
        # vertical_removal_input is a list of list of simplices
        # should be decreasing
        assert all(set(vertical_removal_input[i]).issuperset(vertical_removal_input[i+1]) for i in range(len(vertical_removal_input)-1))
        #example: [[(2,),(3,),(4,),(5,)],[(2,),(3,),(4,)],[(2,),(3,)]]
        # canonically, vertical_removal is a list of list of simplices
        # each entry of vertical_removal is a list of simplices to be removed, for example [(1,),(2,3)]
        assert len(vertical_removal_input)==len_radii
        vertical_removal = [*vertical_removal_input] # just a change of name
    #check that radii is sorted
    assert all(radii[i]<=radii[i+1] for i in range(len_radii-1))
    print("Creating filtration...", flush=True)
    parentalST=SimplexTree()
    parentalST.from_point_cloud(pts,method=method,sc_dim_ceil=max_simplex_dim,radius_max=max(radii)+EPSILON)

    upper=SimplexTree()
    lower=SimplexTree()
    for i,radius in enumerate(radii):
        x_coord=i+1
        sc=parentalST.truncation(radius)
        # breakpoint()
        # import pdb
        # pdb.set_trace()
        # for simplex in sc.simplices:
        for simplex,fv in sc.get_simplices(): # for faster performance
            # if len(simplex)<=max_simplex_dim+1:
            upper.insert(simplex,x_coord) 
                # this function will not make existing filtration value higher
                # This function inserts the given N-simplex 
                # and its subfaces with the given filtration value (default value is ‘0.0’). 
                # If some of those simplices are already present with a higher filtration value, 
                # their filtration value is lowered.
        # for simplex in sc.delete_simplices(vertical_removal[i]).simplices:
        for simplex,fv in sc.delete_simplices(vertical_removal[i]).get_simplices(): # for faster performance
            # if len(simplex)<=max_simplex_dim+1:
            lower.insert(simplex,x_coord)
        print(f"Progress: {100*(i+1)/len(radii):.2f}%", flush=True)
    return CLFiltration(upper=upper,lower=lower,ladder_length=len_radii,h_params=radii,info={'vertical_removal':vertical_removal_input},enable_validation=False)