"""
(Unofficial) SAD to XSuite Converter

Tests for the macOS SAD installer helpers.
"""

################################################################################
# Required Packages
################################################################################
import _install_sad_macos as installer

################################################################################
# Homebrew Helpers
################################################################################
def test_brew_install_uses_cask_flag(monkeypatch):
    """
    Cask dependencies should be installed with `brew install --cask`.
    """
    commands = []

    def fake_run(cmd):
        commands.append(cmd)

    monkeypatch.setattr(installer, "run", fake_run)

    installer.brew_install("xquartz", cask = True)

    assert commands == [["brew", "install", "--cask", "xquartz"]]

def test_ensure_brew_bin_exists_uses_executable_name(tmp_path, monkeypatch):
    """
    Homebrew binary checks should not duplicate the `bin` path component.
    """
    prefix  = tmp_path / "gcc"
    bin_dir = prefix / "bin"
    exe     = bin_dir / "gfortran"

    bin_dir.mkdir(parents = True)
    exe.touch()

    def fake_brew_prefix(formula):
        assert formula == "gcc"
        return prefix

    def fail_brew_install(formula):
        raise AssertionError(f"Unexpected install attempt for {formula}")

    monkeypatch.setattr(installer, "brew_prefix", fake_brew_prefix)
    monkeypatch.setattr(installer, "brew_install", fail_brew_install)

    assert installer.ensure_brew_bin_exists("gfortran", "gcc") == exe
