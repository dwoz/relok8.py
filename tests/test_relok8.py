from textwrap import dedent

import pytest
from unittest.mock import MagicMock, patch

from relok8 import is_elf, is_in_dir, is_macho, parse_otool_l, parse_readelf_d, patch_rpath, parse_rpath


def test_is_macko_true(tmp_path):
    lib_path = tmp_path / "test.dylib"
    with open(lib_path, "wb") as fp:
        fp.write(b"\xcf\xfa\xed\xfe")
    assert is_macho(lib_path) == True


def test_is_macko_false(tmp_path):
    lib_path = tmp_path / "test.dylib"
    with open(lib_path, "wb") as fp:
        fp.write(b"\xcf\xfa\xed\xfa")
    assert is_macho(lib_path) == False


def test_is_macko_not_a_file(tmp_path):
    with pytest.raises(IsADirectoryError):
        assert is_macho(tmp_path) == False


def test_is_macko_file_does_not_exist(tmp_path):
    lib_path = tmp_path / "test.dylib"
    with pytest.raises(FileNotFoundError):
        assert is_macho(lib_path) == False


def test_is_elf_true(tmp_path):
    lib_path = tmp_path / "test.so"
    with open(lib_path, "wb") as fp:
        fp.write(b"\x7f\x45\x4c\x46")
    assert is_elf(lib_path) == True


def test_is_elf_false(tmp_path):
    lib_path = tmp_path / "test.so"
    with open(lib_path, "wb") as fp:
        fp.write(b"\xcf\xfa\xed\xfa")
    assert is_elf(lib_path) == False


def test_is_elf_not_a_file(tmp_path):
    with pytest.raises(IsADirectoryError):
        assert is_elf(tmp_path) == False


def test_is_melffile_does_not_exist(tmp_path):
    lib_path = tmp_path / "test.so"
    with pytest.raises(FileNotFoundError):
        assert is_elf(lib_path) == False


def test_parse_otool_l():
    # XXX
    pass


def test_parse_readelf_d_no_rpath():
    section = dedent(
        """
    Dynamic section at offset 0xbdd40 contains 28 entries:
      Tag        Type                         Name/Value
     0x0000000000000001 (NEEDED)             Shared library: [libz.so.1]
     0x0000000000000001 (NEEDED)             Shared library: [libbz2.so.1]
     0x0000000000000001 (NEEDED)             Shared library: [libpng15.so.15]
     0x0000000000000001 (NEEDED)             Shared library: [libc.so.6]
     0x000000000000000e (SONAME)             Library soname: [libfreetype.so.6]
    """
    )
    assert parse_readelf_d(section) == []


def test_parse_readelf_d_rpath():
    section = dedent(
        """
    Dynamic section at offset 0x58000 contains 27 entries:
      Tag        Type                         Name/Value
     0x000000000000000f (RPATH)              Library rpath: [$ORIGIN/../..]
     0x0000000000000001 (NEEDED)             Shared library: [libsqlite3.so.0]
     0x0000000000000001 (NEEDED)             Shared library: [libpthread.so.0]
     0x0000000000000001 (NEEDED)             Shared library: [libc.so.6]
     0x000000000000000c (INIT)               0x51f8
     """
    )
    assert parse_readelf_d(section) == ["$ORIGIN/../.."]


def test_is_in_dir(tmp_path):
    parent = tmp_path / "foo"
    child = tmp_path / "foo" / "bar" / "bang"
    assert is_in_dir(child, parent) == True


def test_patch_rpath(tmp_path):
    path = str(tmp_path / "test")
    new_rpath = str(tmp_path / "lib")
    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        with patch("relok8.parse_rpath", return_value=[str(tmp_path / "old" / "lib")]):
            assert patch_rpath(path, new_rpath) is True


def test_patch_rpath_failed(tmp_path):
    path = str(tmp_path / "test")
    new_rpath = str(tmp_path / "lib")
    with patch("subprocess.run", return_value=MagicMock(returncode=1)):
        with patch("relok8.parse_rpath", return_value=[str(tmp_path / "old" / "lib")]):
            assert patch_rpath(path, new_rpath) is False


def test_patch_rpath_no_change(tmp_path):
    path = str(tmp_path / "test")
    new_rpath = str(tmp_path / "lib")
    with patch("subprocess.run", return_value=MagicMock(returncode=1)):
        with patch("relok8.parse_rpath", return_value=[new_rpath]):
            assert patch_rpath(path, new_rpath) is True