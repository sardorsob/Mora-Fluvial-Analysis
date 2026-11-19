import os
import sys


def set_workdir(py_file=None):
    """Set the process working directory for a legacy script with relative paths.

    Pass a script filename relative to this module's directory. With no
    filename, use the parent of this module's directory. If the new directory
    differs, also add this module's directory to the import path.
    """
    # A caller can set the directory directly before reading relative paths:
    # os.chdir(os.path.dirname(os.path.abspath(getData.__file__)))

    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        # If evaluated without __file__, resolve the path from the working directory.
        script_dir = os.getcwd()

    if py_file:
        py_path = os.path.join(script_dir, py_file)
    else:
        py_path = script_dir

    os.chdir(os.path.dirname(os.path.abspath(py_path)))

    if script_dir != os.getcwd():
        sys.path.append(script_dir)
    #print(f"Current working directory set to: {os.getcwd()}")

# Example call
#set_workdir('filename.py')
