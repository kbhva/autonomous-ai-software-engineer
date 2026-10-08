import pytest

from flagship.tools.files import RepositoryFileTools


def test_repository_root_and_relative_paths(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "hello.txt").write_text("hello", encoding="utf-8")
    tools = RepositoryFileTools(repo)
    assert tools.resolve_path("hello.txt") == (repo / "hello.txt").resolve()
    assert tools.read_file("hello.txt").data["content"] == "hello"


@pytest.mark.parametrize("path", ["../outside.txt", "../../repo2/file", "", "/outside.txt"])
def test_path_traversal_rejected(tmp_path, path):
    repo = tmp_path / "repo"
    repo.mkdir()
    tools = RepositoryFileTools(repo)
    with pytest.raises(ValueError):
        tools.resolve_path(path)


def test_symlink_escape_prevented_for_read_and_write(tmp_path):
    repo, outside = tmp_path / "repo", tmp_path / "outside"
    repo.mkdir(); outside.mkdir()
    (outside / "secret.txt").write_text("secret", encoding="utf-8")
    (repo / "escape").symlink_to(outside, target_is_directory=True)
    tools = RepositoryFileTools(repo)
    assert not tools.read_file("escape/secret.txt").success
    result = tools.write_file("escape/new.txt", "bad")
    assert not result.success
    assert not (outside / "new.txt").exists()


def test_file_write_and_read(tmp_path):
    tools = RepositoryFileTools(tmp_path)
    written = tools.write_file("src/new.py", "answer = 42\n")
    assert written.success
    read = tools.read_file("src/new.py")
    assert read.success
    assert read.data["content"] == "answer = 42\n"


def test_repository_scoped_listing_skips_generated_and_symlink_dirs(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").touch()
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "secret").touch()
    external = tmp_path.parent / f"{tmp_path.name}-external"
    external.mkdir()
    (external / "leak.txt").touch()
    (tmp_path / "linked").symlink_to(external, target_is_directory=True)
    result = RepositoryFileTools(tmp_path).list_files()
    assert result.success
    assert result.data["files"] == ["src/main.py"]
