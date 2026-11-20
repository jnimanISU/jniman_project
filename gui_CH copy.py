from pathlib import Path
from tkinter import Tk, messagebox, ttk

from main_CH import run_backup_process
from treeview import FileExplorer


class CanvasBackupApp(Tk):
    """Tkinter GUI: 1) pick output folder, 2) pick .imscc file, 3) show results."""

    STEP1_TEXT = "Step 1: select the output folder, then click Next"
    STEP2_TEXT = "Step 2: select an .imscc file, then click Next"

    def __init__(self):
        super().__init__()
        self.title("Canvas Backup Tool")
        self.geometry("700x550")

        self.step = 1
        self.output_dir = None
        self.project_dir = Path(__file__).resolve().parent

        self.create_widgets()

    def create_widgets(self):
        #header: status text with the Next/Start over button to its right
        header = ttk.Frame(self)
        header.pack(fill="x", padx=8, pady=4)
        header.columnconfigure(0, weight=1)

        self.status_label = ttk.Label(header, text=self.STEP1_TEXT)
        self.status_label.grid(row=0, column=0, sticky="w")
        self.folder_label = ttk.Label(header, text="")
        self.folder_label.grid(row=1, column=0, sticky="w")
        self.imscc_label = ttk.Label(header, text="")
        self.imscc_label.grid(row=2, column=0, sticky="w")

        self.next_button = ttk.Button(header, text="Next", command=self.on_next)
        self.next_button.grid(row=0, column=1, rowspan=3, sticky="e", padx=(8, 0))

        self.explorer = FileExplorer(
            self, start_path=self.project_dir, filter="Folders_only"
        )
        self.explorer.pack(fill="both", expand=True, padx=8, pady=8)

    def project_path(self, path):
        """Display a path starting at the project root folder name."""
        return str(Path(self.project_dir.name) / path.relative_to(self.project_dir))

    def start_over(self):
        self.step = 1
        self.output_dir = None
        self.explorer.load(self.project_dir, "Folders_only")
        self.status_label.config(text=self.STEP1_TEXT)
        self.folder_label.config(text="")
        self.imscc_label.config(text="")
        self.next_button.config(text="Next")

    def on_next(self):
        """Advance to the next step, or start over after the backup is done."""
        if self.step == 3:
            self.start_over()
            return

        selected = self.explorer.selected_path()
        if selected is None:
            messagebox.showwarning("Nothing selected", "Please select an item.")
            return

        if self.step == 1:
            self.choose_output_folder(selected)
        elif self.step == 2:
            self.run_backup(selected)

    def choose_output_folder(self, folder):
        if not folder.is_dir():
            messagebox.showwarning("Not a folder", "Please select a folder.")
            return

        self.output_dir = folder
        self.folder_label.config(text=f"Folder: {self.project_path(folder)}")
        #list every .imscc file in the project, not just inside the chosen folder
        self.explorer.load(self.project_dir, "imscc_only")
        self.status_label.config(text=self.STEP2_TEXT)
        self.step = 2

    def run_backup(self, imscc_file):
        if imscc_file.suffix.lower() != ".imscc":
            messagebox.showwarning(
                "Not an .imscc file", "Please select an .imscc file."
            )
            return

        self.status_label.config(text="Processing backup... Please wait.")
        self.update()

        try:
            results = run_backup_process(str(imscc_file), str(self.output_dir))
        except Exception as error:
            self.status_label.config(text=self.STEP2_TEXT)
            messagebox.showerror("Backup failed", str(error))
            return

        self.imscc_label.config(text=f"Imscc file: {self.project_path(imscc_file)}")
        self.explorer.load(self.project_dir, "All")
        self.explorer.reveal(self.output_dir)
        self.status_label.config(
            text=f"Done: {results['modules_count']} modules, "
                 f"{results['files_copied']} files copied."
        )
        self.next_button.config(text="Start over")
        self.step = 3


if __name__ == "__main__":
    app = CanvasBackupApp()
    app.mainloop()
