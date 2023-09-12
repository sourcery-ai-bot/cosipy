import numpy as np
from constants import *
from config import *


def percolation(GRID, water, t, debug_level):
    """ Percolation and refreezing of melt water through the snow- and firn pack

    Args:

        GRID    ::  GRID-Structure 
        water   ::  Melt water (m w.e.q.) at the surface
        dt      ::  Integration time

    """

    # Courant-Friedrich Lewis Criteria
    curr_t = 0
    Tnew = 0

    Q = 0  # initial runoff [m w.e.]

    # Get height of snow layers
    hlayers = GRID.get_height()

    # Check stability criteria for diffusion
    dt_stab = c_stab * min(hlayers) / percolation_velocity

    # set liquid water content of top layer (idx, LWCnew) in m
    GRID.set_node_liquid_water_content(0, GRID.get_node_liquid_water_content(0)+float(water))

    # Percolation velocity
    pvel = percolation_velocity

    # upwind scheme to adapt liquid water content of entire GRID
    while curr_t < t:

        # Get local copy
        LWCtmp = np.copy(GRID.get_liquid_water_content())

        # Select appropriate time step
        dt_use = min(dt_stab, t - curr_t)

        # Loop over all internal grid points for percolation 
        for idxNode in range(0, GRID.number_nodes, 1):

            # volumetric ice content (Coleou et Lesaffre, 1998)
            theta_ice = GRID.get_node_density(idxNode)/ice_density

            # maximum volumentric water content (Coleou et Lesaffre, 1998)
            if (theta_ice <= 0.23):
                theta_ret = 0.0264 + 0.0099*((1-theta_ice)/theta_ice) 
            elif (theta_ice > 0.23) & (theta_ice <= 0.812):
                theta_ret = 0.08 - 0.1023*(theta_ice-0.03)
            else:
                theta_ret = 0

            # Set porosity
            GRID.set_node_porosity(idxNode, 1-((GRID.get_node_density(idxNode)-theta_ret*(water_density))/ice_density))

            # Set maximum volumetic ice content
            GRID.set_node_max_vol_ice_content(idxNode, theta_ret)

            if (idxNode==0):
                x = LWCtmp[idxNode] * (1-GRID.get_node_max_vol_ice_content(idxNode))
                xd = LWCtmp[idxNode+1] * (1-GRID.get_node_max_vol_ice_content(idxNode))
                dx = np.abs((GRID.get_node_height(idxNode+1) / 2.0) + (GRID.get_node_height(idxNode) / 2.0))

                ux = 0
                uy = (xd-x)/dx
                GRID.set_node_liquid_water_content(idxNode, LWCtmp[idxNode] + dt_use * (ux * pvel + uy * pvel))

            elif (idxNode==GRID.number_nodes-1):

                xu = LWCtmp[idxNode-1] * (1-GRID.get_node_max_vol_ice_content(idxNode))
                x = LWCtmp[idxNode] * (1-GRID.get_node_max_vol_ice_content(idxNode))
                dx = np.abs((GRID.get_node_height(idxNode-1) / 2.0) + (GRID.get_node_height(idxNode) / 2.0))

                ux = (xu-x)/dx
                uy = 0
                GRID.set_node_liquid_water_content(idxNode, LWCtmp[idxNode] + dt_use * (ux * pvel + uy * pvel))

            else:
                # Percolation of water exceeding the max. retention

                xu = LWCtmp[idxNode-1] * (1-GRID.get_node_max_vol_ice_content(idxNode))
                x = LWCtmp[idxNode] * (1-GRID.get_node_max_vol_ice_content(idxNode))
                xd = LWCtmp[idxNode+1] * (1-GRID.get_node_max_vol_ice_content(idxNode))
                dx1 = np.abs((GRID.get_node_height(idxNode-1) / 2.0) + (GRID.get_node_height(idxNode) / 2.0))
                dx2 = np.abs((GRID.get_node_height(idxNode+1) / 2.0) + (GRID.get_node_height(idxNode) / 2.0))

                ux = (xu-x)/dx1 
                uy = (xd-x)/dx2

                # Calculate runoff in m w.e.q
                if ((GRID.get_node_density(idxNode+1)>=snow_ice_threshold)):
                    Q = Q + dt_use*(uy*pvel)
                    GRID.set_node_liquid_water_content(idxNode, LWCtmp[idxNode] + dt_use * (ux * pvel + uy * pvel))
                    break
                else:
                    GRID.set_node_liquid_water_content(idxNode, LWCtmp[idxNode] + dt_use * (ux * pvel + uy * pvel))

        # Add the time step to current time
        curr_t += dt_use

    # Changes in LWC
    LWCchange = np.sum(LWCtmp) - np.sum(GRID.get_liquid_water_content())

    # Do the refreezing after percolation
    water_refreezed = refreeze(GRID)

    return -Q, water_refreezed, LWCchange


def calc_cc(GRID, node):
    """ Calculates the cold content, the potential latent energy release by refreezing """

    # cold content of the snow at layer node (J m^-2) 
    Qcc = -spec_heat_ice * GRID.get_node_density(node) * GRID.get_node_height(node) * (GRID.get_node_temperature(node)-zero_temperature)
    GRID.set_node_cold_content(node, -Qcc)


def refreeze(GRID):

    # water refreezed
    water_refreezed = 0
    LWCref = 0
    
    # Loop over all internal grid points for percolation 
    for idxNode in range(0, GRID.number_nodes-1, 1):
    
        # Set cold content and potential latent heat energy
        calc_cc(GRID, idxNode)
        
        # potential latent energy if all water is refreezed (J m^-2)
        Qp = lat_heat_melting * water_density * GRID.get_node_liquid_water_content(idxNode)
  
        energy = np.minimum(np.abs(GRID.get_node_cold_content(idxNode)), Qp)

        # Update temperature (warm the snowpack)
        GRID.set_node_temperature(idxNode, GRID.get_node_temperature(idxNode) + (energy/(spec_heat_ice*GRID.get_node_density(idxNode)*GRID.get_node_height(idxNode))) )
        
        # How much water is refreezed [kg m^-2, mm]
        LWCref = np.abs(energy/(lat_heat_melting*water_density))
        GRID.set_node_refreeze(idxNode, LWCref)

        GRID.set_node_liquid_water_content(idxNode, np.maximum(GRID.get_node_liquid_water_content(idxNode)-LWCref,0))

        # Update density (increase density)
        a = GRID.get_node_height(idxNode)*(GRID.get_node_density(idxNode)/ice_density)
        b = LWCref/water_density
        GRID.set_node_density(idxNode, (1-(b/a))*GRID.get_node_density(idxNode)+(b/a)*ice_density)
        
        # Convert kg m^-2 (mm) to m w.e.q.
        water_refreezed = water_refreezed + (LWCref/ice_density)

    return water_refreezed
