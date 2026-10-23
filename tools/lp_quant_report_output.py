"""Keep CPU review reports separate from every historical study artifact."""
from pathlib import Path
from lp_protocol import ROOT

DIRECTORY = ROOT / 'artifacts/gpup-quant-pr-review-20261023'


def report_output(output=None, kind='resident'):
    output = Path(output) if output is not None else DIRECTORY / (kind + '-report.json')
    # Resolve directory aliases before opening anything. Restricting the entire
    # output directory also protects historical receipts beyond report.json.
    if not output.resolve().is_relative_to(DIRECTORY.resolve()):
        raise ValueError('quantization PR reports require their separate review directory')
    # Never truncate an existing file: this also rejects hard links to a report
    # outside the directory. Each fresh report has a new explicit identity.
    if output.exists() or output.is_symlink():
        raise ValueError('quantization PR report already exists')
    return output
