# core.py

import os

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class RenameSettings:
    prefix: str = ""
    suffix: str = ""
    numbering_enabled: bool = True
    start_number: int = 1
    number_width: int = 3
    increment: int = 1


@dataclass
class RenameEntry:
    source: Path
    destination: Path
    status: str = "pending"


@dataclass
class ValidationReport:
    is_valid: bool = False
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class OperationSummary:
    total_files: int = 0
    successful_renames: int = 0
    unchanged_files: int = 0
    skipped_files: int = 0
    refused_operations: int = 0
    failed_operations: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class FilenameResult:
    filename: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class RenamePlan:
    entries: list[RenameEntry] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def discover_files(
    folder: str | Path,
    extensions: str | list[str] | tuple[str, ...] | set[str] | None = None,
) -> list[Path]:
    """Discover files directly inside a folder.

    Args:
        folder: Folder to search. Subfolders are not searched.
        extensions: Optional extension or collection of extensions.
            Matching is case-insensitive. Extensions may include
            or omit the leading dot.

    Returns:
        A deterministically sorted list of eligible file paths.

    Raises:
        FileNotFoundError: If the folder does not exist.
        NotADirectoryError: If the path is not a directory.
        PermissionError: If the folder cannot be accessed.
        OSError: If file discovery encounters another filesystem error.
        ValueError: If an extension filter is invalid.
    """
    folder_path = Path(folder)
    if not folder_path.exists():
        raise FileNotFoundError(f"Folder does not exist: {folder_path}")
    if not folder_path.is_dir():
        raise NotADirectoryError(f"Path is not a folder: {folder_path}")
    if extensions is None:
        allowed_extensions = None
    else:
        if isinstance(extensions, str):
            extensions = [extensions]
        allowed_extensions = set()
        for extension in extensions:
            extension = extension.strip()
            if not extension:
                raise ValueError("Extensions must not be empty.")
            if not extension.startswith("."):
                extension = f".{extension}"
            if extension == ".":
                raise ValueError("An extension must contain a name.")
            allowed_extensions.add(extension.casefold())
    files = []
    try:
        with os.scandir(folder_path) as entries:
            for entry in entries:
                if not entry.is_file(follow_symlinks=False):
                    continue
                file_path = Path(entry.path)
                if allowed_extensions is not None:
                    if file_path.suffix.casefold() not in allowed_extensions:
                        continue
                files.append(file_path)
    except OSError as exc:
        raise OSError(
            f"Unable to discover files in folder '{folder_path}': {exc}"
        ) from exc
    return sorted(
        files,
        key=lambda path: (path.name.casefold(), path.name),
    )

def generate_filename(
    filename: str | Path,
    settings: RenameSettings,
    index: int = 0,
) -> FilenameResult:
    """Generate a proposed filename without modifying the filesystem.

    Args:
        filename: Original filename or path.
        settings: Filename-generation configuration.
        index: Zero-based position in the rename sequence.

    Returns:
        A FilenameResult containing the proposed filename and warnings.

    Raises:
        TypeError: If the filename or settings have an invalid type.
        ValueError: If the filename or settings are invalid.
    """
    if not isinstance(filename, (str, Path)):
        raise TypeError("filename must be a string or Path.")
    if not isinstance(settings, RenameSettings):
        raise TypeError("settings must be a RenameSettings instance.")
    if not isinstance(settings.prefix, str):
        raise TypeError("prefix must be a string.")
    if not isinstance(settings.suffix, str):
        raise TypeError("suffix must be a string.")
    if not isinstance(settings.numbering_enabled, bool):
        raise TypeError("numbering_enabled must be a boolean.")
    if isinstance(settings.start_number, bool) or not isinstance(
        settings.start_number, int
    ):
        raise TypeError("start_number must be an integer.")
    if settings.start_number < 0:
        raise ValueError("start_number must not be negative.")
    if isinstance(settings.number_width, bool) or not isinstance(
        settings.number_width, int
    ):
        raise TypeError("number_width must be an integer.")
    if settings.number_width < 1:
        raise ValueError("number_width must be at least 1.")
    if isinstance(settings.increment, bool) or not isinstance(
        settings.increment, int
    ):
        raise TypeError("increment must be an integer.")
    if settings.increment < 1:
        raise ValueError("increment must be at least 1.")
    if isinstance(index, bool) or not isinstance(index, int):
        raise TypeError("index must be an integer.")
    if index < 0:
        raise ValueError("index must not be negative.")
    original_name = Path(filename).name
    if not original_name or original_name in {".", ".."}:
        raise ValueError("filename must contain a valid filename.")
    original_path = Path(original_name)
    stem = original_path.stem
    extension = original_path.suffix
    warnings = []
    if settings.numbering_enabled:
        number = settings.start_number + index * settings.increment
        number_text = str(number).zfill(settings.number_width)
        if len(str(number)) > settings.number_width:
            warnings.append(
                f"Number {number} exceeds the configured width "
                f"of {settings.number_width} digits."
            )
        new_name = (
            f"{settings.prefix}{number_text}"
            f"{settings.suffix}{extension}"
        )
    else:
        new_name = (
            f"{settings.prefix}{stem}"
            f"{settings.suffix}{extension}"
        )
    if new_name in {"", ".", ".."}:
        raise ValueError("Generated filename is invalid.")
    return FilenameResult(filename=new_name, warnings=warnings)

def build_rename_plan(files, settings):
    if not isinstance(files, (list, tuple)):
        raise TypeError("files must be a list or tuple of file paths.")
    if not isinstance(settings, RenameSettings):
        raise TypeError("settings must be a RenameSettings instance.")
    normalized_files = []
    seen_sources = set()
    for file_path in files:
        if not isinstance(file_path, (str, Path)):
            raise TypeError(
                "Every item in files must be a string or pathlib.Path."
            )
        source = Path(file_path)
        if source in seen_sources:
            raise ValueError(f"Duplicate source path: {source}")
        seen_sources.add(source)
        normalized_files.append(source)
    plan = RenamePlan()
    for index, source in enumerate(normalized_files):
        result = generate_filename(
            source.name,
            settings,
            index=index,
        )
        destination = source.with_name(result.filename)
        status = "unchanged" if source == destination else "pending"
        plan.entries.append(
            RenameEntry(
                source=source,
                destination=destination,
                status=status,
            )
        )
        plan.warnings.extend(
            f"{source.name}: {warning}"
            for warning in result.warnings
        )
    return plan

def validate_rename_plan(plan: RenamePlan) -> ValidationReport:
    """Validate a rename plan without modifying the filesystem.

    Existing destination paths are treated as conflicts, even if
    another entry proposes to rename the file currently occupying them.
    Unchanged entries are excluded from rename conflict checks.
    """
    if not isinstance(plan, RenamePlan):
        raise TypeError("plan must be a RenamePlan instance.")

    report = ValidationReport()
    seen_sources = set()
    destination_entries = {}

    invalid_characters = '<>:"/\\|?*'
    reserved_names = {
        "CON", "PRN", "AUX", "NUL",
        *(f"COM{i}" for i in range(1, 10)),
        *(f"LPT{i}" for i in range(1, 10)),
    }

    # First pass: check entry types, paths, statuses, and source files.
    for entry in plan.entries:
        if not isinstance(entry, RenameEntry):
            report.errors.append(
                "Rename plan contains an invalid entry."
            )
            continue
        if not isinstance(entry.source, Path):
            report.errors.append(
                f"Invalid source path: {entry.source!r}"
            )
            continue
        if not isinstance(entry.destination, Path):
            report.errors.append(
                f"Invalid destination path: {entry.destination!r}"
            )
            continue
        if entry.status not in {"pending", "unchanged"}:
            report.errors.append(
                f"Invalid entry status for {entry.source}: "
                f"{entry.status!r}"
            )
            continue

        # Compare normalized absolute paths for duplicate detection.
        source_key = os.path.normcase(
            os.path.abspath(entry.source)
        )
        if source_key in seen_sources:
            report.errors.append(
                f"Duplicate source path in plan: {entry.source}"
            )
        else:
            seen_sources.add(source_key)

        try:
            source_exists = entry.source.exists()
            source_is_file = (
                entry.source.is_file()
                and not entry.source.is_symlink()
            )
        except OSError as exc:
            report.errors.append(
                f"Unable to inspect source '{entry.source}': {exc}"
            )
            continue

        if not source_exists:
            report.errors.append(
                f"Source does not exist: {entry.source}"
            )
            continue
        if not source_is_file:
            report.errors.append(
                f"Source is not a regular, non-symbolic-link file: "
                f"{entry.source}"
            )
            continue

        source_key = os.path.normcase(
            os.path.abspath(entry.source)
        )
        destination_key = os.path.normcase(
            os.path.abspath(entry.destination)
        )

        if entry.status == "unchanged":
            if source_key != destination_key:
                report.errors.append(
                    f"Unchanged entry has different paths: "
                    f"{entry.source}"
                )
            continue

        # A pending entry must represent an actual rename.
        if source_key == destination_key:
            report.errors.append(
                f"Pending entry has identical source and destination: "
                f"{entry.source}"
            )
            continue

        # Validate the destination filename using Windows rules.
        destination_name = entry.destination.name
        reserved_base = destination_name.split(".")[0].upper()
        if (
            not destination_name
            or destination_name in {".", ".."}
            or any(ord(char) < 32 for char in destination_name)
            or any(char in invalid_characters for char in destination_name)
            or destination_name.endswith((" ", "."))
            or reserved_base in reserved_names
        ):
            report.errors.append(
                f"Invalid Windows destination filename: "
                f"{destination_name!r}"
            )
            continue

        # Keep the destination's parent directory unchanged.
        if destination_key in destination_entries:
            previous_source = destination_entries[destination_key]
            report.errors.append(
                f"Duplicate destination '{entry.destination}' "
                f"proposed by '{previous_source}' and '{entry.source}'."
            )
        else:
            destination_entries[destination_key] = entry.source

    # Second pass: inspect existing destinations.
    # Any occupied destination blocks a pending rename, including
    # destinations occupied by another source in this same plan.
    for entry in plan.entries:
        if not isinstance(entry, RenameEntry):
            continue
        if not isinstance(entry.source, Path):
            continue
        if not isinstance(entry.destination, Path):
            continue
        if entry.status != "pending":
            continue
        destination_key = os.path.normcase(
            os.path.abspath(entry.destination)
        )

        # Skip filesystem checks for destinations already identified
        # as invalid or duplicated; the corresponding errors are enough.
        destination_name = entry.destination.name
        reserved_base = destination_name.split(".")[0].upper()

        if (
            not destination_name
            or destination_name in {".", ".."}
            or any(ord(char) < 32 for char in destination_name)
            or any(char in invalid_characters for char in destination_name)
            or destination_name.endswith((" ", "."))
            or reserved_base in reserved_names
        ):
            continue
        if destination_key not in destination_entries:
            continue

        try:
            if entry.destination.exists() or entry.destination.is_symlink():
                report.errors.append(
                    f"Destination already exists: {entry.destination}"
                )
        except OSError as exc:
            report.errors.append(
                f"Unable to inspect destination "
                f"'{entry.destination}': {exc}"
            )

    report.is_valid = not report.errors
    return report


def execute_rename_plan(
    plan: RenamePlan,
    validation_report: ValidationReport,
    progress_callback: Callable[[int, int, RenameEntry], None] | None = None,
) -> OperationSummary:
    """Execute a validated rename plan with per-file safety checks.

    The function never intentionally overwrites an existing destination.
    Results are returned in an OperationSummary; persistent logging is
    postponed to Version 2.

    The caller is responsible for supplying the validation report
    corresponding to this plan.
    """
    if not isinstance(plan, RenamePlan):
        raise TypeError("plan must be a RenamePlan instance.")

    if not isinstance(validation_report, ValidationReport):
        raise TypeError(
            "validation_report must be a ValidationReport instance."
        )

    if progress_callback is not None and not callable(progress_callback):
        raise TypeError("progress_callback must be callable or None.")

    summary = OperationSummary(total_files=len(plan.entries))

    if not validation_report.is_valid:
        summary.refused_operations = len(plan.entries)
        summary.errors.append(
            "Batch refused: the rename plan has not passed validation."
        )
        return summary

    total = len(plan.entries)
    completed = 0

    for entry in plan.entries:
        outcome = "processed"

        try:
            if not isinstance(entry, RenameEntry):
                summary.refused_operations += 1
                summary.errors.append(
                    f"Operation refused: invalid plan entry at "
                    f"position {completed + 1}."
                )
                outcome = "refused"
            elif not isinstance(entry.source, Path) or not isinstance(
                entry.destination, Path
            ):
                summary.refused_operations += 1
                summary.errors.append(
                    "Operation refused: source and destination "
                    "must be pathlib.Path objects."
                )
                outcome = "refused"
            elif entry.status not in {"pending", "unchanged"}:
                summary.refused_operations += 1
                summary.errors.append(
                    f"Operation refused for '{entry.source}': "
                    f"unsupported status {entry.status!r}."
                )
                outcome = "refused"
            else:
                source = entry.source
                destination = entry.destination

                source_key = os.path.normcase(os.path.abspath(source))
                destination_key = os.path.normcase(
                    os.path.abspath(destination)
                )
                if entry.status == "unchanged":
                    if source_key != destination_key:
                        summary.refused_operations += 1
                        summary.errors.append(
                            f"Operation refused for '{source}': "
                            "unchanged entry has different paths."
                        )
                        outcome = "refused"
                    elif source.is_symlink() or not source.is_file():
                        summary.refused_operations += 1
                        summary.errors.append(
                            f"Operation refused: source is no longer "
                            f"a regular file: {source}"
                        )
                        outcome = "refused"
                    else:
                        summary.unchanged_files += 1
                        entry.status = "unchanged"
                        outcome = "unchanged"
                elif source_key == destination_key:
                    summary.refused_operations += 1
                    summary.errors.append(
                        f"Operation refused for '{source}': "
                        "pending entry has identical paths."
                    )
                    outcome = "refused"
                elif source.parent != destination.parent:
                    summary.refused_operations += 1
                    summary.errors.append(
                        f"Operation refused for '{source}': "
                        "destination must remain in the source folder."
                    )
                    outcome = "refused"
                elif source.is_symlink() or not source.is_file():
                    summary.refused_operations += 1
                    summary.errors.append(
                        f"Operation refused: source is missing, "
                        f"not a regular file, or is a symbolic link: "
                        f"{source}"
                    )
                    outcome = "refused"
                elif destination.exists() or destination.is_symlink():
                    summary.refused_operations += 1
                    summary.errors.append(
                        f"Operation refused: destination already exists: "
                        f"{destination}"
                    )
                    outcome = "refused"
                else:
                    try:
                        source.rename(destination)
                    except OSError as exc:
                        summary.failed_operations += 1
                        summary.errors.append(
                            f"Rename failed: '{source}' -> "
                            f"'{destination}': {exc}"
                        )
                        outcome = "failed"
                    else:
                        summary.successful_renames += 1
                        entry.status = "renamed"
                        outcome = "success"
        except OSError as exc:
            summary.refused_operations += 1
            summary.errors.append(
                f"Operation refused because a filesystem check failed: "
                f"{exc}"
            )
            outcome = "refused"
        completed += 1
        if progress_callback is not None:
            try:
                progress_callback(completed, total, entry)
            except Exception as exc:
                summary.errors.append(
                    f"Progress callback failed after processing "
                    f"item {completed}: {exc}"
                )
    return summary
