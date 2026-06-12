import argparse
import argdump

# Create a parser
parser = argparse.ArgumentParser(prog="mytool")
parser.add_argument("input")
parser.add_argument("-v", "--verbose", action="count", default=0)
parser.add_argument("--format", choices=["json", "csv"])

# Serialize
data = argdump.dump(parser)       # dict
json_str = argdump.dumps(parser)  # JSON string

# Deserialize
restored = argdump.load(data)
restored = argdump.loads(json_str)

# Use normally
args = restored.parse_args(["input.txt", "-vvv", "--format", "json"])