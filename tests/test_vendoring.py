import subprocess

from conftest import REPO_ROOT, load_json

REGISTRY_PATH = REPO_ROOT / ".claude/skills/shepherd/registry.base.json"
REGISTRY = load_json(REGISTRY_PATH)
REGISTRY_DIR = REGISTRY_PATH.parent  # base engine paths resolve relative to here


def _engines():
    """(use name, skill-relative engine path) for every use that has an engine."""
    return [(name, spec["engine"]) for name, spec in REGISTRY["uses"].items()
            if spec.get("engine")]


def test_every_use_engine_exists():
    for name, path in _engines():
        assert (REGISTRY_DIR / path).is_file(), f"missing vendored engine for {name}: {path}"


def test_every_engine_is_vendored_in_repo():
    for name, path in _engines():
        assert path.startswith("../_vendored/"), \
            f"engine for {name} is not under _vendored/: {path}"


def test_vendored_md_has_entry_per_engine():
    text = (REPO_ROOT / "VENDORED.md").read_text()
    for name, _ in _engines():
        assert name in text, f"VENDORED.md missing entry for {name}"


def test_no_committed_skill_references_a_plugin_path():
    # No-install guard: committed skills/agents/config must not point at plugin caches.
    out = subprocess.run(
        ["git", "grep", "-nI", "--cached", "-e", "plugins/cache", "-e", ".claude/plugins",
         "--", ".claude/", ".shepherd/"],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert out.stdout == "", f"plugin-path references found:\n{out.stdout}"


def test_vendored_files_are_git_tracked():
    sample = next(path for _, path in _engines())
    repo_rel = (REGISTRY_DIR / sample).resolve().relative_to(REPO_ROOT)
    out = subprocess.run(
        ["git", "ls-files", "--error-unmatch", str(repo_rel)],
        cwd=REPO_ROOT, capture_output=True, text=True,
    )
    assert out.returncode == 0, "vendored files must be committed, not gitignored"
