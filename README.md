# python-cli-to-boutiques

GitHub Action to create a [Boutiques descriptor](https://boutiques.github.io/) for a Python CLI written with `argparse` or `click`.

## Inputs

| Name | Description | Required | Default |
|------|-------------|----------|---------|
| `parser-type` | Type of parser to serialize. Either `"argparse"` or `"click"`. | yes | `argparse` |
| `parser-location` | Module path to and name of function that produces the `argparse.ArgumentParser` or `click.Command` object. E.g., `"my_package.my_module:my_func_name"`. | yes | — |
| `output-path` | Where the output Boutiques description file should be written. | yes | — |
| `open-pr` | Whether to open a pull request with the generated descriptor. A GitHub token must be provided as well. | no | `true` |
| `token` | GitHub token with write permissions for `contents` and `pull-requests`. Required if `open-pr` is true. | no | — |
| `exclude-version` | Whether to exclude the `tool-version` field in the Boutiques descriptor even if version information is available. Enabled by default because dynamic versioning schemes can cause the descriptor to be updated on every commit. | no | `true` |
| `click-prog-name` | Program name to use for the Click parser type. By default this will be the name of the decorated function. | no | — |
| `click-parent-location` | Module path to and name of function that produces the `click.Group` object that contains the `click.Command` object to serialize. E.g., `"my_package.my_module:my_func_name"`. Needed for nested commands. | no | — |
| `updates-file` | Path to a JSON file with updates to apply to the generated Boutiques descriptor. The file should contain a map of dot/bracket paths to values (e.g. `{"container-image.image": "my-container-image:tag", "container-image.type": "docker"}`). | no | — |

## Example workflows

### `argparse` CLI

```yaml
name: Create Boutiques descriptor

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  create-descriptor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
      - uses: actions/setup-python@v6
        with:
          python-version: "3.x"
      - name: Install package
        run: |
          pip install -U pip
          pip install .
      - uses: michellewang/python-cli-to-boutiques@v1
        with:
          parser-type: argparse
          parser-location: my_tool.cli:get_parser
          output-path: descriptor.json
          open-pr: true
          token: ${{ secrets.TOKEN }}
          exclude-version: true
```


### With a custom updates file

Custom values can be set to any field using `updates-file`:

```yaml
      - uses: michellewang/python-cli-to-boutiques@v1
        with:
          parser-type: argparse
          parser-location: my_tool.cli:get_parser
          output-path: descriptor.json
          open-pr: true
          token: ${{ secrets.TOKEN }}
          exclude-version: true
          updates-file: descriptor_updates.json
```

The updates file is a JSON file mapping dot/bracket paths to custom values.
It can be useful for example for adding a `"container-image"` field:

```json
{
   "container-image.image": "my-container-image:tag",
   "container-image.type": "docker",
}
```

> [!NOTE]
> If injecting the container image this way, make sure to keep the tag up-to-date before a new release.

### `click` CLI

```yaml
      - uses: michellewang/python-cli-to-boutiques@v1
        with:
          parser-type: click
          parser-location: my_tool.cli:cli
          output-path: descriptor.json
          open-pr: true
          token: ${{ secrets.TOKEN }}
          exclude-version: true
          click-prog-name: my-tool
```
