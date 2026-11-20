import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path


class FileExplorer(ttk.Frame):
    FILTERS = ("All", "Folders_only", "imscc_only")

    def __init__(self, parent, start_path=None, filter="All", **kwargs):
        super().__init__(parent, **kwargs)

        self.filter = "All"
        self.imscc_folders = set()

        # Maps Treeview item IDs to filesystem paths.
        self.paths = {}

        self.tree = ttk.Treeview(
            self,
            columns=("type", "size"),
            show="tree headings"
        )

        self.tree.heading("#0", text="Name")
        self.tree.heading("type", text="Type")
        self.tree.heading("size", text="Size")

        self.tree.column("#0", width=300)
        self.tree.column("type", width=100)
        self.tree.column("size", width=100, anchor="e")

        scrollbar = ttk.Scrollbar(
            self,
            orient="vertical",
            command=self.tree.yview
        )

        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.tree.bind("<<TreeviewOpen>>", self._open_folder)
        self.tree.bind("<Double-1>", self._double_click)

        self.load(start_path, filter)

    def load(self, start_path=None, filter="All"):
        """Clear the tree and refill it, reusing the same widget."""
        if filter not in self.FILTERS:
            raise ValueError(f"filter must be one of {self.FILTERS}, got {filter!r}")
        self.filter = filter

        self.tree.delete(*self.tree.get_children())
        self.paths.clear()

        # Use the current working directory unless another path is supplied.
        start_path = Path(start_path or Path.cwd()).resolve()

        self.imscc_folders = set()
        if self.filter == "imscc_only":
            self.imscc_folders = self._find_imscc_folders(start_path)

        root_id = self._insert_path("", start_path)
        self.tree.item(root_id, open=True)
        # In imscc_only mode _insert_path already built and expanded the tree.
        if self.filter != "imscc_only":
            self._load_children(root_id, start_path)

    def _find_imscc_folders(self, start_path):
        # Collect every folder that has an .imscc file somewhere below it.
        folders = set()

        for current, dirnames, filenames in os.walk(start_path):
            # Skip hidden folders such as .git; they are slow to scan and irrelevant.
            dirnames[:] = [name for name in dirnames if not name.startswith(".")]

            if any(name.lower().endswith(".imscc") for name in filenames):
                folder = Path(current)
                while True:
                    folders.add(folder)
                    if folder == start_path:
                        break
                    folder = folder.parent

        return folders

    def _insert_path(self, parent, path):
        if path.is_dir():
            file_type = "Folder"
            size = ""
        else:
            file_type = path.suffix[1:].upper() or "File"

            try:
                size = self._format_size(path.stat().st_size)
            except OSError:
                size = ""

        item_id = self.tree.insert(
            parent,
            "end",
            text=path.name or str(path),
            values=(file_type, size)
        )

        self.paths[item_id] = path

        if path.is_dir():
            if self.filter == "imscc_only":
                # Fully expand so the user sees the .imscc files immediately.
                self._load_children(item_id, path)
                self.tree.item(item_id, open=True)
            else:
                # Add a placeholder so folders initially display an expand arrow.
                self.tree.insert(item_id, "end", text="Loading...")

        return item_id

    def _load_children(self, item_id, folder):
        # Remove any existing children, including the placeholder.
        self.tree.delete(*self.tree.get_children(item_id))

        try:
            children = sorted(
                folder.iterdir(),
                key=lambda path: (not path.is_dir(), path.name.lower())
            )
        except (PermissionError, OSError):
            return

        for path in children:
            if self._is_visible(path):
                self._insert_path(item_id, path)

    def _is_visible(self, path):
        if self.filter == "imscc_only":
            if path.is_dir():
                return path in self.imscc_folders
            return path.suffix.lower() == ".imscc"
        # Folders always stay visible so the whole tree can be navigated.
        if path.is_dir():
            return True
        return self.filter != "Folders_only"

    def selected_path(self):
        """Return the Path of the currently selected row, or None."""
        return self.paths.get(self.tree.focus())

    def reveal(self, path):
        """Expand the folders leading to path (and path itself), then select it.

        All other folders stay collapsed. Works with the lazily loaded tree.
        """
        root_id = self.tree.get_children()[0]

        try:
            parts = Path(path).resolve().relative_to(self.paths[root_id]).parts
        except ValueError:
            return

        item_id = root_id
        self._expand(item_id)
        for part in parts:
            item_id = next(
                (
                    child for child in self.tree.get_children(item_id)
                    if child in self.paths and self.paths[child].name == part
                ),
                None
            )
            if item_id is None:
                return
            self._expand(item_id)

        self.tree.selection_set(item_id)
        self.tree.focus(item_id)
        self.tree.see(item_id)

    def _expand(self, item_id):
        children = self.tree.get_children(item_id)

        # Only the "Loading..." placeholder is present until a folder is loaded.
        if children and all(child not in self.paths for child in children):
            self._load_children(item_id, self.paths[item_id])
        self.tree.item(item_id, open=True)

    def _open_folder(self, event=None):
        item_id = self.tree.focus()
        path = self.paths.get(item_id)

        # In imscc_only mode the tree is built up front, so there is nothing to load.
        if path and path.is_dir() and self.filter != "imscc_only":
            self._load_children(item_id, path)

    def _double_click(self, event=None):
        # Use the row under the cursor, not the focused row, so double-clicking
        # a header or empty space doesn't open the previously selected file.
        item_id = self.tree.identify_row(event.y) if event else self.tree.focus()
        path = self.paths.get(item_id)

        if path and path.is_file():
            self._open_file(path)

    @staticmethod
    def _open_file(path):
        # Launch the file with the OS's default application for its type.
        try:
            if sys.platform.startswith("win"):
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.run(["open", str(path)], check=True)
            else:
                subprocess.run(["xdg-open", str(path)], check=True)
        except (OSError, subprocess.SubprocessError) as error:
            messagebox.showerror("Cannot open file", f"{path}\n\n{error}")

    @staticmethod
    def _format_size(size):
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024

        return f"{size:.1f} PB"


# MAIN - run through all 3 cases (testing only)
if __name__ == "__main__":
    root = tk.Tk()
    root.title("File Explorer")
    root.geometry("700x500")

    project_dir = Path(__file__).resolve().parent

    explorer = FileExplorer(root, start_path=project_dir, filter="Folders_only")
    explorer.pack(fill="both", expand=True, padx=8, pady=8)

    # input() blocks Tk, so root.update() first to make the window draw.
    root.update()
    input("Case 1: Folders_only. Press Enter for the next case...")

    explorer.load(project_dir, "imscc_only")
    root.update()
    input("Case 2: imscc_only. Press Enter for the next case...")

    explorer.load(project_dir / "course_backup", "All")
    root.update()
    input("Case 3: All. Press Enter to quit...")

    root.destroy()