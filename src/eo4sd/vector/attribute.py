#! /usr/bin/env python3
# -*- coding: utf-8 -*-


import re


DESCRIPTION = "Attribute table is composed of prescribed attributes."
IS_SYSTEM = False


def run_check(params, status):
    import osgeo.ogr as ogr

    from qc_tool.vector.helper import do_layers


    OGR_TYPES = {ogr.OFTBinary: "binary",
                 ogr.OFTDate: "date",
                 ogr.OFTDateTime: "datetime",
                 ogr.OFTInteger: "integer",
                 ogr.OFTInteger64: "integer64",
                 ogr.OFTInteger64List: "list-of-integer64",
                 ogr.OFTIntegerList: "list-of-integer",
                 ogr.OFTReal: "real",
                 ogr.OFTRealList: "list-of-real",
                 ogr.OFTString: "string",
                 ogr.OFTStringList: "list-of-string",
                 ogr.OFTTime: "time",
                 ogr.OFTWideString: "wide-string",
                 ogr.OFTWideStringList: "list-of-wide-string"}

    ALLOWED_TYPES = {ogr.OFTInteger: "numeric",
                     ogr.OFTInteger64: "numeric",
                     ogr.OFTReal: "numeric",
                     ogr.OFTString: "string",
                     ogr.OFTWideString: "string"}

    for layer_def in do_layers(params):
        ds = ogr.Open(str(layer_def["src_filepath"]))
        layer = ds.GetLayerByName(layer_def["src_layer_name"])

        # check product_attrs, replacing YEAR1 with actual year and YEAR2 with
        product_attrs = {}
        for attr_name, attr_type_names in params["attributes"].items():
            if layer_def["year1"] is not None and layer_def["year1"] in attr_name:
                new_attr_name = attr_name.replace("YEAR1", layer_def["year1"])
                product_attrs[new_attr_name] = attr_type_names
            elif layer_def["year2"] is not None and layer_def["year2"] in attr_name:
                new_attr_name = attr_name.replace("YEAR2", layer_def["year2"])
                product_attrs[new_attr_name] = attr_type_names
            else:
                product_attrs[attr_name] = attr_type_names

        extra_attrs = {}
        for field_defn in layer.schema:
            field_type = field_defn.GetType()
            field_name = field_defn.name
            if field_name not in product_attrs:
                # extra field
                continue
            if field_type not in OGR_TYPES:
                # Field type is unknown.
                del product_attrs[field_name]
            elif field_type not in ALLOWED_TYPES:
                # Field type is not allowed.
                del product_attrs[field_name]
            elif ALLOWED_TYPES[field_type] not in product_attrs[field_name]:
                # Field does not match a type in product definition.
                extra_attrs[field_name] = ALLOWED_TYPES[field_type]
            else:
                # Field matches product definition.
                del product_attrs[field_name]
        missing_attrs = product_attrs

        if len(extra_attrs) > 0:
            status.aborted("Layer {:s} has attributes in incorrect format: {:s}."
                          .format(layer_def["src_layer_name"],
                                  ", ".join("{:s}({:s})".format(attr_name, ",".join(extra_attrs[attr_name]))
                                            for attr_name in sorted(extra_attrs.keys()))))

        if len(missing_attrs) > 0:
            status.aborted("Layer {:s} has missing attributes: {:s}."
                           .format(layer_def["src_layer_name"],
                                   ", ".join("{:s}({:s})".format(attr_name, ",".join(missing_attrs[attr_name]))
                                             for attr_name in sorted(missing_attrs.keys()))))
