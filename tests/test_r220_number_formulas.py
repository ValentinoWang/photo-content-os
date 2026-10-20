"""Keep the frontend numeric contract in the normal pytest quality command."""
from pathlib import Path
import shutil
import subprocess


def test_studio_number_formulas_have_positive_and_negative_proof():
    node = shutil.which('node')
    assert node, 'studio-number-formula-runtime: install Node.js to run the frontend numeric contract'
    subprocess.run([node, str(Path(__file__).with_suffix('.mjs'))], check=True, capture_output=True, text=True)
