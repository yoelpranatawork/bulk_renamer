# test.py

import tempfile
import unittest

from pathlib import Path
from unittest.mock import patch


from core import (
    RenameEntry,
    RenamePlan,
    RenameSettings,
    ValidationReport,
    build_rename_plan,
    discover_files,
    execute_rename_plan,
    generate_filename,
    validate_rename_plan,
)


class TestFileDiscovery(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_discovers_files_in_deterministic_order(self):
        for name in ["b.txt", "A.txt", "C.txt"]:
            (self.folder / name).write_text("test", encoding="utf-8")

        files = discover_files(self.folder)

        self.assertEqual(
            [path.name for path in files],
            ["A.txt", "b.txt", "C.txt"],
        )

    def test_filters_extensions_case_insensitively(self):
        for name in ["photo.JPG", "image.jpg", "notes.txt"]:
            (self.folder / name).write_text("test", encoding="utf-8")

        files = discover_files(self.folder, extensions="jpg")

        self.assertEqual(
            {path.name for path in files},
            {"photo.JPG", "image.jpg"},
        )

    def test_excludes_subdirectories(self):
        (self.folder / "file.txt").write_text("test", encoding="utf-8")
        subfolder = self.folder / "subfolder"
        subfolder.mkdir()
        (subfolder / "nested.txt").write_text("test", encoding="utf-8")

        files = discover_files(self.folder)

        self.assertEqual([path.name for path in files], ["file.txt"])

    def test_returns_empty_list_when_no_files_match(self):
        (self.folder / "notes.txt").write_text("test", encoding="utf-8")

        self.assertEqual(
            discover_files(self.folder, extensions="jpg"),
            [],
        )

    def test_rejects_nonexistent_folder(self):
        missing_folder = self.folder / "missing"

        with self.assertRaises(FileNotFoundError):
            discover_files(missing_folder)


class TestFilenameGeneration(unittest.TestCase):
    def test_generates_numbered_filename(self):
        result = generate_filename(
            "photo.JPG",
            RenameSettings(),
            index=0,
        )

        self.assertEqual(result.filename, "001.JPG")
        self.assertEqual(result.warnings, [])

    def test_generates_filename_without_numbering(self):
        settings = RenameSettings(
            prefix="new_",
            suffix="_edited",
            numbering_enabled=False,
        )

        result = generate_filename("my.photo.jpg", settings)

        self.assertEqual(
            result.filename,
            "new_my.photo_edited.jpg",
        )

    def test_warns_when_number_exceeds_width(self):
        settings = RenameSettings(
            start_number=1000,
            number_width=3,
        )

        result = generate_filename("photo.jpg", settings)

        self.assertEqual(result.filename, "1000.jpg")
        self.assertEqual(len(result.warnings), 1)


class TestRenamePlan(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_builds_plan_in_supplied_order(self):
        files = [
            self.folder / "photo.jpg",
            self.folder / "report.txt",
        ]

        plan = build_rename_plan(files, RenameSettings())

        self.assertEqual(
            [entry.destination.name for entry in plan.entries],
            ["001.jpg", "002.txt"],
        )
        self.assertEqual(
            [entry.status for entry in plan.entries],
            ["pending", "pending"],
        )

    def test_marks_unchanged_entry(self):
        plan = build_rename_plan(
            [self.folder / "001.jpg"],
            RenameSettings(),
        )

        self.assertEqual(plan.entries[0].status, "unchanged")

    def test_rejects_duplicate_source_paths(self):
        source = self.folder / "photo.jpg"

        with self.assertRaises(ValueError):
            build_rename_plan(
                [source, source],
                RenameSettings(),
            )

    def test_empty_input_produces_empty_plan(self):
        plan = build_rename_plan([], RenameSettings())

        self.assertEqual(plan.entries, [])
        self.assertEqual(plan.warnings, [])


class TestRenamePlanValidation(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_accepts_valid_plan(self):
        source = self.folder / "photo.jpg"
        source.write_text("test", encoding="utf-8")

        plan = build_rename_plan([source], RenameSettings())
        report = validate_rename_plan(plan)

        self.assertTrue(report.is_valid)
        self.assertEqual(report.errors, [])

    def test_rejects_missing_source(self):
        source = self.folder / "missing.jpg"
        destination = self.folder / "001.jpg"
        plan = RenamePlan(
            entries=[RenameEntry(source, destination)]
        )

        report = validate_rename_plan(plan)

        self.assertFalse(report.is_valid)
        self.assertTrue(
            any("Source does not exist" in error
                for error in report.errors)
        )

    def test_rejects_existing_destination(self):
        source = self.folder / "photo.jpg"
        destination = self.folder / "001.jpg"
        source.write_text("source", encoding="utf-8")
        destination.write_text("destination", encoding="utf-8")

        plan = build_rename_plan([source], RenameSettings())
        report = validate_rename_plan(plan)

        self.assertFalse(report.is_valid)
        self.assertTrue(
            any("Destination already exists" in error
                for error in report.errors)
        )
        self.assertEqual(source.read_text(encoding="utf-8"), "source")
        self.assertEqual(
            destination.read_text(encoding="utf-8"),
            "destination",
        )

    def test_rejects_duplicate_destinations(self):
        source_a = self.folder / "a.txt"
        source_b = self.folder / "b.txt"
        destination = self.folder / "result.txt"

        source_a.write_text("a", encoding="utf-8")
        source_b.write_text("b", encoding="utf-8")

        plan = RenamePlan(
            entries=[
                RenameEntry(source_a, destination),
                RenameEntry(source_b, destination),
            ]
        )

        report = validate_rename_plan(plan)

        self.assertFalse(report.is_valid)
        self.assertTrue(
            any("Duplicate destination" in error
                for error in report.errors)
        )

    def test_rejects_invalid_windows_filename(self):
        source = self.folder / "source.txt"
        source.write_text("test", encoding="utf-8")

        plan = RenamePlan(
            entries=[
                RenameEntry(source, self.folder / "bad?.txt")
            ]
        )

        report = validate_rename_plan(plan)

        self.assertFalse(report.is_valid)
        self.assertTrue(
            any("Invalid Windows destination filename" in error
                for error in report.errors)
        )

    def test_accepts_unchanged_entry(self):
        source = self.folder / "001.txt"
        source.write_text("test", encoding="utf-8")

        plan = RenamePlan(
            entries=[RenameEntry(source, source, "unchanged")]
        )

        report = validate_rename_plan(plan)

        self.assertTrue(report.is_valid)
        self.assertEqual(report.errors, [])

    def test_collects_multiple_validation_errors(self):
        missing_source = self.folder / "missing.txt"
        existing_source = self.folder / "source.txt"
        existing_source.write_text("test", encoding="utf-8")

        plan = RenamePlan(
            entries=[
                RenameEntry(
                    missing_source,
                    self.folder / "new.txt",
                ),
                RenameEntry(
                    existing_source,
                    self.folder / "bad?.txt",
                ),
            ]
        )

        report = validate_rename_plan(plan)

        self.assertFalse(report.is_valid)
        self.assertGreaterEqual(len(report.errors), 2)
        self.assertTrue(
            any("Source does not exist" in error
                for error in report.errors)
        )
        self.assertTrue(
            any("Invalid Windows destination filename" in error
                for error in report.errors)
        )


class TestRenameExecution(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_successful_rename_preserves_contents(self):
        source = self.folder / "photo.jpg"
        source.write_text("test content", encoding="utf-8")

        plan = build_rename_plan([source], RenameSettings())
        report = validate_rename_plan(plan)
        summary = execute_rename_plan(plan, report)

        destination = self.folder / "001.jpg"

        self.assertTrue(report.is_valid)
        self.assertFalse(source.exists())
        self.assertTrue(destination.is_file())
        self.assertEqual(
            destination.read_text(encoding="utf-8"),
            "test content",
        )
        self.assertEqual(summary.total_files, 1)
        self.assertEqual(summary.successful_renames, 1)
        self.assertEqual(summary.failed_operations, 0)
        self.assertEqual(summary.refused_operations, 0)

    def test_invalid_validation_report_refuses_batch(self):
        plan = RenamePlan(
            entries=[
                RenameEntry(
                    self.folder / "a.txt",
                    self.folder / "001.txt",
                ),
                RenameEntry(
                    self.folder / "b.txt",
                    self.folder / "002.txt",
                ),
            ]
        )
        report = ValidationReport(
            is_valid=False,
            errors=["Test validation error"],
        )

        summary = execute_rename_plan(plan, report)

        self.assertEqual(summary.total_files, 2)
        self.assertEqual(summary.refused_operations, 2)
        self.assertEqual(summary.successful_renames, 0)
        self.assertTrue(
            any("Batch refused" in error for error in summary.errors)
        )

    def test_unchanged_file_is_counted_without_renaming(self):
        source = self.folder / "001.txt"
        source.write_text("unchanged content", encoding="utf-8")

        plan = build_rename_plan([source], RenameSettings())
        report = validate_rename_plan(plan)
        summary = execute_rename_plan(plan, report)

        self.assertTrue(report.is_valid)
        self.assertTrue(source.exists())
        self.assertEqual(
            source.read_text(encoding="utf-8"),
            "unchanged content",
        )
        self.assertEqual(summary.unchanged_files, 1)
        self.assertEqual(summary.successful_renames, 0)

    def test_partial_failure_does_not_stop_remaining_renames(self):
        source_a = self.folder / "a.txt"
        source_b = self.folder / "b.txt"
        source_a.write_text("content a", encoding="utf-8")
        source_b.write_text("content b", encoding="utf-8")

        plan = build_rename_plan(
            [source_a, source_b],
            RenameSettings(),
        )
        report = validate_rename_plan(plan)
        self.assertTrue(report.is_valid)

        original_rename = Path.rename
        calls = 0

        def controlled_rename(path, target):
            nonlocal calls
            calls += 1

            if calls == 1:
                raise PermissionError("Simulated permission error")

            return original_rename(path, target)

        with patch.object(Path, "rename", controlled_rename):
            summary = execute_rename_plan(plan, report)

        self.assertEqual(summary.total_files, 2)
        self.assertEqual(summary.failed_operations, 1)
        self.assertEqual(summary.successful_renames, 1)
        self.assertTrue(source_a.exists())
        self.assertFalse(source_b.exists())
        self.assertTrue((self.folder / "002.txt").is_file())
        self.assertTrue(
            any("Simulated permission error" in error
                for error in summary.errors)
        )

    def test_progress_callback_reports_each_entry(self):
        source_a = self.folder / "a.txt"
        source_b = self.folder / "b.txt"
        source_a.write_text("a", encoding="utf-8")
        source_b.write_text("b", encoding="utf-8")

        plan = build_rename_plan(
            [source_a, source_b],
            RenameSettings(),
        )
        report = validate_rename_plan(plan)
        progress = []

        summary = execute_rename_plan(
            plan,
            report,
            lambda completed, total, entry: progress.append(
                (completed, total, entry.source.name)
            ),
        )

        self.assertEqual(
            progress,
            [
                (1, 2, "a.txt"),
                (2, 2, "b.txt"),
            ],
        )
        self.assertEqual(summary.successful_renames, 2)

    def test_progress_callback_error_is_recorded(self):
        source = self.folder / "photo.jpg"
        source.write_text("test", encoding="utf-8")

        plan = build_rename_plan([source], RenameSettings())
        report = validate_rename_plan(plan)

        def broken_callback(completed, total, entry):
            raise RuntimeError("Simulated callback error")

        summary = execute_rename_plan(
            plan,
            report,
            broken_callback,
        )

        self.assertEqual(summary.successful_renames, 1)
        self.assertTrue(
            any("Simulated callback error" in error
                for error in summary.errors)
        )


if __name__ == "__main__":
    unittest.main()
