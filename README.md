# Bulk Renamer

Bulk Renamer is a Windows desktop application for renaming multiple files in a selected folder.

## Features

- Select a folder containing files to rename.
- Filter files by file extension.
- Add a prefix and/or suffix to filenames.
- Configure sequential numbering, including the starting number and number width.
- Preview proposed filenames before renaming.
- Validate rename operations before execution.
- Display rename progress and a summary of the results.
- Avoid overwriting existing destination files.
- Keep the application responsive while rename operations run.

## Download and Run

1. Open the project's GitHub Releases page.
2. Download `bulk_renamer.exe` from the latest release.
3. Run `bulk_renamer.exe` on Windows.

No separate Python installation is required to run the packaged executable.

**Important:** Review the rename preview and validation results before confirming a rename operation. Back up important files before performing bulk renaming.

## Usage

1. Launch Bulk Renamer.
2. Select the folder containing the files you want to rename.
3. Configure the file-extension filter and filename options.
4. Review the proposed filenames in the preview.
5. Validate the rename plan and address any reported errors.
6. Confirm the operation to rename the files.
7. Review the progress and final results.

## Run from Source

Requirements:
- Python
- Tkinter, which is included with many standard Python installations

Clone or download the source code, then open a terminal in the project directory.

Run the application:

```bash
python app.py
```

## Run the Tests

The project includes unit tests for file discovery, filename generation, rename-plan construction, validation, and execution.

Run the tests with:

```bash
python -m unittest -v test
```

## Build the Windows Executable

Install PyInstaller:

```bash
python -m pip install pyinstaller
```

Build the executable:

```bash
python -m PyInstaller --onefile --windowed --name bulk_renamer app.py
```

After a successful build, the executable will be available at:

```text
dist/bulk_renamer.exe
```

## Project Files

- `app.py` — application entry point.
- `gui.py` — graphical user interface.
- `core.py` — file discovery, filename generation, validation, and rename operations.
- `test.py` — automated unit tests.

### Windows SmartScreen Warning

When launching `bulk_renamer.exe`, Windows may display a Microsoft Defender SmartScreen warning because the application is new and does not have an established reputation or a code-signing certificate.

This warning does not necessarily mean the application is unsafe. For your security, download the executable only from the official [GitHub Releases](https://github.com/yoelpranatawork/bulk_renamer/releases) page and review the source code if you wish to inspect how the application works.

## Disclaimer

Bulk Renamer is provided **"AS IS" and without warranties of any kind**, whether express or implied.

The author makes no guarantees regarding future updates, new features, bug fixes, maintenance, or ongoing support. The project may be changed, discontinued, or left unmaintained at any time.

**Use this software at your own risk.** Although the application provides preview and validation features, the author does not guarantee that every rename operation will produce the intended result. Users are responsible for reviewing the proposed changes, verifying the selected files and destination filenames, and ensuring that important files are backed up before proceeding.

To the maximum extent permitted by applicable law, the author shall not be held liable for any loss or damage arising from the use of, or inability to use, this software, including accidentally renamed files, data loss, or other unintended consequences.

By using Bulk Renamer, you acknowledge that you are responsible for your own file operations and for assessing whether this software is suitable for your needs.

## License

Bulk Renamer is licensed under the [PolyForm Noncommercial License 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0).

You may use, modify, and redistribute the software for noncommercial purposes, provided you comply with the license terms and preserve the required notices.

Commercial use or distribution is not permitted under this license. Please contact the author to request separate permission for commercial use.

The license explicitly permits noncommercial use by qualifying charitable organizations, educational institutions, public research organizations, public safety or health organizations, environmental protection organizations, and government institutions, regardless of their funding sources.

See the `LICENSE` file for the complete terms.
