"""Check renamed distribution and console scripts without importing installed code."""
import configparser
from email.parser import BytesParser
from pathlib import Path
from zipfile import ZipFile

wheels=list(Path("dist").glob("actrift-0.8.0-*.whl"))
assert len(wheels)==1, "Expected exactly one ACTRIFT wheel"
with ZipFile(wheels[0]) as archive:
    names=archive.namelist()
    metadata=BytesParser().parsebytes(archive.read(next(n for n in names if n.endswith(".dist-info/METADATA"))))
    assert metadata["Name"]=="actrift" and metadata["Version"]=="0.8.0"
    config=configparser.ConfigParser()
    config.read_string(archive.read(next(n for n in names if n.endswith(".dist-info/entry_points.txt"))).decode())
    assert dict(config["console_scripts"])=={"actrift":"ghostdiff.cli:main","actrift-mcp":"ghostdiff.mcp_server:main"}
    assert "ghostdiff/engine.py" in names
print("ACTRIFT wheel metadata, command names and compatibility namespace verified")
