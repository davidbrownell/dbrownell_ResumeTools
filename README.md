**Project:**
[![License](https://img.shields.io/github/license/davidbrownell/dbrownell_ResumeTools?color=dark-green)](https://github.com/davidbrownell/dbrownell_ResumeTools/blob/master/LICENSE)

**Package:**
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/dbrownell_ResumeTools?color=dark-green)](https://pypi.org/project/dbrownell_ResumeTools/)
[![PyPI - Version](https://img.shields.io/pypi/v/dbrownell_ResumeTools?color=dark-green)](https://pypi.org/project/dbrownell_ResumeTools/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/dbrownell_ResumeTools)](https://pypistats.org/packages/dbrownell-resumetools)

**Development:**
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)
[![pytest](https://img.shields.io/badge/pytest-enabled-brightgreen)](https://docs.pytest.org/)
[![CI](https://github.com/davidbrownell/dbrownell_ResumeTools/actions/workflows/CICD.yml/badge.svg)](https://github.com/davidbrownell/dbrownell_ResumeTools/actions/workflows/CICD.yml)
[![Code Coverage](https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/davidbrownell/f15146b1b8fdc0a5d45ac0eb786a84f7/raw/dbrownell_ResumeTools_code_coverage.json)](https://github.com/davidbrownell/dbrownell_ResumeTools/actions)
[![GitHub commit activity](https://img.shields.io/github/commit-activity/y/davidbrownell/dbrownell_ResumeTools?color=dark-green)](https://github.com/davidbrownell/dbrownell_ResumeTools/commits/main/)

<!-- Content above this delimiter will be copied to the generated README.md file. DO NOT REMOVE THIS COMMENT, as it will cause regeneration to fail. -->

## Contents
- [Overview](#overview)
- [Installation](#installation)
- [Development](#development)
- [Additional Information](#additional-information)
- [License](#license)

## Overview
`dbrownell_ResumeTools` separates a resume's content from its presentation.

Content is written once as [JSON Resume](https://jsonresume.org/) data (json or yaml). Presentation is a [css](https://developer.mozilla.org/en-US/docs/Web/CSS) or [less](https://lesscss.org/) stylesheet applied to the html generated from that content. Updating a resume is then a matter of editing data rather than editing a document, and restyling one is a matter of changing a stylesheet rather than reformatting every entry by hand.

Text values within the content may be written as [markdown](https://commonmark.org/), so emphasis, links, and lists live alongside the data that they decorate.

### How to use `dbrownell_ResumeTools`
Generate html from resume content and a stylesheet:

```shell
uv run dbrownell_ResumeTools <content_filename> <style_filename> <output_directory>
```

| Argument | Description |
| --- | --- |
| `<content_filename>` | json or yaml content that conforms to the [JSON Resume](https://jsonresume.org/) schema. |
| `<style_filename>` | A `.css` or `.less` stylesheet; less content is compiled to css. |
| `<output_directory>` | Directory populated with the generated `index.html` and the stylesheet that it references. |

[Sample content and stylesheets](https://github.com/davidbrownell/dbrownell_ResumeTools/tree/main/src/dbrownell_ResumeTools/samples) are included with the package; this command generates and displays the sample resume when it is run from that directory:

```shell
uv run dbrownell_ResumeTools resume.json standard.less ./output --serve --browser
```

`--serve` serves the generated content over http and `--browser` displays it in a browser, which is served until that browser is closed. Run `uv run dbrownell_ResumeTools --help` for all available options.

#### Creating a pdf
Print the displayed content to a pdf from the browser itself (`Ctrl+P` / `Cmd+P`, then "Save as PDF"). `standard.less` defines `@media print` rules that compact the content for a printed page, so no separate command is involved.

This is `resume.json` rendered with `standard.less`:

<img src="https://raw.githubusercontent.com/davidbrownell/dbrownell_ResumeTools/main/docs/sample_resume.png" alt="Sample resume generated from resume.json and standard.less" width="600" />

<!-- Content below this delimiter will be copied to the generated README.md file. DO NOT REMOVE THIS COMMENT, as it will cause regeneration to fail. -->

## Installation

| Installation Method | Command |
| --- | --- |
| Via [uv](https://github.com/astral-sh/uv) | `uv add dbrownell_ResumeTools` |
| Via [pip](https://pip.pypa.io/en/stable/) | `pip install dbrownell_ResumeTools` |

### Verifying Signed Artifacts
Artifacts are signed and verified using [py-minisign](https://github.com/x13a/py-minisign) and the public key in the file `./minisign_key.pub`.

To verify that an artifact is valid, visit [the latest release](https://github.com/davidbrownell/dbrownell_ResumeTools/releases/latest) and download the `.minisign` signature file that corresponds to the artifact, then run the following command, replacing `<filename>` with the name of the artifact to be verified:

```shell
uv run --with py-minisign python -c "import minisign; minisign.PublicKey.from_file('minisign_key.pub').verify_file('<filename>'); print('The file has been verified.')"
```

## Development
Please visit [Contributing](https://github.com/davidbrownell/dbrownell_ResumeTools/blob/main/CONTRIBUTING.md) and [Development](https://github.com/davidbrownell/dbrownell_ResumeTools/blob/main/DEVELOPMENT.md) for information on contributing to this project.

## Additional Information
Additional information can be found at these locations.

| Title | Document | Description |
| --- | --- | --- |
| Code of Conduct | [CODE_OF_CONDUCT.md](https://github.com/davidbrownell/dbrownell_ResumeTools/blob/main/CODE_OF_CONDUCT.md) | Information about the norms, rules, and responsibilities we adhere to when participating in this open source community. |
| Contributing | [CONTRIBUTING.md](https://github.com/davidbrownell/dbrownell_ResumeTools/blob/main/CONTRIBUTING.md) | Information about contributing to this project. |
| Development | [DEVELOPMENT.md](https://github.com/davidbrownell/dbrownell_ResumeTools/blob/main/DEVELOPMENT.md) | Information about development activities involved in making changes to this project. |
| Governance | [GOVERNANCE.md](https://github.com/davidbrownell/dbrownell_ResumeTools/blob/main/GOVERNANCE.md) | Information about how this project is governed. |
| Maintainers | [MAINTAINERS.md](https://github.com/davidbrownell/dbrownell_ResumeTools/blob/main/MAINTAINERS.md) | Information about individuals who maintain this project. |
| Security | [SECURITY.md](https://github.com/davidbrownell/dbrownell_ResumeTools/blob/main/SECURITY.md) | Information about how to privately report security issues associated with this project. |

## License
`dbrownell_ResumeTools` is licensed under the <a href="https://choosealicense.com/licenses/MIT/" target="_blank">MIT</a> license.
