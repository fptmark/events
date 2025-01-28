from pathlib import Path
import sys

def generate_file(path_root: str, file_name: Path, lines: list[str])-> Path:
    outfile = Path(path_root) / file_name
    outfile.parent.mkdir(parents=True, exist_ok=True)
    with open(outfile, "w") as main_file:
        main_file.writelines(lines) 
    return outfile


def read_file_to_array(template: str, num=0)-> list[str]:
    """
    Reads the content of a file and returns it as an array of strings.

    Args:
        file_name (str): The name or path of the file to be read.

    Returns:
        list[str]: A list of strings, where each string is a line in the file.
    """
    try:
        file_name = f"{template}{num}.txt" if num > 0 else template
        with open(file_name, 'r', encoding='utf-8') as file:
            return file.readlines()
    except FileNotFoundError:
        print(f"Error: The file '{file_name}' was not found.")
        return []
    except IOError as e:
        print(f"Error reading the file '{file_name}': {e}")
        return []

# Example usage:
#file_content = read_file_to_array('example.txt')