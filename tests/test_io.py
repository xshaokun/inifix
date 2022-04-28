import difflib
import re
import tempfile
from pathlib import Path

import pytest

from inifix.io import _tokenize_line
from inifix.io import dump
from inifix.io import dumps
from inifix.io import load
from inifix.io import loads
from inifix.io import Section


@pytest.mark.parametrize(
    "invalid_data", ["", "SingleToken", "[InvalidSectionName", "InvalidSection]"]
)
def test_tokenizer(invalid_data):
    with pytest.raises(ValueError):
        _tokenize_line(invalid_data, file="fake_filename", line_number=-1)


def test_unit_read(inifile):
    load(inifile)


def test_idempotent_io(inifile):
    data0 = load(inifile)
    with tempfile.TemporaryDirectory() as tmpdir:
        save1 = Path(tmpdir) / "save1"
        save2 = Path(tmpdir) / "save2"
        dump(data0, save1)
        data1 = load(save1)
        dump(data1, save2)

        text1 = save1.read_text().split("\n")
        text2 = save2.read_text().split("\n")

        diff = "".join(difflib.context_diff(text1, text2))
        assert not diff


@pytest.mark.parametrize(
    "data, expected",
    [
        ("""val content\n""", {"val": "content"}),
        ("""val 'content'\n""", {"val": "content"}),
        ("""val content"\n""", {"val": 'content"'}),
        ("""val "content\n""", {"val": '"content'}),
        ("""val content'\n""", {"val": "content'"}),
        ("""val 'content\n""", {"val": "'content"}),
        ("""val "content"\n""", {"val": "content"}),
        ("""val "content'"\n""", {"val": "content'"}),
        ("""val '"content"'\n""", {"val": '"content"'}),
        ("""val "'content'"\n""", {"val": "'content'"}),
        ("""val true\n""", {"val": True}),
        ("""val "true"\n""", {"val": "true"}),
        ("""val 'true'\n""", {"val": "true"}),
        ("""val false\n""", {"val": False}),
        ("""val "false"\n""", {"val": "false"}),
        ("""val 'false'\n""", {"val": "false"}),
        ("""val 1\n""", {"val": 1}),
        ("""val "1"\n""", {"val": "1"}),
        ("""val '1'\n""", {"val": "1"}),
        ("""val 1e2\n""", {"val": 100}),
        ("""val "1e2"\n""", {"val": "1e2"}),
        ("""val '1e2'\n""", {"val": "1e2"}),
        (
            "name true 'true'     'steven bacon'  1",
            {"name": [True, "true", "steven bacon", 1]},
        ),
    ],
)
def test_string_casting(data, expected):
    mapping = loads(data)
    assert mapping == expected


@pytest.mark.parametrize(
    "data, expected",
    [
        ('''[Spam]\nEggs "Bacon Saussage"''', {"Spam": {"Eggs": "Bacon Saussage"}}),
        (
            "name true 'true'     'steven   bacon'  1",
            {"name": [True, "true", "steven   bacon", 1]},
        ),
    ],
)
def test_idempotent_string_parsing(data, expected):
    initial_mapping = loads(data)
    assert initial_mapping == expected
    round_str = dumps(initial_mapping)
    round_mapping = loads(round_str)
    assert round_mapping == initial_mapping


def test_section_init():
    data = {
        "dummy": [0.0001, True],
        "thisparameternameshouldprobablybeshorter": [45, 68],
        "thisoneisshorter": [15, 68, 774, 6, 7, 5],
        "faultyTowers": 42,
    }
    s1 = Section(data)
    assert s1.name is None

    s2 = Section(data, name="test")
    assert s2.name == "test"


def test_invalid_section_value():
    val = frozenset((1, 2, 3))
    data = {
        "yes": val,
    }
    with pytest.raises(
        TypeError,
        match=re.escape(
            "Expected all values to be scalars or lists of scalars. "
            f"Received invalid values {val}"
        ),
    ):
        Section(data)


def test_invalid_section_key():
    data = {
        1: True,
    }
    with pytest.raises(
        TypeError, match=re.escape("Expected str keys. Received invalid key: 1")
    ):
        Section(data)


@pytest.mark.parametrize(
    "mode,expected_err",
    [("rt", FileNotFoundError), ("rb", FileNotFoundError), ("wb", TypeError)],
)
def test_dump_wrong_mode(mode, expected_err, inifile, tmp_path):
    conf = load(inifile)
    save_file = str(tmp_path / "save.ini")
    with pytest.raises(expected_err):
        with open(save_file, mode=mode) as fh:
            dump(conf, fh)


def test_dump_to_file_descriptor(inifile, tmp_path):
    conf = load(inifile)

    file = tmp_path / "save.ini"
    with open(file, mode="w") as fh:
        dump(conf, fh)

    # a little weak but better than just testing that the file isn't empty
    new_body = file.read_text()
    for key, val in conf.items():
        if isinstance(val, dict):
            assert f"[{key}]\n" in new_body


def test_dump_to_file_path(inifile, tmp_path):
    conf = load(inifile)

    # pathlib.Path obj
    file1 = tmp_path / "save1.ini"
    dump(conf, file1)
    body1 = file1.read_text()

    # str
    file2 = tmp_path / "save2.ini"
    sfile2 = str(file2)
    dump(conf, sfile2)
    body2 = file2.read_text()

    assert body1 == body2
    for key, val in conf.items():
        if isinstance(val, dict):
            assert f"[{key}]\n" in body2


def test_load_empty_file(tmp_path):
    target = tmp_path / "empty_file"
    target.touch()
    with pytest.raises(
        ValueError, match=re.escape(f"{str(target)!r} appears to be empty.")
    ):
        load(target)


def test_load_from_descriptor(inifile):
    with open(inifile) as fh:
        load(fh)


def test_loads_empty_str():
    ret = loads("")
    assert ret == {}


def test_loads_invalid_str():
    with pytest.raises(ValueError, match="Failed to parse line 1: 'invalid'"):
        loads("invalid")


def test_loads_dumps_roundtrip(inifile):
    with open(inifile) as fh:
        data = fh.read()
    d1 = loads(data)
    s1 = dumps(d1)
    d2 = loads(s1)
    assert d1 == d2
