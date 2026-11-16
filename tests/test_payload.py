from hfbench import payload as pl


def test_join_set_doubles_each_file_with_the_next(tmp_path):
    src, dst = tmp_path / "src", tmp_path / "dst"
    src.mkdir()
    for name, body in (("b.txt", b"BB"), ("a.txt", b"AA"), ("c.txt", b"CC")):
        (src / name).write_bytes(body)
    digest, per = pl.derive_join_set(src, dst)
    assert (dst / "a.txt").read_bytes() == b"AABB"
    assert (dst / "b.txt").read_bytes() == b"BBCC"
    assert (dst / "c.txt").read_bytes() == b"CCAA"
    assert digest == pl.sha256_set(dst)[0] and set(per) == {"a.txt", "b.txt", "c.txt"}
