from receiver.config import dcmtk_config


def test_dcmtk_config_does_not_require_obsolete_dcmin_setting():
    config = dcmtk_config({"DCMTK_BIN": "/usr/bin"})

    assert config.dcmtk_bin == "/usr/bin"
    assert config.dcmin == ""
