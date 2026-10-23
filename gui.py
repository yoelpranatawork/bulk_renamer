# gui.py

from __future__ import annotations

import queue
import threading
import tkinter as tk

from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import core as engine


class RenamerApp:
    """Main application window."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Bulk Renamer")
        self.root.minsize(800, 600)
        self._center_window(800, 600)

        # User configuration.
        self.folder_var = tk.StringVar()
        self.extensions_var = tk.StringVar()
        self.prefix_var = tk.StringVar()
        self.suffix_var = tk.StringVar()
        self.numbering_var = tk.BooleanVar(value=True)
        self.start_number_var = tk.StringVar(value="1")
        self.number_width_var = tk.StringVar(value="3")
        self.increment_var = tk.StringVar(value="1")

        # Status information.
        self.status_var = tk.StringVar(
            value="Select a folder to begin."
        )
        self.count_var = tk.StringVar(
            value="No preview generated."
        )
        self.progress_var = tk.DoubleVar(value=0)

        # Core-engine data.
        self.files: list[Path] = []
        self.plan: engine.RenamePlan | None = None
        self.validation_report: engine.ValidationReport | None = None
        self.settings: engine.RenameSettings | None = None

        # Worker-thread communication.
        self.operation_running = False
        self.messages: queue.Queue = queue.Queue()

        self._build_ui()
        self._bind_invalidation_events()
        self._update_numbering_controls()
        self._set_rename_enabled(False)

    def _center_window(
        self,
        width: int,
        height: int,
    ) -> None:
        """Set the initial window size and center it on the screen."""

        self.root.update_idletasks()

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        x = max(0, (screen_width - width) // 2)
        y = max(0, (screen_height - height) // 2)

        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _build_ui(self) -> None:
        """Create the main window and its sections."""

        main = ttk.Frame(self.root, padding=8)
        main.grid(row=0, column=0, sticky="nsew")

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        main.columnconfigure(0, weight=1)
        main.rowconfigure(2, weight=1)

        # ----------------------------------------------------------
        # 1. Folder and extension selection
        # ----------------------------------------------------------

        folder_frame = ttk.LabelFrame(
            main,
            text="1. Folder and File Selection",
            padding=8,
        )
        folder_frame.grid(
            row=0, column=0, sticky="ew", pady=(0, 8)
        )
        folder_frame.columnconfigure(1, weight=1)

        ttk.Label(
            folder_frame, text="Folder:"
        ).grid(
            row=0, column=0, sticky="w", padx=(0, 8), pady=3
        )

        self.folder_entry = ttk.Entry(
            folder_frame,
            textvariable=self.folder_var,
        )
        self.folder_entry.grid(
            row=0, column=1, sticky="ew", pady=3
        )

        self.browse_button = ttk.Button(
            folder_frame,
            text="Browse...",
            command=self._browse_folder,
        )
        self.browse_button.grid(
            row=0, column=2, padx=(8, 0), pady=3
        )

        ttk.Label(
            folder_frame, text="Extensions:"
        ).grid(
            row=1, column=0, sticky="w", padx=(0, 8), pady=3
        )

        self.extensions_entry = ttk.Entry(
            folder_frame,
            textvariable=self.extensions_var,
        )
        self.extensions_entry.grid(
            row=1, column=1, sticky="ew", pady=3
        )

        ttk.Label(
            folder_frame,
            text="Blank = all files",
        ).grid(
            row=1, column=2, sticky="w", padx=(8, 0)
        )

        # ----------------------------------------------------------
        # 2. Naming configuration and 4. Validation/progress
        # ----------------------------------------------------------

        settings_row = ttk.Frame(main)
        settings_row.grid(
            row=1, column=0, sticky="ew", pady=(0, 8)
        )

        settings_row.columnconfigure(0, weight=1, uniform="panels")
        settings_row.columnconfigure(1, weight=1, uniform="panels")

        naming_frame = ttk.LabelFrame(
            settings_row,
            text="2. Naming Configuration",
            padding=8,
        )
        naming_frame.grid(
            row=0, column=0, sticky="nsew", padx=(0, 4)
        )
        naming_frame.columnconfigure(1, weight=1)

        ttk.Label(naming_frame, text="Prefix:").grid(
            row=0, column=0, sticky="w", padx=(0, 6), pady=3
        )
        self.prefix_entry = ttk.Entry(
            naming_frame, textvariable=self.prefix_var
        )
        self.prefix_entry.grid(
            row=0, column=1, sticky="ew", pady=3
        )

        ttk.Label(naming_frame, text="Suffix:").grid(
            row=1, column=0, sticky="w", padx=(0, 6), pady=3
        )
        self.suffix_entry = ttk.Entry(
            naming_frame, textvariable=self.suffix_var
        )
        self.suffix_entry.grid(
            row=1, column=1, sticky="ew", pady=3
        )

        self.numbering_check = ttk.Checkbutton(
            naming_frame,
            text="Enable sequential numbering",
            variable=self.numbering_var,
            command=self._on_numbering_changed,
        )
        self.numbering_check.grid(
            row=2, column=0, columnspan=2,
            sticky="w", pady=(4, 6)
        )

        ttk.Label(naming_frame, text="Start number:").grid(
            row=3, column=0, sticky="w", padx=(0, 6), pady=2
        )
        self.start_number_entry = ttk.Entry(
            naming_frame,
            textvariable=self.start_number_var,
        )
        self.start_number_entry.grid(
            row=3, column=1, sticky="ew", pady=2
        )

        ttk.Label(naming_frame, text="Number width:").grid(
            row=4, column=0, sticky="w", padx=(0, 6), pady=2
        )
        self.number_width_entry = ttk.Entry(
            naming_frame,
            textvariable=self.number_width_var,
        )
        self.number_width_entry.grid(
            row=4, column=1, sticky="ew", pady=2
        )

        ttk.Label(naming_frame, text="Increment:").grid(
            row=5, column=0, sticky="w", padx=(0, 6), pady=2
        )
        self.increment_entry = ttk.Entry(
            naming_frame,
            textvariable=self.increment_var,
        )
        self.increment_entry.grid(
            row=5, column=1, sticky="ew", pady=2
        )

        validation_frame = ttk.LabelFrame(
            settings_row,
            text="4. Validation and Progress",
            padding=8,
        )
        validation_frame.grid(
            row=0, column=1, sticky="nsew", padx=(4, 0)
        )
        validation_frame.columnconfigure(0, weight=1)
        validation_frame.rowconfigure(1, weight=1)

        self.validation_status = ttk.Label(
            validation_frame,
            text="Validation: Not yet checked",
        )
        self.validation_status.grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )

        message_frame = ttk.Frame(validation_frame)
        message_frame.grid(
            row=1, column=0, sticky="nsew"
        )
        message_frame.columnconfigure(0, weight=1)
        message_frame.rowconfigure(0, weight=1)

        self.message_text = tk.Text(
            message_frame,
            height=5,
            wrap="word",
            state="disabled",
        )
        self.message_text.grid(
            row=0, column=0, sticky="nsew"
        )

        message_scrollbar = ttk.Scrollbar(
            message_frame,
            orient="vertical",
            command=self.message_text.yview,
        )
        message_scrollbar.grid(
            row=0, column=1, sticky="ns"
        )

        self.message_text.configure(
            yscrollcommand=message_scrollbar.set
        )

        self.progress_bar = ttk.Progressbar(
            validation_frame,
            variable=self.progress_var,
            maximum=100,
            mode="determinate",
        )
        self.progress_bar.grid(
            row=2, column=0, sticky="ew", pady=(7, 3)
        )

        self.progress_label = ttk.Label(
            validation_frame,
            text="0% complete",
        )
        self.progress_label.grid(
            row=3, column=0, sticky="w"
        )
        # ----------------------------------------------------------
        # 3. Rename preview
        # ----------------------------------------------------------

        preview_frame = ttk.LabelFrame(
            main,
            text="3. Rename Preview",
            padding=6,
        )
        preview_frame.grid(
            row=2, column=0, sticky="nsew", pady=(0, 8)
        )
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)

        columns = ("source", "destination", "status")

        self.preview_tree = ttk.Treeview(
            preview_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        self.preview_tree.heading(
            "source", text="Original Filename"
        )
        self.preview_tree.heading(
            "destination", text="Proposed Filename"
        )
        self.preview_tree.heading(
            "status", text="Status"
        )

        self.preview_tree.column(
            "source",
            width=200,
            minwidth=100,
            stretch=True,
        )
        self.preview_tree.column(
            "destination",
            width=250,
            minwidth=100,
            stretch=True,
        )
        self.preview_tree.column(
            "status",
            width=90,
            minwidth=70,
            stretch=False,
            anchor="center",
        )

        self.preview_tree.grid(
            row=0, column=0, sticky="nsew"
        )

        vertical_scrollbar = ttk.Scrollbar(
            preview_frame,
            orient="vertical",
            command=self.preview_tree.yview,
        )
        vertical_scrollbar.grid(
            row=0, column=1, sticky="ns"
        )

        horizontal_scrollbar = ttk.Scrollbar(
            preview_frame,
            orient="horizontal",
            command=self.preview_tree.xview,
        )
        horizontal_scrollbar.grid(
            row=1, column=0, sticky="ew"
        )

        self.preview_tree.configure(
            yscrollcommand=vertical_scrollbar.set,
            xscrollcommand=horizontal_scrollbar.set,
        )

        self.preview_tree.tag_configure(
            "unchanged", foreground="#666666"
        )
        self.preview_tree.tag_configure(
            "warning", foreground="#9A6700"
        )
        self.preview_tree.tag_configure(
            "error", foreground="#B42318"
        )
        self.preview_tree.tag_configure(
            "renamed", foreground="#18794E"
        )

        # File counts and current status.
        ttk.Label(
            main,
            textvariable=self.count_var,
        ).grid(
            row=3, column=0, sticky="w", pady=(0, 5)
        )

        ttk.Label(
            main,
            textvariable=self.status_var,
        ).grid(
            row=4, column=0, sticky="w", pady=(0, 5)
        )

        # Action buttons.
        actions = ttk.Frame(main)
        actions.grid(
            row=5, column=0, sticky="ew"
        )

        for column in range(3):
            actions.columnconfigure(column, weight=1)

        self.preview_button = ttk.Button(
            actions,
            text="Generate Preview",
            command=self._generate_preview,
        )
        self.preview_button.grid(
            row=0, column=0, sticky="ew", padx=(0, 4)
        )

        self.validate_button = ttk.Button(
            actions,
            text="Validate Plan",
            command=self._validate_plan,
        )
        self.validate_button.grid(
            row=0, column=1, sticky="ew", padx=4
        )

        self.rename_button = ttk.Button(
            actions,
            text="Rename Files",
            command=self._rename_files,
        )
        self.rename_button.grid(
            row=0, column=2, sticky="ew", padx=4
        )

        self.reset_button = ttk.Button(
            actions,
            text="Reset",
            command=self._reset_form,
        )
        self.reset_button.grid(
            row=0, column=3, sticky="ew", padx=(4, 0)
        )

        actions.columnconfigure(3, weight=1)

    # --------------------------------------------------------------
    # Configuration and interface state
    # --------------------------------------------------------------

    def _bind_invalidation_events(self) -> None:
        """Invalidate an old preview when settings change."""

        variables = (
            self.folder_var,
            self.extensions_var,
            self.prefix_var,
            self.suffix_var,
            self.numbering_var,
            self.start_number_var,
            self.number_width_var,
            self.increment_var,
        )

        for variable in variables:
            variable.trace_add(
                "write", self._on_configuration_changed
            )

    def _on_configuration_changed(self, *_args) -> None:
        if not self.operation_running:
            self._invalidate_plan()

    def _invalidate_plan(self) -> None:
        """Discard preview and validation results that are out of date."""

        self.files = []
        self.plan = None
        self.validation_report = None
        self.settings = None

        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)

        self.count_var.set(
            "Preview is out of date. Generate a new preview."
        )
        self.validation_status.configure(
            text="Validation: Not yet checked"
        )
        self.status_var.set(
            "Configuration changed; regenerate the preview."
        )

        self.progress_var.set(0)
        self.progress_label.configure(text="0% complete")

        self._set_rename_enabled(False)
        self._set_messages("")

    def _set_messages(self, text: str) -> None:
        self.message_text.configure(state="normal")
        self.message_text.delete("1.0", "end")

        if text:
            self.message_text.insert("1.0", text)

        self.message_text.configure(state="disabled")

    def _append_messages(self, text: str) -> None:
        self.message_text.configure(state="normal")
        self.message_text.insert("end", text + "\n")
        self.message_text.see("end")
        self.message_text.configure(state="disabled")

    def _set_rename_enabled(self, enabled: bool) -> None:
        state = (
            "normal"
            if enabled and not self.operation_running
            else "disabled"
        )
        self.rename_button.configure(state=state)

    def _set_busy(self, busy: bool) -> None:
        """Disable configuration controls while a rename is running."""

        self.operation_running = busy
        state = "disabled" if busy else "normal"

        widgets = (
            self.browse_button,
            self.folder_entry,
            self.extensions_entry,
            self.prefix_entry,
            self.suffix_entry,
            self.numbering_check,
            self.start_number_entry,
            self.number_width_entry,
            self.increment_entry,
            self.preview_button,
            self.validate_button,
        )

        for widget in widgets:
            widget.configure(state=state)

        if not busy:
            self._update_numbering_controls()

        can_rename = (
            not busy
            and self.plan is not None
            and self.validation_report is not None
            and self.validation_report.is_valid
        )
        self._set_rename_enabled(can_rename)

    def _update_numbering_controls(self) -> None:
        state = (
            "normal"
            if self.numbering_var.get()
            and not self.operation_running
            else "disabled"
        )

        for widget in (
            self.start_number_entry,
            self.number_width_entry,
            self.increment_entry,
        ):
            widget.configure(state=state)

    def _on_numbering_changed(self) -> None:
        self._update_numbering_controls()
        self._invalidate_plan()

    def _reset_form(self) -> None:
        """Restore the GUI to its initial state."""

        if self.operation_running:
            return

        # Clear folder and naming configuration.
        self.folder_var.set("")
        self.extensions_var.set("")
        self.prefix_var.set("")
        self.suffix_var.set("")
        self.numbering_var.set(True)
        self.start_number_var.set("1")
        self.number_width_var.set("3")
        self.increment_var.set("1")

        # Clear the previous preview and validation results.
        self._invalidate_plan()

        self.progress_var.set(0)
        self.progress_label.configure(text="0% complete")
        self.count_var.set("No preview generated.")
        self.status_var.set(
            "Form reset. Select a folder to begin."
        )
        self.validation_status.configure(
            text="Validation: Not yet checked"
        )

        self._set_messages("")

        # Restore the initial focus.
        self.folder_entry.focus_set()

    def _browse_folder(self) -> None:
        selected = filedialog.askdirectory(
            parent=self.root,
            title="Select folder containing files to rename",
        )

        if selected:
            self.folder_var.set(selected)

    # --------------------------------------------------------------
    # Read and validate GUI settings
    # --------------------------------------------------------------

    def _read_settings(self) -> engine.RenameSettings:
        try:
            start_number = int(
                self.start_number_var.get().strip()
            )
            number_width = int(
                self.number_width_var.get().strip()
            )
            increment = int(
                self.increment_var.get().strip()
            )
        except ValueError as exc:
            raise ValueError(
                "Start number, number width, and increment "
                "must be whole numbers."
            ) from exc

        return engine.RenameSettings(
            prefix=self.prefix_var.get(),
            suffix=self.suffix_var.get(),
            numbering_enabled=self.numbering_var.get(),
            start_number=start_number,
            number_width=number_width,
            increment=increment,
        )

    def _read_extensions(self) -> list[str] | None:
        text = self.extensions_var.get().strip()

        if not text:
            return None

        extensions = [
            item.strip()
            for item in text.replace(";", ",").split(",")
        ]

        if any(not item for item in extensions):
            raise ValueError(
                "Enter extensions separated by commas, "
                "for example: jpg, .png"
            )

        return extensions

    # --------------------------------------------------------------
    # Preview generation
    # --------------------------------------------------------------

    def _generate_preview(self) -> None:
        if self.operation_running:
            return

        self._invalidate_plan()

        try:
            folder = self.folder_var.get().strip()

            if not folder:
                raise ValueError("Select a folder first.")

            settings = self._read_settings()
            extensions = self._read_extensions()

            # Discover files once. Reuse this list for the plan.
            files = engine.discover_files(folder, extensions)
            plan = engine.build_rename_plan(files, settings)

        except (OSError, TypeError, ValueError) as exc:
            self.status_var.set("Unable to generate preview.")
            self.validation_status.configure(
                text="Validation: Not available"
            )
            self._append_messages(f"ERROR: {exc}")

            messagebox.showerror(
                "Preview Error",
                str(exc),
                parent=self.root,
            )
            return

        self.files = files
        self.settings = settings
        self.plan = plan
        self.validation_report = None

        self._populate_preview()

        self.progress_var.set(0)
        self.progress_label.configure(text="0% complete")

        self.validation_status.configure(
            text="Validation: Not yet checked"
        )
        self._set_rename_enabled(False)

        rename_count = sum(
            entry.status == "pending"
            for entry in plan.entries
        )
        unchanged_count = sum(
            entry.status == "unchanged"
            for entry in plan.entries
        )

        self.count_var.set(
            f"{len(files)} files found | "
            f"{rename_count} planned changes | "
            f"{unchanged_count} unchanged"
        )

        messages = [
            f"WARNING: {warning}"
            for warning in plan.warnings
        ]

        if not files:
            messages.append("No eligible files were found.")

        self._set_messages("\n".join(messages))
        self.status_var.set(
            "Preview generated. Validate before renaming."
        )

    def _populate_preview(self) -> None:
        for item in self.preview_tree.get_children():
            self.preview_tree.delete(item)

        if self.plan is None:
            return

        warning_sources = set()

        for warning in self.plan.warnings:
            if ":" in warning:
                warning_sources.add(
                    warning.split(":", 1)[0]
                )

        for index, entry in enumerate(self.plan.entries):
            tags = ()

            if entry.status == "unchanged":
                tags = ("unchanged",)
            elif entry.source.name in warning_sources:
                tags = ("warning",)

            self.preview_tree.insert(
                "",
                "end",
                iid=f"file_{index}",
                values=(
                    entry.source.name,
                    entry.destination.name,
                    entry.status,
                ),
                tags=tags,
            )

    # --------------------------------------------------------------
    # Batch validation
    # --------------------------------------------------------------

    def _validate_plan(self) -> None:
        if self.operation_running:
            return

        if self.plan is None:
            messagebox.showwarning(
                "Preview Required",
                "Generate a preview before validating.",
                parent=self.root,
            )
            return

        self._set_rename_enabled(False)
        self._set_messages("")

        try:
            report = engine.validate_rename_plan(self.plan)
        except Exception as exc:
            self.validation_report = None

            self.validation_status.configure(
                text="Validation: Failed"
            )
            self.status_var.set(
                "Validation could not be completed."
            )
            self._append_messages(f"ERROR: {exc}")

            messagebox.showerror(
                "Validation Error",
                str(exc),
                parent=self.root,
            )
            return

        self.validation_report = report

        messages = []

        for error in report.errors:
            messages.append(f"ERROR: {error}")

        for warning in report.warnings:
            messages.append(f"WARNING: {warning}")

        if not messages:
            messages.append(
                "No validation errors or warnings."
            )

        self._set_messages("\n".join(messages))

        if report.is_valid:
            self.validation_status.configure(
                text="Validation: Passed"
            )
            self.status_var.set(
                "Plan validated successfully."
            )
            self._set_rename_enabled(True)
        else:
            self.validation_status.configure(
                text="Validation: Failed"
            )
            self.status_var.set(
                f"Validation failed: {len(report.errors)} error(s)."
            )
            self._set_rename_enabled(False)

    # --------------------------------------------------------------
    # Rename execution
    # --------------------------------------------------------------

    def _rename_files(self) -> None:
        if self.operation_running:
            return

        if (
            self.plan is None
            or self.validation_report is None
            or not self.validation_report.is_valid
        ):
            messagebox.showwarning(
                "Validation Required",
                "Generate a preview and successfully validate it first.",
                parent=self.root,
            )
            return

        pending_count = sum(
            entry.status == "pending"
            for entry in self.plan.entries
        )
        unchanged_count = sum(
            entry.status == "unchanged"
            for entry in self.plan.entries
        )

        if pending_count == 0:
            messagebox.showinfo(
                "Nothing to Rename",
                "There are no filename changes to perform.",
                parent=self.root,
            )
            return

        confirmed = messagebox.askyesno(
            "Confirm Rename Operation",
            f"Rename {pending_count} file(s)?\n\n"
            f"Unchanged files: {unchanged_count}\n\n"
            "This operation changes filenames on disk. "
            "Make sure you have reviewed the preview.",
            icon="warning",
            parent=self.root,
        )

        if not confirmed:
            return

        # Check the plan again immediately before execution.
        try:
            report = engine.validate_rename_plan(self.plan)
        except Exception as exc:
            messagebox.showerror(
                "Validation Error",
                str(exc),
                parent=self.root,
            )
            return

        self.validation_report = report

        if not report.is_valid:
            self.validation_status.configure(
                text="Validation: Failed"
            )
            self._set_messages(
                "\n".join(
                    f"ERROR: {error}"
                    for error in report.errors
                )
            )
            self._set_rename_enabled(False)

            messagebox.showerror(
                "Plan Changed",
                "The plan is no longer valid. Review the errors "
                "and generate a new preview.",
                parent=self.root,
            )
            return

        plan = self.plan
        validation_report = self.validation_report

        self.messages = queue.Queue()
        self.progress_var.set(0)
        self.progress_label.configure(text="0% complete")
        self._set_messages("Rename operation started.")
        self.status_var.set("Renaming files...")

        self._set_busy(True)

        worker = threading.Thread(
            target=self._worker_execute,
            args=(plan, validation_report, self.messages),
            daemon=True,
        )
        worker.start()

        self.root.after(100, self._process_worker_messages)

    @staticmethod
    def _worker_execute(
        plan: engine.RenamePlan,
        report: engine.ValidationReport,
        messages: queue.Queue,
    ) -> None:
        """Execute the batch outside the GUI thread."""

        def on_progress(
            completed: int,
            total: int,
            entry: engine.RenameEntry,
        ) -> None:
            messages.put(
                (
                    "progress",
                    completed,
                    total,
                    entry.source.name,
                    entry.status,
                )
            )

        try:
            summary = engine.execute_rename_plan(
                plan,
                report,
                progress_callback=on_progress,
            )
        except Exception as exc:
            messages.put(("fatal_error", str(exc)))
        else:
            messages.put(("complete", summary))

    def _process_worker_messages(self) -> None:
        """Process queued worker results on the Tkinter main thread."""

        try:
            while True:
                message = self.messages.get_nowait()
                kind = message[0]

                if kind == "progress":
                    (
                        _,
                        completed,
                        total,
                        filename,
                        status,
                    ) = message

                    percent = (
                        completed / total * 100
                        if total
                        else 100
                    )

                    self.progress_var.set(percent)
                    self.progress_label.configure(
                        text=(
                            f"{completed}/{total} files processed "
                            f"({percent:.0f}%)"
                        )
                    )
                    self.status_var.set(
                        f"Processing: {filename}"
                    )

                    self._update_row_status(filename, status)

                elif kind == "fatal_error":
                    _, error = message

                    self._set_busy(False)
                    self.status_var.set(
                        "Rename operation stopped."
                    )
                    self._append_messages(
                        f"FATAL ERROR: {error}"
                    )

                    messagebox.showerror(
                        "Operation Error",
                        error,
                        parent=self.root,
                    )
                    return

                elif kind == "complete":
                    _, summary = message
                    self._finish_operation(summary)
                    return

        except queue.Empty:
            pass

        if self.operation_running:
            self.root.after(
                100, self._process_worker_messages
            )

    def _update_row_status(
        self,
        filename: str,
        status: str,
    ) -> None:
        """Update the displayed status of a processed file."""

        for item_id in self.preview_tree.get_children():
            values = self.preview_tree.item(
                item_id, "values"
            )

            if values and values[0] == filename:
                self.preview_tree.set(
                    item_id, "status", status
                )

                if status == "renamed":
                    self.preview_tree.item(
                        item_id, tags=("renamed",)
                    )
                elif status == "unchanged":
                    self.preview_tree.item(
                        item_id, tags=("unchanged",)
                    )
                elif status in {"failed", "refused"}:
                    self.preview_tree.item(
                        item_id, tags=("error",)
                    )

                break

    def _finish_operation(
        self,
        summary: engine.OperationSummary,
    ) -> None:
        """Display the final summary and invalidate the old plan."""

        self._set_busy(False)

        if summary.total_files:
            self.progress_var.set(100)
            self.progress_label.configure(
                text=(
                    f"{summary.total_files}/"
                    f"{summary.total_files} files processed"
                )
            )
        else:
            self.progress_var.set(0)
            self.progress_label.configure(
                text="No files to process"
            )

        self.validation_status.configure(
            text="Validation: Operation completed"
        )
        self.status_var.set("Rename operation finished.")

        result_lines = [
            "Operation summary",
            "-----------------",
            f"Total files: {summary.total_files}",
            f"Successful renames: {summary.successful_renames}",
            f"Unchanged files: {summary.unchanged_files}",
            f"Skipped files: {summary.skipped_files}",
            f"Refused operations: {summary.refused_operations}",
            f"Failed operations: {summary.failed_operations}",
        ]

        if summary.errors:
            result_lines.append("")
            result_lines.append("Errors and details:")
            result_lines.extend(
                f"- {error}" for error in summary.errors
            )

        self._set_messages("\n".join(result_lines))

        # Require a fresh preview before another operation.
        self.plan = None
        self.validation_report = None
        self.settings = None
        self._set_rename_enabled(False)

        self.count_var.set(
            "Operation completed. Generate a new preview "
            "before another run."
        )

        if summary.errors:
            messagebox.showwarning(
                "Operation Completed with Issues",
                "\n".join(result_lines),
                parent=self.root,
            )
        else:
            messagebox.showinfo(
                "Operation Completed",
                "\n".join(result_lines),
                parent=self.root,
            )


def main() -> None:
    root = tk.Tk()
    RenamerApp(root)
    root.mainloop()
