import os
from pathlib import Path
from tempfile import TemporaryDirectory
import pytest

from ..cli import generate


@pytest.mark.parametrize(
    "language, expected_extension",
    [
        ("python", ".py"),
        ("typescript", ".ts"),
    ],
)
def test_generate_cli(language: str, expected_extension: str) -> None:
    with TemporaryDirectory() as temp_dir_name:
        outpath = Path(temp_dir_name)
        
        # Call the CLI's generate function with the specified language
        # Assuming the CLI's `generate` function is updated to accept a language parameter
        # or that we are testing the effect of setting it via a (mocked) CLI argument.
        # For now, let's assume `cli.generate` can be directly called with a language param
        # if it were refactored slightly, or we test the full CLI invocation.
        # The current `cli.generate` takes `language` as a Typer Option.
        # To test this directly, we pass it as a keyword argument.
        generate(outpath=outpath, rebuild=True, language=language)

        # Check if files with the expected extension are created
        # We expect at least filters.py/ts and sources.py/ts
        # The exact names depend on the templates being rendered.
        # From test_gen.py, we expect 'filters' and 'sources' named files.
        
        generated_files = list(outpath.glob(f"**/*{expected_extension}"))
        assert len(generated_files) > 0, f"No {expected_extension} files generated for {language}"

        # Verify specific key files
        expected_filters_file = outpath / f"filters{expected_extension}"
        expected_sources_file = outpath / f"sources{expected_extension}"
        
        assert expected_filters_file.exists(), f"{expected_filters_file} not generated for {language}"
        assert expected_sources_file.exists(), f"{expected_sources_file} not generated for {language}"

        # Optionally, could do a very basic content check, e.g., not empty
        assert expected_filters_file.read_text().strip() != "", f"{expected_filters_file} is empty for {language}"
        assert expected_sources_file.read_text().strip() != "", f"{expected_sources_file} is empty for {language}"


def test_generate_cli_default_python() -> None:
    # Test the default behavior (should be Python)
    with TemporaryDirectory() as temp_dir_name:
        outpath = Path(temp_dir_name)
        generate(outpath=outpath, rebuild=True) # No language specified

        generated_files = list(outpath.glob("**/*.py"))
        assert len(generated_files) > 0, "No .py files generated for default language (python)"

        expected_filters_file = outpath / "filters.py"
        expected_sources_file = outpath / "sources.py"
        assert expected_filters_file.exists(), "filters.py not generated for default language"
        assert expected_sources_file.exists(), "sources.py not generated for default language"
