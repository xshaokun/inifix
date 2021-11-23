import os
import shutil
from pathlib import Path
from stat import S_IREAD

import pytest

from inifix import load
from inifix.format import iniformat
from inifix.format import main


@pytest.mark.parametrize("flag", ["-i", "--inplace"])
def test_format_keep_data(flag, inifile, capsys, tmp_path):
    target = tmp_path / inifile.name

    ref_data = load(inifile)
    shutil.copyfile(inifile, target)

    ret = main([str(target), flag])
    assert isinstance(ret, int)

    out, err = capsys.readouterr()

    # nothing to output to stdout with --inplace
    assert out == ""
    if err == f"{target} is already formatted\n":
        assert ret == 0
    else:
        assert err == f"Fixing {target}\n"
        assert ret != 0

    data_new = load(target)
    assert data_new == ref_data


@pytest.mark.parametrize("infile", ("format-in.ini", "format-out.ini"))
def test_exact_format_stdout(infile, capsys, tmp_path):
    DATA_DIR = Path(__file__).parent / "data"

    expected = (DATA_DIR / "format-out.ini").read_text() + "\n"

    target = tmp_path / "out.ini"
    shutil.copyfile(DATA_DIR / infile, target)
    baseline = target.read_text() + "\n"

    ret = main([str(target)])
    out, err = capsys.readouterr()

    assert out == expected
    if err == f"{target} is already formatted\n":
        assert ret == 0
        assert out == baseline
    else:
        assert err == f"Fixing {target}\n"
        assert ret != 0
        assert out != ""


@pytest.mark.parametrize("flag", ["-i", "--inplace"])
def test_exact_format_inplace(flag, capsys, tmp_path):
    DATA_DIR = Path(__file__).parent / "data"
    target = tmp_path / "out.ini"
    shutil.copyfile(DATA_DIR / "format-in.ini", target)

    ret = main([str(target), flag])
    out, err = capsys.readouterr()

    if err == f"{target} is already formatted\n":
        assert ret == 0
    else:
        assert err == f"Fixing {target}\n"
        assert ret != 0

    expected = (DATA_DIR / "format-out.ini").read_text()
    res = target.read_text()
    assert res == expected


@pytest.mark.parametrize("size", ["10", "20", "50"])
@pytest.mark.filterwarnings(r"ignore:^The following parameters\n")
def test_exact_format_with_column_size_flag(size, capsys, tmp_path):
    DATA_DIR = Path(__file__).parent / "data"
    target = tmp_path / "out.ini"
    shutil.copyfile(DATA_DIR / "format-column-size-in.ini", target)

    ret = main([str(target), "-i", "--name-column-size", size])
    out, err = capsys.readouterr()

    assert err == f"Fixing {target}\n"
    assert ret != 0

    expected = (DATA_DIR / f"format-column-size-out-{size}.ini").read_text()
    res = target.read_text()
    assert res == expected


def test_missing_file(capsys, tmp_path):
    target = tmp_path / "not_a_file"
    ret = main([str(target)])
    assert ret != 0
    out, err = capsys.readouterr()
    assert out == ""
    assert err == f"Error: could not find {target}\n"


def test_empty_file(capsys, tmp_path):
    target = tmp_path / "invalid_file"
    target.touch()
    ret = main([str(target)])
    assert ret != 0
    out, err = capsys.readouterr()
    assert out == "\n"
    assert f"Error: {target} appears to be emtpy.\n" in err


def test_error_read_only_file(inifile, capsys, tmp_path):
    target = tmp_path / inifile.name
    shutil.copy(inifile, target)

    data = target.read_text()
    if iniformat(data) == data:
        return

    os.chmod(target, S_IREAD)

    ret = main([str(target), "--inplace"])
    assert ret != 0
    out, err = capsys.readouterr()
    assert out == ""
    assert f"Error: could not write to {target}\n" in err


def test_write_to_console(inifile, capsys, tmp_path):
    target = tmp_path / inifile.name
    shutil.copy(inifile, target)

    baseline = target.read_text() + "\n"

    ret = main([str(target)])
    # we can't predict if formatting is needed
    assert isinstance(ret, int)
    out, err = capsys.readouterr()

    if err == f"{target} is already formatted\n":
        assert ret == 0
        assert out == baseline
    else:
        assert err == f"Fixing {target}\n"
        assert ret != 0
        assert out != ""
