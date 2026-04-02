"""
Notebook-friendly tool chain for Jupyter integration.

Provides functionality to:
- Read Jupyter notebooks (.ipynb files)
- Edit notebook cells
- Execute notebook cells
- Manage kernel sessions
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class NotebookCell:
    """Jupyter notebook cell."""

    cell_type: str  # "code", "markdown", "raw"
    source: str
    execution_count: int | None = None
    outputs: list[dict[str, Any]] | None = None
    metadata: dict[str, Any] | None = None


class NotebookReader:
    """Reads Jupyter notebooks."""

    def __init__(self, path: Path | str):
        """
        Initialize notebook reader.

        Args:
            path: Path to .ipynb file
        """
        self.path = Path(path)
        self._notebook: dict[str, Any] | None = None

    def load(self) -> dict[str, Any]:
        """Load notebook from file."""
        with open(self.path) as f:
            self._notebook = json.load(f)
        return self._notebook

    @property
    def notebook(self) -> dict[str, Any]:
        """Get loaded notebook."""
        if self._notebook is None:
            self.load()
        return self._notebook or {}

    def get_cells(self) -> list[NotebookCell]:
        """Get all cells."""
        cells = []
        for i, cell_data in enumerate(self.notebook.get("cells", [])):
            cell = NotebookCell(
                cell_type=cell_data.get("cell_type", "code"),
                source="".join(cell_data.get("source", [])),
                execution_count=cell_data.get("execution_count"),
                outputs=cell_data.get("outputs"),
                metadata=cell_data.get("metadata"),
            )
            cells.append(cell)

        return cells

    def get_cell(self, index: int) -> NotebookCell | None:
        """Get cell by index."""
        cells = self.get_cells()
        if 0 <= index < len(cells):
            return cells[index]
        return None

    def find_cells_by_type(self, cell_type: str) -> list[NotebookCell]:
        """Find cells by type."""
        return [cell for cell in self.get_cells() if cell.cell_type == cell_type]

    def get_code_cells(self) -> list[NotebookCell]:
        """Get all code cells."""
        return self.find_cells_by_type("code")

    def get_markdown_cells(self) -> list[NotebookCell]:
        """Get all markdown cells."""
        return self.find_cells_by_type("markdown")


class NotebookEditor:
    """Edits Jupyter notebooks."""

    def __init__(self, path: Path | str):
        """
        Initialize notebook editor.

        Args:
            path: Path to .ipynb file
        """
        self.path = Path(path)
        self.reader = NotebookReader(path)
        self._modified = False

    def load(self) -> None:
        """Load notebook."""
        self.reader.load()

    def save(self) -> None:
        """Save notebook to file."""
        if self.reader._notebook is None:
            return

        with open(self.path, "w") as f:
            json.dump(self.reader._notebook, f, indent=1)

        self._modified = False

    def add_cell(
        self,
        cell_type: str,
        source: str,
        index: int | None = None,
    ) -> None:
        """
        Add a new cell.

        Args:
            cell_type: Cell type ("code", "markdown", "raw")
            source: Cell source code
            index: Optional index to insert at (appends if None)
        """
        if self.reader._notebook is None:
            self.load()

        cell_data = {
            "cell_type": cell_type,
            "source": [source],
            "metadata": {},
        }

        if cell_type == "code":
            cell_data["execution_count"] = None
            cell_data["outputs"] = []

        cells = self.reader._notebook.get("cells", [])

        if index is not None:
            cells.insert(index, cell_data)
        else:
            cells.append(cell_data)

        self.reader._notebook["cells"] = cells
        self._modified = True

    def update_cell(self, index: int, source: str) -> bool:
        """
        Update cell source.

        Args:
            index: Cell index
            source: New source code

        Returns:
            True if cell was updated
        """
        if self.reader._notebook is None:
            self.load()

        cells = self.reader._notebook.get("cells", [])

        if 0 <= index < len(cells):
            cells[index]["source"] = [source]
            self.reader._notebook["cells"] = cells
            self._modified = True
            return True

        return False

    def delete_cell(self, index: int) -> bool:
        """
        Delete a cell.

        Args:
            index: Cell index

        Returns:
            True if cell was deleted
        """
        if self.reader._notebook is None:
            self.load()

        cells = self.reader._notebook.get("cells", [])

        if 0 <= index < len(cells):
            cells.pop(index)
            self.reader._notebook["cells"] = cells
            self._modified = True
            return True

        return False

    def move_cell(self, from_index: int, to_index: int) -> bool:
        """
        Move a cell to a new position.

        Args:
            from_index: Current cell index
            to_index: Target cell index

        Returns:
            True if cell was moved
        """
        if self.reader._notebook is None:
            self.load()

        cells = self.reader._notebook.get("cells", [])

        if 0 <= from_index < len(cells) and 0 <= to_index < len(cells):
            cell = cells.pop(from_index)
            cells.insert(to_index, cell)
            self.reader._notebook["cells"] = cells
            self._modified = True
            return True

        return False

    def clear_outputs(self) -> None:
        """Clear all cell outputs."""
        if self.reader._notebook is None:
            self.load()

        cells = self.reader._notebook.get("cells", [])

        for cell in cells:
            if cell.get("cell_type") == "code":
                cell["execution_count"] = None
                cell["outputs"] = []

        self.reader._notebook["cells"] = cells
        self._modified = True


class NotebookTools:
    """Collection of notebook tools."""

    @staticmethod
    def read_notebook(path: Path | str) -> dict[str, Any]:
        """
        Read a notebook file.

        Args:
            path: Path to notebook

        Returns:
            Notebook data
        """
        reader = NotebookReader(path)
        return reader.notebook

    @staticmethod
    def list_cells(path: Path | str) -> list[dict[str, Any]]:
        """
        List notebook cells.

        Args:
            path: Path to notebook

        Returns:
            List of cell information
        """
        reader = NotebookReader(path)
        cells = reader.get_cells()

        return [
            {
                "index": i,
                "type": cell.cell_type,
                "source": cell.source[:100],  # Preview
                "execution_count": cell.execution_count,
            }
            for i, cell in enumerate(cells)
        ]

    @staticmethod
    def add_cell_to_notebook(
        path: Path | str,
        cell_type: str,
        source: str,
        index: int | None = None,
    ) -> None:
        """
        Add a cell to notebook.

        Args:
            path: Path to notebook
            cell_type: Cell type
            source: Cell source
            index: Optional index
        """
        editor = NotebookEditor(path)
        editor.add_cell(cell_type, source, index)
        editor.save()
