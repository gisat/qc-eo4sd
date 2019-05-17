#! /usr/bin/env python3
# -*- coding: utf-8 -*-


DESCRIPTION = "Features use specific codes in specific attributes."
IS_SYSTEM = False


def get_invalid_codes_message(cursor, error_table_name, pg_layer_name, pg_fid_name,
                              code_column_name, limit=50):
    # Get invalid codes
    sql = ("SELECT DISTINCT {0:s} "
           "FROM {1:s} "
           "WHERE {2:s} IN (SELECT {3:s} FROM {4:s}) "
           "ORDER BY {5:s};")
    sql = sql.format(code_column_name,
                     pg_layer_name,
                     pg_fid_name,
                     pg_fid_name,
                     error_table_name,
                     code_column_name)
    cursor.execute(sql)
    items = [row[0] for row in cursor.fetchmany(limit)]
    if len(items) == 0:
        return None

    # Prepare and shorten the message.
    message = ", ".join(map(str, items))
    return message


def run_check(params, status):
    from qc_tool.vector.helper import do_layers
    from qc_tool.vector.helper import get_failed_items_message

    cursor = params["connection_manager"].get_connection().cursor()
    for layer_def in do_layers(params):
        for column_name, allowed_codes in params["column_defs"]:

            # check product_attrs, replacing YEAR1 with actual year and YEAR2 with
            if layer_def["year1"] is not None and layer_def["year1"] in column_name:
                column_name = column_name.replace("year1", layer_def["year1"])
            elif layer_def["year2"] is not None and layer_def["year2"] in column_name:
                column_name = column_name.replace("year2", layer_def["year1"])

            # Prepare clause excluding features with non-null value of specific column.
            if "exclude_column_name" in params:
                exclude_clause = "AND {:s} IS NULL".format(params["exclude_column_name"])
            else:
                exclude_clause = ""

            # Prepare parameters used in sql clauses.
            sql_params = {"fid_name": layer_def["pg_fid_name"],
                          "layer_name": layer_def["pg_layer_name"],
                          "column_name": column_name,
                          "exclude_clause": exclude_clause,
                          "error_table": "s{:02d}_{:s}_{:s}_error".format(params["step_nr"], layer_def["pg_layer_name"], column_name)}

            # Create table of error items.
            sql = ("CREATE TABLE {error_table} AS"
                   " SELECT {fid_name}"
                   " FROM {layer_name}"
                   " WHERE"
                   "  ({column_name} IS NULL"
                   "   OR {column_name} NOT IN %s)"
                   "  {exclude_clause};")
            sql = sql.format(**sql_params)
            cursor.execute(sql, [tuple(allowed_codes)])

            # Report error items.
            items_message = get_failed_items_message(cursor, sql_params["error_table"], layer_def["pg_fid_name"])
            if items_message is not None:
                invalid_codes_message = get_invalid_codes_message(cursor,
                                                                  sql_params["error_table"],
                                                                  layer_def["pg_layer_name"],
                                                                  layer_def["pg_fid_name"],
                                                                  sql_params["column_name"])
                status.failed("Layer {:s} has column {:s} with invalid codes in features with {:s}: {:s}. Invalid codes are: {:s}."
                              .format(layer_def["pg_layer_name"], column_name, layer_def["fid_display_name"], items_message, invalid_codes_message))
                status.add_error_table(sql_params["error_table"], layer_def["pg_layer_name"], layer_def["pg_fid_name"])