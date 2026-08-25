import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common.text import (
    decode_dcmtk_output,
    fix_utf8_mojibake,
    fix_utf8_mojibake_tree,
)


def test_fixes_schaedel_mojibake():
    # UTF-8 "ä" (C3 A4) decoded as Latin-1 → U+00C3 U+00A4
    broken = "Sch\u00c3\u00a4del axial Knochen"
    assert fix_utf8_mojibake(broken) == "Schädel axial Knochen"


def test_leaves_correct_umlauts():
    assert fix_utf8_mojibake("Schädel sagittal Weichteil") == "Schädel sagittal Weichteil"


def test_leaves_ascii():
    assert fix_utf8_mojibake("CT Thorax") == "CT Thorax"


def test_tree_fixes_nested_series():
    doc = {
        "Category": "parent",
        "_childDocuments_": [{"SeriesDescription": "Sch\u00c3\u00a4del axial Knochen"}],
    }
    out = fix_utf8_mojibake_tree(doc)
    assert out["_childDocuments_"][0]["SeriesDescription"] == "Schädel axial Knochen"


def test_decode_dcmtk_prefers_utf8():
    assert decode_dcmtk_output("Schädel".encode("utf-8")) == "Schädel"


def test_decode_dcmtk_latin1_fallback():
    assert decode_dcmtk_output("Schädel".encode("latin-1")) == "Schädel"
