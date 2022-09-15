import pathlib
from textwrap import dedent

import pytest
from unittest.mock import MagicMock, call, patch

from relok8 import is_elf, is_in_dir, is_macho, main, parse_readelf_d, patch_rpath, handle_elf
from tests.helpers import LinuxProject

from argparse import Namespace


def test_is_macho_true(tmp_path):
    lib_path = tmp_path / "test.dylib"
    lib_path.write_bytes(b"\xcf\xfa\xed\xfe")
    assert is_macho(lib_path) is True


def test_is_macho_false(tmp_path):
    lib_path = tmp_path / "test.dylib"
    lib_path.write_bytes(b"\xcf\xfa\xed\xfa")
    assert is_macho(lib_path) is False


def test_is_macho_not_a_file(tmp_path):
    with pytest.raises(IsADirectoryError):
        assert is_macho(tmp_path) is False


def test_is_macho_file_does_not_exist(tmp_path):
    lib_path = tmp_path / "test.dylib"
    with pytest.raises(FileNotFoundError):
        assert is_macho(lib_path) is False


def test_is_elf_true(tmp_path):
    lib_path = tmp_path / "test.so"
    lib_path.write_bytes(b"\x7f\x45\x4c\x46")
    assert is_elf(lib_path) is True


def test_is_elf_false(tmp_path):
    lib_path = tmp_path / "test.so"
    lib_path.write_bytes(b"\xcf\xfa\xed\xfa")
    assert is_elf(lib_path) is False


def test_is_elf_not_a_file(tmp_path):
    with pytest.raises(IsADirectoryError):
        assert is_elf(tmp_path) is False


def test_is_elf_file_does_not_exist(tmp_path):
    lib_path = tmp_path / "test.so"
    with pytest.raises(FileNotFoundError):
        assert is_elf(lib_path) is False


def test_parse_otool_l():
    # XXX
    pass


def test_parse_macho():
    # XXX
    pass


def test_handle_macho():
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
    assert is_in_dir(child, parent) is True


def test_is_in_dir_false(tmp_path):
    parent = tmp_path / "foo"
    child = tmp_path / "bar" / "bang"
    assert is_in_dir(child, parent) is False


def test_patch_rpath(tmp_path):
    path = str(tmp_path / "test")
    new_rpath = str(pathlib.Path("$ORIGIN", "..", "..", "lib"))
    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        with patch("relok8.parse_rpath", return_value=[str(tmp_path / "old" / "lib")]):
            assert patch_rpath(path, new_rpath) == new_rpath


def test_patch_rpath_failed(tmp_path):
    path = str(tmp_path / "test")
    new_rpath = str(pathlib.Path("$ORIGIN", "..", "..", "lib"))
    with patch("subprocess.run", return_value=MagicMock(returncode=1)):
        with patch("relok8.parse_rpath", return_value=[str(tmp_path / "old" / "lib")]):
            assert patch_rpath(path, new_rpath) is False


def test_patch_rpath_no_change(tmp_path):
    path = str(tmp_path / "test")
    new_rpath = str(pathlib.Path("$ORIGIN", "..", "..", "lib"))
    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        with patch("relok8.parse_rpath", return_value=[new_rpath]):
            assert patch_rpath(path, new_rpath, only_relative=False) == new_rpath


def test_patch_rpath_remove_non_relative(tmp_path):
    path = str(tmp_path / "test")
    new_rpath = str(pathlib.Path("$ORIGIN", "..", "..", "lib"))
    with patch("subprocess.run", return_value=MagicMock(returncode=0)):
        with patch("relok8.parse_rpath", return_value=[str(tmp_path / "old" / "lib")]):
            assert patch_rpath(path, new_rpath) == new_rpath


def test_main_linux(tmp_path):
    proj = LinuxProject(tmp_path)
    simple = proj.add_simple_elf("simple.so", "foo", "bar")
    simple2 = proj.add_simple_elf("simple2.so", "foo", "bar", "bop")
    proj.add_file("not-an-so", "fake", "foo", "bar", "bop")

    args = Namespace(
        root=proj.root_dir,
        libs=proj.libs_dir,
        log_level="info",
        rpath_only=True,
    )
    calls = [
        call(str(simple), str(args.libs), args.rpath_only, str(args.root)),
        call(str(simple2), str(args.libs), args.rpath_only, str(args.root)),
    ]
    with proj:
        with patch("relok8.parser.parse_args", return_value=args):
                with patch("relok8.handle_elf", return_value=args) as elf_mock:
                    main()
                    assert elf_mock.call_count == 2
                    elf_mock.assert_has_calls(calls, any_order=True)


def test_handle_elf(tmp_path):
    proj = LinuxProject(tmp_path / "proj")
    pybin = proj.add_simple_elf("python", "foo")
    libcrypt = tmp_path / "libcrypt.so.2"
    libcrypt.touch()

    ldd_ret = """
    linux-vdso.so.1 => linux-vdso.so.1 (0x0123456789)
	libcrypt.so.2 => {libcrypt} (0x0123456789)
	libm.so.6 => /usr/lib/libm.so.6 (0x0123456789)
	libc.so.6 => /usr/lib/libc.so.6 (0x0123456789)
    """.format(libcrypt=libcrypt).encode()

    with proj:
        with patch("subprocess.run", return_value=MagicMock(stdout=ldd_ret)):
            with patch("relok8.patch_rpath") as patch_rpath_mock:
                handle_elf(str(pybin), str(proj.libs_dir), False, str(proj.root_dir))
                assert not (proj.libs_dir / "linux-vdso.so.1").exists()
                assert (proj.libs_dir / "libcrypt.so.2").exists()
                assert not (proj.libs_dir / "libm.so.6").exists()
                assert not (proj.libs_dir / "libc.so.6").exists()
                assert patch_rpath_mock.call_count == 1
                patch_rpath_mock.assert_called_with(str(pybin), "$ORIGIN/../lib")


def test_handle_elf_rpath_only(tmp_path):
    proj = LinuxProject(tmp_path / "proj")
    pybin = proj.add_simple_elf("python", "foo")
    libcrypt = proj.libs_dir / "libcrypt.so.2"
    fake = tmp_path / "fake.so.2"
    fake.touch()

    ldd_ret = """
    linux-vdso.so.1 => linux-vdso.so.1 (0x0123456789)
	libcrypt.so.2 => {libcrypt} (0x0123456789)
	fake.so.2 => {fake} (0x0123456789)
	libm.so.6 => /usr/lib/libm.so.6 (0x0123456789)
	libc.so.6 => /usr/lib/libc.so.6 (0x0123456789)
    """.format(libcrypt=libcrypt, fake=fake).encode()

    with proj:
        libcrypt.touch()
        with patch("subprocess.run", return_value=MagicMock(stdout=ldd_ret)):
            with patch("relok8.patch_rpath") as patch_rpath_mock:
                handle_elf(str(pybin), str(proj.libs_dir), True, str(proj.root_dir))
                assert not (proj.libs_dir / "fake.so.2").exists()
                assert patch_rpath_mock.call_count == 1
                patch_rpath_mock.assert_called_with(str(pybin), "$ORIGIN/../lib")
