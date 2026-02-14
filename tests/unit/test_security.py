import pytest
from pathlib import Path
from unittest.mock import MagicMock
from matome.cli import _validate_output_dir
from matome.engines.interactive_raptor import InteractiveRaptorEngine
from domain_models.config import ProcessingConfig
import typer

class TestSecurity:
    def test_validate_output_dir_symlink_attack(self, tmp_path: Path) -> None:
        """
        Verify that _validate_output_dir detects symlinks in the path components.
        """
        # Create a legitimate directory structure
        safe_dir = tmp_path / "safe"
        safe_dir.mkdir()

        # Create a symlink pointing outside (or inside, policy forbids any symlink)
        link_dir = safe_dir / "link"
        target_dir = tmp_path / "target"
        target_dir.mkdir()

        try:
            link_dir.symlink_to(target_dir)
        except OSError:
            pytest.skip("Symlinks not supported on this OS")

        # Mock CWD to be tmp_path for the test
        with pytest.raises(typer.Exit):
             # We must change cwd so is_relative_to works as expected in the test environment
             # But _validate_output_dir calls Path.cwd().
             # We can't easily change real CWD safely in parallel tests.
             # We should rely on passing relative paths or mocking Path.cwd

             # Assuming _validate_output_dir is imported from matome.cli
             # We'll monkeypatch Path.cwd
             with pytest.MonkeyPatch.context() as m:
                 m.setattr(Path, "cwd", lambda: tmp_path)
                 _validate_output_dir(link_dir)

    def test_validate_output_dir_parent_traversal(self, tmp_path: Path) -> None:
        """Verify traversal attempts are caught."""
        with pytest.MonkeyPatch.context() as m:
             m.setattr(Path, "cwd", lambda: tmp_path)

             # Path outside CWD
             outside = tmp_path.parent / "outside"
             with pytest.raises(typer.Exit):
                 _validate_output_dir(outside)

    def test_sanitize_instruction(self) -> None:
        """Test instruction sanitization in InteractiveRaptorEngine."""
        config = ProcessingConfig()
        engine = InteractiveRaptorEngine(
            store=MagicMock(),
            summarizer=MagicMock(),
            config=config
        )

        # Test stripping
        dirty = "  Refine this  "
        clean = engine._sanitize_instruction(dirty)
        assert clean == "Refine this"

        # Test basic pass-through of valid chars (we aren't doing heavy sanitization yet, just structure)
        valid = "Make it shorter."
        assert engine._sanitize_instruction(valid) == valid
