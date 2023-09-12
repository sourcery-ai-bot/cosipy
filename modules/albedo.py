import numpy as np
from constants import *
import sys

def updateAlbedo(GRID, evdiff):
    """ This methods updates the albedo """

    if albedo_method != 'Oerlemans98':
        print('Albedo parameterisation ', albedo_method, ' not available, using default')
    return method_Oerlemans(GRID,evdiff)

def method_Oerlemans(GRID,evdiff):
    # Check if snow or ice
    if (GRID.get_node_density(0) <= snow_ice_threshold):
        # Get current snowheight from layer height
        idx = (next((i for i, x in enumerate(GRID.get_density()) if x >= snow_ice_threshold), None))
        h = np.sum(GRID.get_height()[:idx])

        # Surface albedo according to Oerlemans & Knap 1998, JGR)
        alphaSnow = albedo_firn + (albedo_fresh_snow - albedo_firn) *  np.exp((-evdiff) / (albedo_mod_snow_aging * 24.0))
        return alphaSnow + (albedo_ice - alphaSnow) * np.exp(
            (-1.0 * h) / (albedo_mod_snow_depth / 100.0)
        )

    else:
        # If no snow cover than set albedo to ice albedo
        return albedo_ice

### idea; albedo decay like (Brock et al. 2000)? or?
### Schmidt et al 2017 >doi:10.5194/tc-2017-67, 2017 use the same albedo parameterisation from Oerlemans and Knap 1998 with a slight updated implementation of considering the surface temperature?
