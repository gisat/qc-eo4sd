#! /usr/bin/env python3


DESCRIPTION = "There is no couple of polygons overlapping beyond the limit."
IS_SYSTEM = False


def run_check(params, status):
    from qc_tool.vector.helper import do_layers
    from qc_tool.vector.helper import get_failed_items_message

    cursor = params["connection_manager"].get_connection().cursor()
    for layer_def in do_layers(params):
        # Prepare parameters used in sql clauses.
        sql_params = {"fid_name": layer_def["pg_fid_name"],
                      "layer_name": layer_def["pg_layer_name"],
                      "error_table": "s{:02d}_{:s}_error".format(params["step_nr"], layer_def["pg_layer_name"])}
        sql_exec_params = {"limit": -params["limit"]}

        # Create table of error items.
        sql = ("CREATE TABLE {error_table} AS"
               " SELECT DISTINCT unnest(ARRAY[ta.{fid_name}, tb.{fid_name}]) AS {fid_name}"
               " FROM {layer_name} ta, {layer_name} tb"
               " WHERE"
               "  ta.{fid_name} < tb.{fid_name}"
               "  AND ta.wkb_geometry && tb.wkb_geometry"
               "  AND (NOT ST_Relate(ta.wkb_geometry, tb.wkb_geometry, '**T***T**')"
               "       OR NOT ST_IsEmpty(ST_Buffer(ST_Intersection(ta.wkb_geometry, tb.wkb_geometry), %(limit)s)));")
        sql = sql.format(**sql_params)
        cursor.execute(sql, sql_exec_params)

        # Report error items.
        items_message = get_failed_items_message(cursor, sql_params["error_table"], layer_def["pg_fid_name"])
        if items_message is not None:
            status.failed("Layer {:s} has overlapping pairs in features with {:s}: {:s}."
                          .format(layer_def["pg_layer_name"], layer_def["fid_display_name"], items_message))
            status.add_error_table(sql_params["error_table"], layer_def["pg_layer_name"], layer_def["pg_fid_name"])
