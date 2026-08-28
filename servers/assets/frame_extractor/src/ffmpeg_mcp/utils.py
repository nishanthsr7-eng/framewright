import os
import tempfile
import zipfile


def convert_to_seconds(time_input):
    """Convert a time to seconds.

    Accepts a number of seconds, a string 'HH:MM:SS' / 'MM:SS' / 'SS', or a tuple (HH, MM, SS).
    Raises ValueError for anything else.
    """
    if isinstance(time_input, (int, float)):
        return float(time_input)

    if isinstance(time_input, str):
        parts = time_input.split(":")
        parts = [float(p) for p in parts]
        if len(parts) == 3:
            hours, minutes, seconds = parts
        elif len(parts) == 2:
            hours = 0
            minutes, seconds = parts
        elif len(parts) == 1:
            hours = 0
            minutes = 0
            seconds = parts[0]
        else:
            raise ValueError(f"Unrecognized time string format: {time_input}")
        return hours * 3600 + minutes * 60 + seconds

    if isinstance(time_input, tuple):
        if len(time_input) == 3:
            hours, minutes, seconds = time_input
        elif len(time_input) == 2:
            hours = 0
            minutes, seconds = time_input
        elif len(time_input) == 1:
            hours = 0
            minutes = 0
            seconds = time_input[0]
        else:
            raise ValueError(f"Unrecognized time tuple format: {time_input}")
        return hours * 3600 + minutes * 60 + seconds

    raise ValueError(f"Unrecognized time input type: {type(time_input)}")


def create_temp_file() -> str:
    """Create an empty temp file and return its path (the caller deletes it)."""
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    temp_file_path = temp_file.name
    # Close it so other processes can open it.
    temp_file.close()
    return temp_file_path


def unzip_to_current_directory(zip_file_path):
    current_directory = os.getcwd()

    with zipfile.ZipFile(zip_file_path, "r") as zip_ref:
        zip_ref.extractall(current_directory)
