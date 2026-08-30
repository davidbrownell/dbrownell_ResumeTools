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

The generated html names what each value is rather than how it is displayed, and references no stylesheet other than the one provided. Layout, icons, fonts, and the resources that provide them are all decided by that stylesheet, so the same content can be presented in completely different ways without the generator being involved.

### How to use `dbrownell_ResumeTools`
Generate html from resume content and a stylesheet:

```shell
uv run dbrownell_ResumeTools <content_filename> <style_filename> [<output_directory>]
```

| Argument | Description |
| --- | --- |
| `<content_filename>` | json or yaml content that conforms to the [JSON Resume](https://jsonresume.org/) schema. |
| `<style_filename>` | A `.css` or `.less` stylesheet, provided as a filename or as an `http`/`https` url that references one; less content is compiled to css. |
| `<output_directory>` | Directory populated with the generated `index.html` and the stylesheet that it references; a temporary directory that is removed once the process exits is used when this argument is not provided. |

[Sample content](https://github.com/davidbrownell/dbrownell_ResumeTools/tree/main/src/dbrownell_ResumeTools/samples) and [themes](https://github.com/davidbrownell/dbrownell_ResumeTools/tree/main/src/dbrownell_ResumeTools/themes) are included with the package; this command generates and displays the sample resume when it is run from the directory that contains them:

```shell
uv run dbrownell_ResumeTools resume.json standard.less --serve --browser
```

`--serve` serves the generated content over http and `--browser` displays it in a browser, which is served until that browser is closed. Run `uv run dbrownell_ResumeTools --help` for all available options.

A stylesheet may also be referenced by url, which applies a stylesheet that is not installed locally; the content that is downloaded is written to the output directory alongside the html that references it:

```shell
uv run dbrownell_ResumeTools resume.json https://raw.githubusercontent.com/davidbrownell/dbrownell_ResumeTools/main/src/dbrownell_ResumeTools/themes/standard.less --serve --browser
```

#### Creating a pdf
Print the displayed content to a pdf from the browser itself (`Ctrl+P` / `Cmd+P`, then "Save as PDF"). The bundled stylesheets define `@media print` rules that compact the content for a printed page, so no separate command is involved. The pdf produced by each bundled stylesheet is linked in [the table below](#writing-a-stylesheet).

### Writing a stylesheet
The generated html assigns a class to every value that names what the value is: the section that contains it (`work`, `education`, `skills`, ...), its role within that section (`section-header`, `entry`, `entry-body`, `detail`, ...), and the schema field that produced it (`position`, `startDate`, `gpa`, `keyword`, ...). Icons are empty `icon` elements that a stylesheet fills in through `::before`. That contract is documented in full at the top of [standard.less](https://github.com/davidbrownell/dbrownell_ResumeTools/blob/main/src/dbrownell_ResumeTools/themes/standard.less), and a stylesheet is free to lay those classes out however it likes.

Six stylesheets are bundled to demonstrate the range. All of them are applied to the same `resume.json` and to the same generated html:

| Stylesheet | Presentation | Sample |
| --- | --- | --- |
| `standard.less` (and the `standard.css` it compiles to) | A single column with a serif display face, a tinted title, and keywords as badges. | [pdf](https://github.com/davidbrownell/dbrownell_ResumeTools/blob/main/docs/sample_resume_standard.pdf) |
| `brutalist.less` | Heavy black rules, hard edges, and offset block shadows in one safety-yellow accent, with numbered sections and chips in place of icons. | [pdf](https://github.com/davidbrownell/dbrownell_ResumeTools/blob/main/docs/sample_resume_brutalist.pdf) |
| `minimal.less` | Monochrome and monospaced, set in a nerd font whose glyphs replace the labels that would otherwise introduce a value. | [pdf](https://github.com/davidbrownell/dbrownell_ResumeTools/blob/main/docs/sample_resume_minimal.pdf) |
| `modernist.less` | A geometric sans face, a tinted block attached to the margin by a heavy bar, entries as cards, and no icon anywhere. | [pdf](https://github.com/davidbrownell/dbrownell_ResumeTools/blob/main/docs/sample_resume_modernist.pdf) |
| `sidebar.less` | Two columns with a dark sidebar, icons on the profiles alone, right-aligned dates, and keywords as a run of text. | [pdf](https://github.com/davidbrownell/dbrownell_ResumeTools/blob/main/docs/sample_resume_sidebar.pdf) |
| `timeline.less` | A full-width banner, dated entries hung off a vertical rail, and keywords as tags. | [pdf](https://github.com/davidbrownell/dbrownell_ResumeTools/blob/main/docs/sample_resume_timeline.pdf) |

| | |
| :---: | :---: |
| <img src="https://raw.githubusercontent.com/davidbrownell/dbrownell_ResumeTools/main/docs/sample_resume_standard.png" alt="Sample resume generated from resume.json and standard.less" width="380" /> | <img src="https://raw.githubusercontent.com/davidbrownell/dbrownell_ResumeTools/main/docs/sample_resume_brutalist.png" alt="Sample resume generated from resume.json and brutalist.less" width="380" /> |
| `standard.less` | `brutalist.less` |
| <img src="https://raw.githubusercontent.com/davidbrownell/dbrownell_ResumeTools/main/docs/sample_resume_minimal.png" alt="Sample resume generated from resume.json and minimal.less" width="380" /> | <img src="https://raw.githubusercontent.com/davidbrownell/dbrownell_ResumeTools/main/docs/sample_resume_modernist.png" alt="Sample resume generated from resume.json and modernist.less" width="380" /> |
| `minimal.less` | `modernist.less` |
| <img src="https://raw.githubusercontent.com/davidbrownell/dbrownell_ResumeTools/main/docs/sample_resume_sidebar.png" alt="Sample resume generated from resume.json and sidebar.less" width="380" /> | <img src="https://raw.githubusercontent.com/davidbrownell/dbrownell_ResumeTools/main/docs/sample_resume_timeline.png" alt="Sample resume generated from resume.json and timeline.less" width="380" /> |
| `sidebar.less` | `timeline.less` |

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
