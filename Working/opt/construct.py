def expand_hardpoints(flat_params):
    """
    Takes a dictionary with dot-separated keys like 'lower_wishbone_outboard.x'
    and returns a nested dictionary of hardpoints.
    """
    hardpoints = {}
    for key, val in flat_params.items():
        parts = key.split('.')
        if len(parts) == 2:
            hp, coord = parts
            if hp not in hardpoints:
                hardpoints[hp] = {}
            hardpoints[hp][coord] = float(val)
    return hardpoints
