import tempfile
from pathlib import Path

from syrupy.assertion import SnapshotAssertion
from syrupy.extensions.single_file import SingleFileSnapshotExtension

import pytest

from ffmpeg.common.schema import (
    FFMpegFilter,
    FFMpegFilterChoice,
    FFMpegFilterOption,
    FFMpegFilterOptionType,
    FFMpegIOType,
    FFMpegOption,
    FFMpegOptionType,
    StreamType,
)

from ..gen import render


@pytest.mark.parametrize("language", ["python", "typescript"])
def test_render(snapshot: SnapshotAssertion, language: str) -> None:
    filters = [
        FFMpegFilter(
            id="ff_af_aap",
            name="aap_filter", # Changed to avoid conflict with potential global option 'aap'
            description="Apply an arbitrary audio filter.",
            ref="https://ffmpeg.org/ffmpeg-filters.html#aap",
            is_dynamic_input=False,
            is_dynamic_output=False,
            stream_typings_input=(
                FFMpegIOType(name="input", type=StreamType.audio),
            ),
            stream_typings_output=(
                FFMpegIOType(name="default", type=StreamType.audio),
            ),
            options=(
                FFMpegFilterOption(
                    name="level_in",
                    description="Set input level.",
                    type=FFMpegFilterOptionType.float,
                    required=False,
                    default=1.0,
                    min_val="0.015625",
                    max_val="64",
                ),
                FFMpegFilterOption(
                    name="mode",
                    description="Set mode.",
                    type=FFMpegFilterOptionType.string, # String, but with choices
                    required=False,
                    default="passthrough",
                    choices=(
                        FFMpegFilterChoice(name="passthrough", help="Pass through mode."),
                        FFMpegFilterChoice(name="measured", help="Measured mode."),
                    ),
                ),
                FFMpegFilterOption(
                    name="a_weighting",
                    description="Enable A-weighting.",
                    type=FFMpegFilterOptionType.boolean,
                    required=False,
                    default=False,
                ),
                 FFMpegFilterOption(
                    name="some_flags",
                    description="Some flags.",
                    type=FFMpegFilterOptionType.flags,
                    required=False,
                    default="flag1",
                    choices=(
                        FFMpegFilterChoice(name="flag1", help="First flag"),
                        FFMpegFilterChoice(name="flag2", help="Second flag"),
                    ),
                ),
            ),
        )
    ]
    global_options = [
        FFMpegOption(
            name="verbose",
            description="Print verbose logs.",
            type=FFMpegOptionType.OPT_TYPE_BOOL,
            is_input_option=True, # To be included in sources.xx.jinja
            is_output_option=True, # Not typically used for sources, but for completeness
            ref="https://ffmpeg.org/ffmpeg.html#Generic-options"
        ),
        FFMpegOption(
            name="sample_rate",
            description="Set audio sample rate.",
            type=FFMpegOptionType.OPT_TYPE_INT,
            is_input_option=True,
            default=44100, # Test default value handling for global options
            ref="https://ffmpeg.org/ffmpeg.html#Audio-Options"
        )
    ]

    with tempfile.TemporaryDirectory() as outpath_str:
        outpath = Path(outpath_str)
        outputs = render(filters, global_options, outpath, language=language)

        assert outputs # Ensure some files were generated

        for outfile in outputs:
            # Ensure file extension matches the language
            if language == "typescript":
                assert outfile.suffix == ".ts"
            elif language == "python":
                assert outfile.suffix == ".py"
            
            # Snapshot testing for file content
            # Use a subdirectory in snapshots for each language to keep them organized
            # Or, append language to snapshot name. For single file extension, simpler to change name.
            snapshot_name = f"{outfile.name}.{language}"
            assert snapshot(name=snapshot_name, extension_class=SingleFileSnapshotExtension) == outfile.read_bytes()


def test_render_unsupported_language() -> None:
    """
    Test that rendering with an unsupported language raises a ValueError.
    """
    with tempfile.TemporaryDirectory() as outpath_str:
        outpath = Path(outpath_str)
        with pytest.raises(ValueError) as excinfo:
            render(filters=[], options=[], outpath=outpath, language="java")
        
        assert "Unsupported language: java" in str(excinfo.value)
        assert "Supported languages are: ['python', 'typescript']" in str(excinfo.value)
