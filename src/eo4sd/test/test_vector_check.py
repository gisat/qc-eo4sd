#!/usr/bin/env python3


from pathlib import Path

import osgeo.ogr as ogr

from qc_tool.common import CONFIG
from qc_tool.common import TEST_DATA_DIR
from qc_tool.test.helper import VectorCheckTestCase


class Test_format(VectorCheckTestCase):
    def setUp(self):
        super().setUp()
        filepath = self.params["jobdir_manager"].tmp_dir.joinpath("test.shp")
        self.params.update({"layer_defs": {"status": {"src_filepath": filepath,
                                                      "src_layer_name": filepath.stem}},
                            "layers": ["status"],
                            "drivers": {".shp": "ESRI Shapefile"}})
        dsrc = ogr.GetDriverByName("ESRI Shapefile").CreateDataSource(str(filepath))
        dsrc.CreateLayer("status")
        dsrc.FlushCache()

    def test(self):
        from eo4sd.vector.format import run_check
        status  = self.status_class()
        run_check(self.params, status)
        self.assertEqual("ok", status.status)

    def test_wrong_ext(self):
        from eo4sd.vector.format import run_check
        self.params["drivers"] = {".gdb": "FileGDB"}
        status  = self.status_class()
        run_check(self.params, status)
        self.assertEqual("aborted", status.status)
        self.assertEqual("The source file has forbidden extension: '.shp'.", status.messages[0])

    def test_wrong_driver(self):
        from eo4sd.vector.format import run_check
        self.params["drivers"] = {".shp": "FileGDB"}
        status  = self.status_class()
        run_check(self.params, status)
        self.assertEqual("aborted", status.status)
        self.assertEqual("The file format is invalid.", status.messages[0])

    def test_wrong_content(self):
        from eo4sd.vector.format import run_check
        self.params["layer_defs"]["status"]["src_filepath"].write_text("Bad file content.")
        status  = self.status_class()
        run_check(self.params, status)
        self.assertEqual("aborted", status.status)
        self.assertEqual("The source file can not be opened.", status.messages[0])

    def test_missing_file(self):
        from eo4sd.vector.format import run_check
        self.params["layer_defs"]["status"]["src_filepath"] = Path("/missing/file.shp")
        status  = self.status_class()
        run_check(self.params, status)
        self.assertEqual("aborted", status.status)
        self.assertEqual("The source file can not be opened.", status.messages[0])


class Test_overlap(VectorCheckTestCase):
    def setUp(self):
        super().setUp()
        self.cursor = self.params["connection_manager"].get_connection().cursor()
        self.cursor.execute("CREATE TABLE test_layer (fid integer, wkb_geometry geometry(Polygon, 4326));")
        self.params.update({"layer_defs": {"layer_1": {"pg_layer_name": "test_layer",
                                                       "pg_fid_name": "fid",
                                                       "fid_display_name": "row number"}},
                            "layers": ["layer_1"],
                            "step_nr": 1,
                            "limit": 0.1})

    def test_non_overlapping(self):
        from eo4sd.vector.overlap import run_check
        self.cursor.execute("INSERT INTO test_layer VALUES (1, ST_MakeEnvelope(0, 0, 1, 1, 4326)),"
                                                         " (2, ST_MakeEnvelope(2, 0, 3, 1, 4326)),"
                                                         " (3, ST_MakeEnvelope(3, 1, 4, 2, 4326)),"
                                                         " (4, ST_MakeEnvelope(4, 1, 5, 2, 4326));")
        status = self.status_class()
        run_check(self.params, status)
        self.assertEqual("ok", status.status)

    def test_overlapping_in_limit(self):
        from eo4sd.vector.overlap import run_check
        self.cursor.execute("INSERT INTO test_layer VALUES (1, ST_MakeEnvelope(0, 0, 1, 1, 4326)),"
                                                         " (2, ST_MakeEnvelope(0.9, 0, 2, 1, 4326)),"
                                                         " (2, ST_MakeEnvelope(1.8, 0, 3, 1, 4326));")
        status = self.status_class()
        run_check(self.params, status)
        self.assertEqual("ok", status.status)

    def test_overlapping_out_of_limit(self):
        from eo4sd.vector.overlap import run_check
        self.cursor.execute("INSERT INTO test_layer VALUES (1, ST_MakeEnvelope(0, 0, 1, 1, 4326)),"
                                                         " (2, ST_MakeEnvelope(0.79, 0, 2, 1, 4326)),"
                                                         " (3, ST_MakeEnvelope(1.7, 0, 3, 1, 4326));")
        status = self.status_class()
        run_check(self.params, status)
        self.assertEqual("failed", status.status)
        self.cursor.execute("SELECT fid FROM s01_test_layer_error ORDER BY fid;")
        self.assertListEqual([(1,), (2,), (3,)], self.cursor.fetchall())

    def test_contains(self):
        from eo4sd.vector.overlap import run_check
        self.cursor.execute("INSERT INTO test_layer VALUES (1, ST_MakeEnvelope(0, 0, 2, 1, 4326)),"
                                                         " (2, ST_MakeEnvelope(0, 0, 0.5, 1, 4326)),"
                                                         " (3, ST_MakeEnvelope(1, 0, 1.001, 1, 4326));")
        status = self.status_class()
        run_check(self.params, status)
        self.assertEqual("failed", status.status)
        self.cursor.execute("SELECT fid FROM s01_test_layer_error ORDER BY fid;")
        self.assertListEqual([(1,), (2,), (3,)], self.cursor.fetchall())
