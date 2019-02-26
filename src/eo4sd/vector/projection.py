#! /usr/bin/env python3
# -*- coding: utf-8 -*-


DESCRIPTION = "Layers use specific projection."
IS_SYSTEM = False


def run_check(params, status):
    import osgeo.ogr as ogr
    import osgeo.osr as osr

    from qc_tool.vector.helper import do_layers

    for layer_def in do_layers(params):
        place = layer_def["place"]
        ds = ogr.Open(str(layer_def["src_filepath"]))
        layer = ds.GetLayerByName(layer_def["src_layer_name"])
        srs = layer.GetSpatialRef()

        if srs is None:
            status.aborted("Layer {:s} has missing spatial reference system.".format(layer_def["src_layer_name"]))
        else:
            srs.AutoIdentifyEPSG()

            # Get epsg code from authority clause.
            authority_name = srs.GetAuthorityName(None)
            authority_code = srs.GetAuthorityCode(None)
            if authority_name == "EPSG":
                # Compare epsg code using the root-level epsg authority in the srs WKT of the layer.
                try:
                    authority_code = int(authority_code)
                except ValueError:
                    status.aborted("Layer {:s} has non integer epsg code {:s}".format(layer_def["src_layer_name"], authority_code))
                else:
                    expected_authority_code = params["epsg"][place]
                    if authority_code != expected_authority_code:
                        status.aborted("Layer {:s} has illegal epsg code {:d}."
                                       "Expected epsg code for {:s} is {:d}"
                                       .format(layer_def["src_layer_name"], authority_code, place, expected_authority_code))
            else:
                # the setting is strict and no epsg code has been found in the srs of the layer.
                status.aborted("Layer {:s} does not have an epsg code or epsg code could not be detected, srs: {:s}."
                               .format(layer_def["src_layer_name"], srs.ExportToWkt()))
