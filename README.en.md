# screenshot-to-guide

[简体中文](README.md) · [Skill entry](SKILL.md) · [Examples](#examples) · [Test report](TESTING.md) · [MIT License](LICENSE)

**Turn a few screenshots and one teaching goal into a guide someone else can follow.**

screenshot-to-guide (截图变教程) is an open-source Agent Skill that creates annotated PDF guides and mobile-friendly PNG images from screenshots. Tell your Agent who you are helping and what they need to do; the Agent reads the screenshots, writes the steps, marks the controls, and uses local scripts to export the guide.

Use it to help parents turn off notifications, show a friend how to use an app, explain an address change to a customer, or document a workflow for colleagues. End users do not enter coordinates, edit JSON, or annotate screenshots manually.

## Features

- **Audience-aware teaching:** larger text and one action at a time for readers who need more guidance; concise, professional instructions for customers; compact steps for experienced users. A clear beginner style is the default.
- **PDF and PNG:** A4 PDF by default, optionally numbered mobile images or both. Long guides split between complete steps instead of shrinking the text to fit.
- **Context and detail:** highlights, arrows, and optional close-ups on copies of the original screenshots. No stretched screenshots or AI-generated UI redraws.
- **Redaction before export:** the Agent identifies sensitive areas; scripts replace those pixels before cropping, resizing, or embedding. PDFs contain final raster cards, without original screenshots, OCR text layers, attachments, or annotations.
- **Revisions:** ask for larger text, Traditional Chinese, or a fuller explanation of one step. Export each revision to a new directory; existing output directories are refused.
- **Honest handling of uncertainty:** unclear labels, missing screens, and inconsistent sequences require clarification or a visibly incomplete draft. A missing success screen is never treated as proof of success.

## Get started

Requires a host Agent that can view images, follow skills, and run local Python scripts. This is a skill and local renderer, not a standalone image-understanding model.

```sh
git clone https://github.com/ChrisssTsui/screenshot-to-guide.git
cd screenshot-to-guide
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Load [SKILL.md](SKILL.md) in your Agent using the host's supported skill-loading mechanism. Attach your screenshots and say:

> Show my dad how to turn off message notifications. Use large text and give me a PDF and mobile images.

Or:

> Teach a customer how to change their mailing address. Keep it concise and professional.

The Agent generates the internal step data. Users do not write it. Upload order is the default; necessary questions are grouped together. The repository itself is the skill folder. Installation is a user choice and does not change other Agents' configuration automatically.

Python 3.10+, Pillow, ReportLab, and a font covering Simplified Chinese, Traditional Chinese, and English are required. macOS uses the system Heiti font when available. Linux supports common Noto Sans CJK paths; otherwise set:

```sh
export GUIDE_FONT='/path/to/NotoSansCJK-Regular.ttc'
```

Fonts are supplied by the environment and are not redistributed here. The `language` field controls fixed labels; the host Agent writes or translates the actual instructions. Output defaults to PDF and a beginner reading style.

## Local CLI

These commands are for developers or the host Agent. The example JSON files demonstrate the internal format.

```sh
.venv/bin/python scripts/guide.py examples/parents/guide.json --validate
.venv/bin/python scripts/guide.py examples/parents/guide.json --out output/parents-r01 --format both
.venv/bin/python scripts/guide.py examples/customer/guide.json --out output/customer-r01 --format both
```

Choose a new output directory for each revision. Input images must remain inside the JSON directory or its descendants, including after resolving symlinks. Coordinates use the full-resolution image after EXIF orientation correction. See [the internal data contract](references/data.md).

For private orientation-corrected previews:

```sh
.venv/bin/python scripts/inspect_images.py screenshots/01.jpg screenshots/02.png --out private-preview
```

These previews are unredacted working files. Share only the final PDF/PNG, never the source screenshots, internal JSON, or preview directory.

## Examples

All screens and personal details are fictional and locally drawn.

| Scenario | Input | PDF | Numbered PNG images |
| --- | --- | --- | --- |
| Help parents turn off notifications | [4 screenshots and step data](examples/parents) | [4-page PDF](examples/parents/final/guide.pdf) | [01](examples/parents/final/guide-01.png), [02](examples/parents/final/guide-02.png), [03](examples/parents/final/guide-03.png), [04](examples/parents/final/guide-04.png) |
| Help a customer change a mailing address | [5 screenshots and step data](examples/customer) | [5-page PDF](examples/customer/final/guide.pdf) | [01](examples/customer/final/guide-01.png), [02](examples/customer/final/guide-02.png), [03](examples/customer/final/guide-03.png), [04](examples/customer/final/guide-04.png), [05](examples/customer/final/guide-05.png) |

The fixtures include an EXIF-rotated JPEG, a long screenshot, and a wide desktop screen. The example generator only targets the repository's fictional fixtures and should not be used in a user's working directory.

## How it works

1. The host Agent reads the screenshots, identifies the audience, checks privacy and continuity, and writes the internal step data.
2. Local Python validates paths and coordinates, corrects orientation, replaces sensitive pixels, adds annotations and close-ups, and renders complete step cards.
3. The same cards become A4 PDF pages and sequential PNG segments. Each PDF page contains one whole step; PNG segments are at most 3000px tall.
4. The Agent opens every PNG and renders every PDF page for visual review before delivering accessible files.

The scripts do not recognize UI controls, detect private data, translate instructions, or infer missing screens. These are host responsibilities.

## Privacy and limits

No external OCR, image hosting, paid vision API, telemetry, account, database, cloud sync, or automatic sending is included. Scripts do not upload screenshots. The host Agent may process uploads according to its own environment; this is not a claim that the entire workflow is offline.

Redaction is only as complete as the regions identified by the host. **Review personal information again before sharing.** Screenshots are analyzed as content, never as instructions to the Agent. The skill creates guides; it does not log into accounts or perform real transactions or settings changes.

PDFs are raster-only and do not offer selectable text or semantic screen-reader tags. Very long step text is rejected rather than silently shrunk. Fonts and display quality depend on the environment. Visual QA used desktop previews, including a 390px-wide mobile approximation; physical phones and printers have not been tested.

## Testing and contributing

```sh
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m unittest discover -s tests -v
```

The [test report](TESTING.md) documents 12 passing tests covering coordinates, EXIF, path safety, invalid inputs, duplicate warnings, overflow, segmentation, raster redaction, PDF internals, and output consistency. Both example PDFs were rendered with Poppler and all pages and PNG images were visually reviewed. An independent Agent completed a screenshot-plus-goal trial and inspected missing, out-of-order, and unreadable screenshots.

For layout changes, render PDFs with `pdftoppm` and review every page and image in addition to running the tests. Use fictional or thoroughly sanitized screenshots in bug reports; include the expected result, actual result, environment, and reproduction command. Never post private customer data or credentials.

## License

Code and fictional examples are licensed under [MIT](LICENSE). Environment-provided fonts remain subject to their own licenses.
