import os
import subprocess
import sys
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path


class FileExplorer(ttk.Frame):
    def __init__(self, parent, start_path=None, **kwargs):
        super().__init__(parent, **kwargs)

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

        # Use the current working directory unless another path is supplied.
        start_path = Path(start_path or Path.cwd()).resolve()

        root_id = self._insert_path("", start_path)
        self.tree.item(root_id, open=True)
        self._load_children(root_id, start_path)

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

        # Add a placeholder so folders initially display an expand arrow.
        if path.is_dir():
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
            self._insert_path(item_id, path)

    def _open_folder(self, event=None):
        item_id = self.tree.focus()
        path = self.paths.get(item_id)

        if path and path.is_dir():
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


root = tk.Tk()
root.title("File Explorer")
root.geometry("700x500")

# Path.cwd().resolve().parent is the folder from which the program was launched.
explorer = FileExplorer(
    root,
    start_path=Path(__file__).resolve().parent
)
explorer.pack(fill="both", expand=True, padx=8, pady=8)

root.mainloop()