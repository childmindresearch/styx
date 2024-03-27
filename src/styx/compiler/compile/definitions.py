def compile_definitions() -> str:
    """Compile the definitions to Python code."""
    import styx.runners.styxdefs

    defs_file = styx.runners.styxdefs.__file__
    with open(defs_file, "r") as f:
        return f.read()
