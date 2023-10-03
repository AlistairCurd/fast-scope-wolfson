"""Acquire N frames at frame rate R and exposure time X"""

from egrabber import *
from pathlib import Path
import time


def set_output_dir(output_parent_dir='.',
                   output_dir='phantom-images'
                   ):
    """Set and create the output directory for images.
    
    Args:
        output_parent_dir (string):
            Path to the parent directory for an output directory.
        output_dir (string):
            Name of the output directory.
    """
    output_dir = Path(output_parent_dir).joinpath(output_dir)
    output_dir.mkdir()
    return output_dir

def main():
    set_output_dir()

if __name__ == '__main__':
    main()
