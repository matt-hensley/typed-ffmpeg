import keyword
import pathlib
from math import isnan
from pathlib import Path

import jinja2

from ffmpeg.common.schema import (
    FFMpegFilter,
    FFMpegFilterOption,
    FFMpegFilterOptionType,
    FFMpegOption,
    FFMpegOptionType,
)

SUPPORTED_LANGUAGES = ["python", "typescript"]

# TypeScript reserved words (a subset, extend as needed)
TS_RESERVED_WORDS = {
    "break", "case", "catch", "class", "const", "constructor", "debugger", "default", "delete",
    "do", "else", "enum", "export", "extends", "false", "finally", "for", "function", "if",
    "import", "in", "instanceof", "new", "null", "return", "super", "switch", "this", "throw",
    "true", "try", "typeof", "var", "void", "while", "with", "yield",
    "implements", "interface", "let", "package", "private", "protected", "public", "static",
    # Strict mode reserved words
    "eval", "arguments",
    # Common types/interfaces that might conflict
    "string", "number", "boolean", "Date", "Array", "Object", "Promise", "Error",
}


def _to_camel_case(snake_str: str) -> str:
    components = snake_str.split("_")
    # We capitalize the first letter of each component except the first one
    # with the 'title' method and join them together.
    if not components:
        return ""
    return components[0] + "".join(x.title() for x in components[1:])

def _to_pascal_case(snake_str: str) -> str:
    components = snake_str.split("_")
    if not components:
        return ""
    return "".join(x.title() for x in components)


def filter_option_typing(option: FFMpegFilterOption) -> str: # Python specific
    """
    The typing of the filter option

    Args:
        option: The filter option

    Returns:
        The typing of the filter option
    """
    base_type = None
    if option.type == FFMpegFilterOptionType.boolean:
        base_type = "Boolean"
    elif option.type == FFMpegFilterOptionType.duration:
        base_type = "Duration"
    elif option.type == FFMpegFilterOptionType.color:
        base_type = "Color"
    elif option.type == FFMpegFilterOptionType.flags:
        base_type = "Flags"
    elif option.type == FFMpegFilterOptionType.dictionary:
        base_type = "Dictionary"
    elif option.type == FFMpegFilterOptionType.pix_fmt:
        base_type = "Pix_fmt"
    elif option.type == FFMpegFilterOptionType.int:
        base_type = "Int"
    elif option.type == FFMpegFilterOptionType.int64:
        base_type = "Int64"
    elif option.type == FFMpegFilterOptionType.double:
        base_type = "Double"
    elif option.type == FFMpegFilterOptionType.float:
        base_type = "Float"
    elif option.type == FFMpegFilterOptionType.string:
        base_type = "String"
    elif option.type == FFMpegFilterOptionType.video_rate:
        base_type = "Video_rate"
    elif option.type == FFMpegFilterOptionType.image_size:
        base_type = "Image_size"
    elif option.type == FFMpegFilterOptionType.rational:
        base_type = "Rational"
    elif option.type == FFMpegFilterOptionType.sample_fmt:
        base_type = "Sample_fmt"
    elif option.type == FFMpegFilterOptionType.binary:
        base_type = "Binary"

    assert base_type, f"{option.type} not fit"
    if not option.choices:
        return base_type

    values = ",".join(f'"{i.name}"' for i in option.choices)
    return base_type + f"| Literal[{values}]"


def stream_name_safe(string: str) -> str:
    """
    Convert stream name to safe name

    Args:
        string: The stream name

    Returns:
        The stream name safe
    """
    opt_name = option_name_safe(string)
    if not opt_name.startswith("_"):
        return "_" + opt_name
    return opt_name


def stream_name_safe(string: str) -> str: # Python specific
    """
    Convert stream name to safe name for Python
    """
    opt_name = python_option_name_safe(string) # Use python_option_name_safe
    if not opt_name.startswith("_"):
        return "_" + opt_name
    return opt_name


def python_option_name_safe(string: str) -> str:
    """
    Convert option name to safe name for Python.
    Original option_name_safe, renamed for clarity.

    Args:
        string: The option name

    Returns:
        The option name safe
    """
    if string in keyword.kwlist:
        return "_" + string
    if string[0].isdigit(): # Check if first character is a digit
        return "_" + string
    if "-" in string:
        return string.replace("-", "_")
    return string


def ts_option_name_safe(name: str, is_property: bool = True) -> str:
    """
    Convert option name to a safe name for TypeScript.
    Handles keywords and converts to camelCase for properties or PascalCase for types/enums.
    """
    name = name.replace("-", "_") # Common first step

    if is_property:
        name = _to_camel_case(name)
    else: # For types, enums
        name = _to_pascal_case(name)

    if not name: # Handle empty string case after processing
        return "_" 

    if name in TS_RESERVED_WORDS:
        return name + "_" # Append underscore if it's a reserved word
    if name[0].isdigit(): 
        return "_" + name
    return name


def ts_filter_option_typing(option: FFMpegFilterOption) -> str:
    """
    The typing of the filter option for TypeScript.
    """
    base_type = "any"  # Default to any if no specific type matches

    if option.type == FFMpegFilterOptionType.boolean:
        base_type = "boolean"
    elif option.type in [
        FFMpegFilterOptionType.duration, # string like "1s", "1ms", "1us" or number of seconds
        FFMpegFilterOptionType.string,
        FFMpegFilterOptionType.color, # Represented as string e.g. "red", "0xRRGGBB"
        FFMpegFilterOptionType.pix_fmt, # Pixel format string
        FFMpegFilterOptionType.video_rate, # String like "25/1" or "ntsc"
        FFMpegFilterOptionType.image_size, # String like "hd720" or "1920x1080"
        FFMpegFilterOptionType.sample_fmt, # Sample format string
    ]:
        base_type = "string"
    elif option.type == FFMpegFilterOptionType.binary: # Could be string (hex) or Uint8Array
        base_type = "string | Uint8Array"
    elif option.type in [
        FFMpegFilterOptionType.int,
        FFMpegFilterOptionType.int64, # TypeScript 'number' can handle large integers
        FFMpegFilterOptionType.double,
        FFMpegFilterOptionType.float,
    ]:
        base_type = "number"
    elif option.type == FFMpegFilterOptionType.rational: # Could be string "num/den" or a specific interface {num: number, den: number}
        base_type = "string | { num: number; den: number }"
    elif option.type == FFMpegFilterOptionType.flags:
        if option.choices: # If choices are defined, use them for a union type
             choice_values = " | ".join(f'"{ts_option_name_safe(i.name, is_property=False)}"' for i in option.choices)
             # For flags, it's common to allow multiple, so an array might be more appropriate,
             # or a string with '+' separated values. For now, a union of single flags for simplicity.
             return choice_values # e.g. "Flag1" | "Flag2"
        else: # No choices, general flags represented as string
            base_type = "string" # e.g., "flag1+flag2"
    elif option.type == FFMpegFilterOptionType.dictionary:
        base_type = "Record<string, string>" # or Record<string, any>

    if not option.choices:
        return base_type

    # Create a TypeScript union type from choices for non-flag types
    choice_values = " | ".join(f'"{ts_option_name_safe(i.name, is_property=False)}"' for i in option.choices)
    
    # If the base_type was already specific (e.g. "number") and there are choices,
    # the choices should conform to that type.
    # Example: an int option with choices 0, 1, 2 would be `0 | 1 | 2` (which is compatible with number).
    # If choices are string representations of numbers, then `string` or `number` union is fine.
    # For now, if base_type is "number" and choices are present, assume choices are numeric literals.
    if base_type == "number" and all(c.name.isdigit() or (c.name.startswith('-') and c.name[1:].isdigit()) for c in option.choices):
        return " | ".join(c.name for c in option.choices)

    return f"{choice_values}"


def ts_option_typing(option: FFMpegOption) -> str:
    """
    The typing of the option for TypeScript.
    """
    if option.type == FFMpegOptionType.OPT_TYPE_FUNC:
        return "() => any" # Representing a function type
    elif option.type == FFMpegOptionType.OPT_TYPE_BOOL:
        return "boolean"
    elif option.type == FFMpegOptionType.OPT_TYPE_STRING:
        return "string"
    elif option.type in [FFMpegOptionType.OPT_TYPE_INT, FFMpegOptionType.OPT_TYPE_INT64]:
        return "number"
    elif option.type in [FFMpegOptionType.OPT_TYPE_FLOAT, FFMpegOptionType.OPT_TYPE_DOUBLE]:
        return "number"
    elif option.type == FFMpegOptionType.OPT_TYPE_TIME: # Duration can be number (seconds) or string
        return "number | string"
    return "any" # Default fallback


def ts_default_value_str(option: FFMpegFilterOption, owner_filter: FFMpegFilter) -> str | None:
    """
    Generates the TypeScript string representation of a default value.
    Returns None if there's no suitable default for direct assignment.
    """
    if option.name in owner_filter.pre_dict: # Handle 'Auto' values from pre_dict
        val = owner_filter.pre_dict[option.name]
        # Represent Auto(val) as a comment, actual value might be complex or runtime-dependent
        return f"/* Auto: {repr(val)} */ undefined" # Or some other placeholder indicating 'auto'

    default_val = option.default
    if default_val is None or (isinstance(default_val, float) and isnan(default_val)):
        if option.type == FFMpegFilterOptionType.string and str(option.default) == "nan": # Handle string "nan"
             return '"nan"'
        return None


    ts_type_str = ts_filter_option_typing(option) # Get the TS type string (e.g. "string", "number", "boolean")

    if ts_type_str == "string" or '"' in ts_type_str: # If it's a string type or a string literal union
        if isinstance(default_val, str):
            escaped_val = default_val.replace("\\", "\\\\").replace("`", "\\`").replace('"', '\\"')
            return f'"{escaped_val}"'
        return f'"{str(default_val)}"'

    if ts_type_str == "number" or (option.choices and all(c.name.isdigit() for c in option.choices)):
        if isinstance(default_val, (int, float)):
            return str(default_val)
        try: # Try to convert if it's a string representation of a number
            return str(float(default_val))
        except ValueError:
            return None 

    if ts_type_str == "boolean":
        if isinstance(default_val, bool):
            return "true" if default_val else "false"
        if str(default_val).lower() in ["true", "1", "yes"]:
            return "true"
        if str(default_val).lower() in ["false", "0", "no"]:
            return "false"
        return None

    # For union types derived from choices, if default_val matches one of the choices
    if option.choices:
        for choice in option.choices:
            # Compare default_val with choice.name, choice.name is string.
            if str(default_val) == choice.name:
                # ts_option_name_safe(choice.name, is_property=False) gives PascalCase for choices
                # but string literal unions are quoted strings.
                return f'"{ts_option_name_safe(choice.name, is_property=False)}"'
    
    return None # Fallback: no simple default assignment


def ts_default_typings(option: FFMpegFilterOption, owner_filter: FFMpegFilter) -> str:
    """
    The default typing of the filter option for TypeScript properties.
    e.g., `propertyName?: type; // Default: value`
    Includes JSDoc style comments.
    """
    prop_name = ts_option_name_safe(option.name)
    ts_type = ts_filter_option_typing(option)
    
    # Build JSDoc comment
    jsdoc_lines = [f"/**"]
    jsdoc_lines.append(f" * {option.description or 'No description available.'}")
    jsdoc_lines.append(f" * Type: {option.type.value}") # Raw type
    if option.choices:
        choices_str = ", ".join(ts_option_name_safe(c.name, is_property=False) for c in option.choices)
        jsdoc_lines.append(f" * Choices: {choices_str}")
    
    default_val_comment = None
    if option.name in owner_filter.pre_dict:
        default_val_comment = f"Auto: {owner_filter.pre_dict[option.name]}"
    elif option.default is not None and not (isinstance(option.default, float) and isnan(option.default)):
        default_val_comment = f"{option.default}"

    if default_val_comment:
        jsdoc_lines.append(f" * Default: {default_val_comment}")
    
    if option.min_val is not None:
        jsdoc_lines.append(f" * Min: {option.min_val}")
    if option.max_val is not None:
        jsdoc_lines.append(f" * Max: {option.max_val}")
    if option.unit:
         jsdoc_lines.append(f" * Unit: {option.unit}")

    jsdoc_lines.append(f" */")
    jsdoc = "\n  ".join(jsdoc_lines)

    # Property is optional if no default or if default is 'auto' (complex to represent)
    # FFmpeg options are generally optional in practice.
    optional_marker = "?" 
    
    # Default value for assignment in class field (not interface)
    # default_assignment_str = ts_default_value_str(option, owner_filter)
    # For interfaces, we just declare the type and optionality.
    # Default value is noted in JSDoc.
    
    return f"{jsdoc}\n  {prop_name}{optional_marker}: {ts_type};"


def ts_filter_option_typings(ffmpeg_filter: FFMpegFilter) -> str:
    """
    The typing of the filter options for TypeScript interface properties.
    """
    output = []
    if not ffmpeg_filter.options: # Handle case with no options
        return "// No options available for this filter."
        
    for option in ffmpeg_filter.options:
        output.append(ts_default_typings(option, ffmpeg_filter))
    return "\n\n  ".join(output) # Separate properties with an extra newline for readability


def ts_input_typings(ffmpeg_filter: FFMpegFilter) -> str:
    """
    The input typings of the filter for TypeScript.
    Assumes a StreamType enum or similar in TypeScript.
    """
    if ffmpeg_filter.formula_typings_input:
        return f"/* Formula: {ffmpeg_filter.formula_typings_input} */ any" # Formula needs TS translation
    
    typings = [f"StreamType.{i.type.value.upper()}" for i in ffmpeg_filter.stream_typings_input]
    if not typings:
        return "void[]" 
    return f"[{', '.join(typings)}]" # e.g. [StreamType.VIDEO, StreamType.AUDIO]


def ts_output_typings(ffmpeg_filter: FFMpegFilter) -> str:
    """
    The output typings of the filter for TypeScript.
    Assumes a StreamType enum or similar in TypeScript.
    """
    if ffmpeg_filter.formula_typings_output:
        return f"/* Formula: {ffmpeg_filter.formula_typings_output} */ any" # Formula needs TS translation

    typings = [f"StreamType.{i.type.value.upper()}" for i in ffmpeg_filter.stream_typings_output]
    if not typings:
        return "void[]"
    return f"[{', '.join(typings)}]"


def option_typing(option: FFMpegOption) -> str: # Python specific
    """
    The typing of the option

    Args:
        option: The option

    Returns:
        The typing of the option
    """
    if option.type == FFMpegOptionType.OPT_TYPE_FUNC:
        return "Func"
    elif option.type == FFMpegOptionType.OPT_TYPE_BOOL:
        return "Boolean"
    elif option.type == FFMpegOptionType.OPT_TYPE_STRING:
        return "String"
    elif option.type == FFMpegOptionType.OPT_TYPE_INT:
        return "Int"
    elif option.type == FFMpegOptionType.OPT_TYPE_INT64:
        return "Int64"
    elif option.type == FFMpegOptionType.OPT_TYPE_FLOAT:
        return "Float"
    elif option.type == FFMpegOptionType.OPT_TYPE_DOUBLE:
        return "Double"
    elif option.type == FFMpegOptionType.OPT_TYPE_TIME:
        return "Time"


def input_typings(ffmpeg_filter: FFMpegFilter) -> str:
    """
    The input typings of the filter

    Args:
        ffmpeg_filter: The filter

    Returns:
        The input typings of the filter
    """
    if ffmpeg_filter.formula_typings_input:
        return ffmpeg_filter.formula_typings_input
    return (
        "["
        + ", ".join(
            f"StreamType.{i.type.value}" for i in ffmpeg_filter.stream_typings_input
        )
        + "]"
    )


def output_typings(ffmpeg_filter: FFMpegFilter) -> str:
    """
    The output typings of the filter

    Args:
        ffmpeg_filter: The filter

    Returns:
        The output typings of the filter
    """
    if ffmpeg_filter.formula_typings_output:
        return ffmpeg_filter.formula_typings_output
    return (
        "["
        + ", ".join(
            f"StreamType.{i.type.value}" for i in ffmpeg_filter.stream_typings_output
        )
        + "]"
    )


def default_value(option: FFMpegFilterOption, f: FFMpegFilter) -> str:
    """
    The default value of the filter option

    Args:
        option: The filter option
        f: The filter

    Returns:
        The default value of the filter option
    """
    if option.name in f.pre_dict:
        return f"Auto({repr(f.pre_dict[option.name])})"
    if not isinstance(option.default, float) or not isnan(option.default):
        return f"Default({repr(option.default)})"
    return 'Default("nan")'


def default_typings(option: FFMpegFilterOption, f: FFMpegFilter) -> str:
    """
    The default typing of the filter option

    Args:
        option: The filter option
        f: The filter

    Returns:
        The default typing of the filter option
    """
    if option.choices:
        return f"{filter_option_typing(option)} | Default = {default_value(option, f)}"
    return f"{filter_option_typing(option)} = {default_value(option, f)}"


def filter_option_typings(ffmpeg_filter: FFMpegFilter) -> str:
    """
    The typing of the filter options

    Args:
        ffmpeg_filter: The filter

    Returns:
        The typing of the filter options
    """
    output = []
    for option in ffmpeg_filter.options: # Python specific filter_option_typings
        output.append(
            f"{python_option_name_safe(option.name)}: {default_typings(option, ffmpeg_filter)}" 
        )
    if output:
        return ",".join(output) + "," # Python tuple-like string
    return ""


# Note: Filters are registered within the render function based on language.

def render(
    filters: list[FFMpegFilter],
    options: list[FFMpegOption],
    outpath: pathlib.Path,
    language: str = "python",
) -> list[pathlib.Path]:
    """
    Render the filter and option documents

    Args:
        filters: The filters
        options: The options
        outpath: The output path
        language: The target language ("python" or "typescript")

    Returns:
        The rendered files
    """
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language: {language}. Supported languages are: {SUPPORTED_LANGUAGES}")

    template_folder = Path(__file__).parent / "templates" / language
    loader = jinja2.FileSystemLoader(template_folder)
    env = jinja2.Environment(
        loader=loader,
        trim_blocks=True, # Useful for Jinja templates
        lstrip_blocks=True # Useful for Jinja templates
    )

    # Register filters based on language
    if language == "typescript":
        env.filters["option_name_safe"] = ts_option_name_safe
        env.filters["filter_option_typing"] = ts_filter_option_typing # type for a single option
        env.filters["option_typing"] = ts_option_typing # type for a global option value
        env.filters["default_typings"] = ts_default_typings # single property string for interface
        env.filters["filter_option_typings"] = ts_filter_option_typings # all properties string for interface
        env.filters["input_typings"] = ts_input_typings
        env.filters["output_typings"] = ts_output_typings
        # stream_name_safe is not currently used in TS templates directly, if needed, a ts_ version would be added.
    else: # Default to Python
        env.filters["stream_name_safe"] = stream_name_safe
        env.filters["option_name_safe"] = python_option_name_safe
        env.filters["filter_option_typing"] = filter_option_typing
        env.filters["option_typing"] = option_typing
        env.filters["input_typings"] = input_typings
        env.filters["output_typings"] = output_typings
        env.filters["filter_option_typings"] = filter_option_typings # Python original (for function signatures)
        env.filters["default_typings"] = default_typings # Python original

    outpath.mkdir(exist_ok=True)
    output = []
    
    template_pattern = "**/*.ts.jinja" if language == "typescript" else "**/*.py.jinja"
    
    # Ensure templates directory exists for the language
    if not template_folder.exists() or not template_folder.is_dir():
        # This case should ideally not be reached if language validation is done properly
        # and template structures are correctly set up.
        # Consider logging a warning or raising an error.
        # For now, let it proceed, glob will just find nothing.
        pass

    for template_file in template_folder.glob(template_pattern):
        template_path = template_file.relative_to(template_folder)
        template = env.get_template(str(template_path))
        code = template.render(filters=filters, options=options)

        opath = outpath / str(template_path).replace(".jinja", "")
        opath.parent.mkdir(parents=True, exist_ok=True)

        with opath.open("w") as ofile:
            ofile.write("# NOTE: this file is auto-generated, do not modify\n")
            ofile.write(code)

        output.append(opath)

    return output
