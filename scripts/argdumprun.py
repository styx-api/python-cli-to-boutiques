import argdump
from .parser import _build_parser
import json


parser = _build_parser()

json_str = argdump.dumps(parser) 
# print(json_str)

with open("mriqc.json", "w") as f:
    json.dump(json.loads(json_str), f, indent=2)