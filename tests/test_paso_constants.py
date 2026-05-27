"""Tests for paso_constants.py — field mapping constants and helpers."""
import pytest
from paso_constants import (
    APPEND_FIELD_MAPPING_POINT_TEMPLATE,
    APPEND_FIELD_MAPPING_POLYGON_TEMPLATE,
    ERASE_CURSOR_FIELDS,
    FIELD_DETAILS_POINT,
    FIELD_DETAILS_POLYGON,
    GTM_WKT,
    MONTO_YEARLY_FIELDS,
    WFL_FIELD_MAPPING_POINT,
    WFL_FIELD_MAPPING_POLYGON,
    build_append_field_mapping,
    build_wfl_field_mapping,
    quarter_name,
)


class TestFieldDetails:
    def test_point_fields_not_empty(self):
        assert len(FIELD_DETAILS_POINT) > 0

    def test_polygon_fields_not_empty(self):
        assert len(FIELD_DETAILS_POLYGON) > 0

    def test_point_has_area_ha(self):
        assert "Area_ha" in FIELD_DETAILS_POINT
        assert FIELD_DETAILS_POINT["Area_ha"]["type"] == "Double"

    def test_polygon_has_cdg(self):
        assert "CdgActvdd" in FIELD_DETAILS_POLYGON
        assert FIELD_DETAILS_POLYGON["CdgActvdd"]["type"] == "Text"


class TestAppendTemplates:
    def test_polygon_template_not_empty(self):
        assert len(APPEND_FIELD_MAPPING_POLYGON_TEMPLATE) >= 30

    def test_point_template_not_empty(self):
        assert len(APPEND_FIELD_MAPPING_POINT_TEMPLATE) >= 30

    def test_polygon_contains_area_ha(self):
        joined = ";".join(APPEND_FIELD_MAPPING_POLYGON_TEMPLATE)
        assert "Area_ha" in joined

    def test_polygon_contains_placeholder(self):
        joined = ";".join(APPEND_FIELD_MAPPING_POLYGON_TEMPLATE)
        assert "{input_fc}" in joined

    def test_point_contains_codigo(self):
        joined = ";".join(APPEND_FIELD_MAPPING_POINT_TEMPLATE)
        assert "CÓDIGO_DE_LA_ACTIVIDAD" in joined


class TestWFLMappings:
    def test_wfl_point_not_empty(self):
        assert len(WFL_FIELD_MAPPING_POINT) >= 30

    def test_wfl_polygon_not_empty(self):
        assert len(WFL_FIELD_MAPPING_POLYGON) >= 30

    def test_wfl_point_has_required_keys(self):
        for entry in WFL_FIELD_MAPPING_POINT:
            assert "field" in entry
            assert "alias" in entry
            assert "type" in entry
            assert "src" in entry
            assert "range" in entry

    def test_wfl_polygon_has_required_keys(self):
        for entry in WFL_FIELD_MAPPING_POLYGON:
            assert "field" in entry
            assert "type" in entry


class TestEraseCursorFields:
    def test_not_empty(self):
        assert len(ERASE_CURSOR_FIELDS) > 0

    def test_contains_objectid(self):
        assert "OBJECTID" in ERASE_CURSOR_FIELDS

    def test_contains_erase_fc(self):
        assert "Erase_FC" in ERASE_CURSOR_FIELDS


class TestMontoFields:
    def test_has_seven_years(self):
        assert len(MONTO_YEARLY_FIELDS) == 7

    def test_contains_2020(self):
        assert any("2020" in f for f in MONTO_YEARLY_FIELDS)

    def test_contains_2026(self):
        assert any("2026" in f for f in MONTO_YEARLY_FIELDS)


class TestGTMWKT:
    def test_is_projcs(self):
        assert GTM_WKT.startswith("PROJCS")

    def test_contains_transverse_mercator(self):
        assert "Transverse_Mercator" in GTM_WKT

    def test_central_meridian(self):
        assert "-90.5" in GTM_WKT


class TestBuildWflFieldMapping:
    def test_basic_output(self):
        fields = [
            {"field": "Area_ha", "alias": "Area_ha", "length": 0,
             "type": "Double", "src": "Area_ha", "range": "-1,-1"},
        ]
        result = build_wfl_field_mapping(fields, r"C:\test.gdb\layer")
        assert "Area_ha" in result
        assert r"C:\test.gdb\layer" in result

    def test_multiple_fields_joined_by_semicolon(self):
        fields = [
            {"field": "A", "alias": "A", "length": 10, "type": "Text", "src": "A", "range": "0,9"},
            {"field": "B", "alias": "B", "length": 8, "type": "Double", "src": "B", "range": "-1,-1"},
        ]
        result = build_wfl_field_mapping(fields, "layer")
        assert result.count(";") == 1


class TestBuildAppendFieldMapping:
    def test_replaces_placeholder(self):
        template = [
            'Area_ha "Area_ha" true true false 8 Double 0 0,First,#,{input_fc},Area_ha,-1,-1',
        ]
        result = build_append_field_mapping(template, "my_fc")
        assert "my_fc" in result
        assert "{input_fc}" not in result

    def test_joins_with_semicolon(self):
        template = [
            'F1 "F1" true true false 8 Double 0 0,First,#,{input_fc},F1,-1,-1',
            'F2 "F2" true true false 8 Text 0 0,First,#,{input_fc},F2,0,7',
        ]
        result = build_append_field_mapping(template, "fc")
        assert result.count(";") == 1


class TestQuarterName:
    def test_basic(self):
        assert quarter_name(2025, 3) == "T2025_Q3"

    def test_q1(self):
        assert quarter_name(2024, 1) == "T2024_Q1"
