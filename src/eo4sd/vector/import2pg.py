#!/usr/bin/env python3
# -*- coding: utf-8 -*-


from subprocess import run


DESCRIPTION = "The layers can be imported into PostGIS database."
IS_SYSTEM = True


def run_check(params, status):
    from osgeo import ogr
    from osgeo.gdalconst import OF_READONLY

    from qc_tool.vector.helper import do_layers

    dsn, schema =  params["connection_manager"].get_dsn_schema()

    # Import all layers found in layer_defs.
    for layer_def in params["layer_defs"].values():
        layer_name = layer_def["src_layer_name"]

        # detect srs from layer_name
        ds = ogr.Open(str(layer_def["src_filepath"]))
        layer = ds.GetLayerByName(layer_def["src_layer_name"])
        srs = layer.GetSpatialRef()
        srs.AutoIdentifyEPSG()
        authority_name = srs.GetAuthorityName(None)
        authority_code = srs.GetAuthorityCode(None)
        if authority_name == "EPSG":
            authority_code = int(authority_code)

        # layer type parameter (MULTIPOLYGON or LINE)
        nlt = "MULTIPOLYGON"
        if "layer_type" in params:
            nlt = params["layer_type"]

        pc = run(["ogr2ogr",
                  "-overwrite",
                  "-a_srs", "EPSG:{:d}".format(authority_code),
                  "-f", "PostgreSQL",
                  "-lco", "SCHEMA={:s}".format(schema),
                  "-lco", "PRECISION=NO",
                  "-nlt", nlt,
                  "PG:{:s}".format(dsn),
                  str(layer_def["src_filepath"]),
                  layer_name])
        if pc.returncode != 0:
            status.aborted("Failed to import layer {:s} into PostGIS.".format(layer_name))
        else:
            # ogr2ogr not always returns non-zero exit code in case of error.
            # Therefore we try some checking whether the layer has been imported correctly.

            ## Open datasource from filesystem.
            src_datasource = ogr.Open(str(layer_def["src_filepath"]), OF_READONLY)
            src_layer = src_datasource.GetLayerByName(layer_name)

            ## Open datasource from postgis.
            conn_string = "PG:{:s} active_schema={:s}".format(dsn, schema)
            dst_datasource = ogr.Open(conn_string, OF_READONLY)
            # NOTE: GetLayerByName() works case insensitive in this case.
            dst_layer = dst_datasource.GetLayerByName(layer_name)
            if dst_layer is None:
                status.aborted("Just imported layer {:s} can not be found in postgis.".format(layer_name))
            else:
                ## Set pg info back to layer_defs.
                ##
                ## FIXME: such construct is not really clear while it exploits mutable dictionaries
                ## and bypasses currently standard use of status.add_params().
                layer_def["pg_layer_name"] = layer_name.lower()
                layer_def["pg_fid_name"] = dst_layer.GetFIDColumn().lower()
                if layer_def["pg_fid_name"] == "objectid":
                    layer_def["fid_display_name"] = "objectid"
                else:
                    layer_def["fid_display_name"] = "row number"

                ## Ensure all features has been imported.
                src_count = src_layer.GetFeatureCount()
                dst_count = dst_layer.GetFeatureCount()
                if src_count != dst_count:
                    status.aborted("Imported layer {:s} has only {:d} out of {:d} features loaded."
                                   .format(layer_name, dst_count, src_count))
