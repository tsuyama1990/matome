from pathlib import Path
from unittest.mock import MagicMock

import pytest
import typer

from domain_models.config import ProcessingConfig
from matome.cli import _validate_output_dir
from matome.engines.interactive_raptor import InteractiveRaptorEngine


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

        # Use MonkeyPatch to simulate running context where CWD is tmp_path
        # We can't rely on pytest.raises context manager nesting logic with other CMs easily in one line in ruff's view?
        # Ruff complaint was about complex statement in with block.

        with pytest.MonkeyPatch.context() as m:
             m.setattr(Path, "cwd", lambda: tmp_path)
             with pytest.raises(typer.Exit):
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

        # Test control char removal
        dirty_chars = "Refine\x00this\x1f"
        clean = engine._sanitize_instruction(dirty_chars)
        assert clean == "Refinethis"

        # Test basic pass-through of valid chars
        valid = "Make it shorter."
        assert engine._sanitize_instruction(valid) == valid
