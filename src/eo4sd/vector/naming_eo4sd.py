#! /usr/bin/env python3
# -*- coding: utf-8 -*-


import re


DESCRIPTION = "Naming is in accord with specification."
IS_SYSTEM = False


def run_check(params, status):
    # Find the shp file.
    shp_filepaths = [path for path in params["unzip_dir"].glob("**/*") if path.is_file() and path.suffix.lower() == ".shp"]
    if len(shp_filepaths) == 0:
        status.aborted("No shapefile has been found in the delivery.")
        return
    if len(shp_filepaths) > 1:
        status.aborted("More than one shapefile have been found in the delivery: {:s}."
                       .format(", ".join(path.name for path in shp_filepaths)))
        return
    shp_filepath = shp_filepaths[0]

    # Check layer name.
    mobj = re.compile(params["layer_regex"], re.IGNORECASE).search(shp_filepath.stem)
    if mobj is None:
        status.aborted("Layer {:s} has illegal name.".format(shp_filepath.stem))
        return

    # Check place and convert it to uppercase.
    place = mobj.group("place").upper()

    # Get layers.
    layer_defs = {"al": {"src_filepath": shp_filepath,
                         "src_layer_name": shp_filepath.stem,
                         "place": place}}

    status.add_params({"layer_defs": layer_defs})