"""Tests for notebook_tools module."""

import unittest
import json
from pathlib import Path
import tempfile
import shutil

from src.notebook_tools import (
    NotebookCell,
    NotebookReader,
    NotebookEditor,
    NotebookTools,
)


class TestNotebookTools(unittest.TestCase):
    """Test cases for notebook tools."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_dir = Path(tempfile.mkdtemp())

        # Create a minimal test notebook
        self.test_notebook = {
            "cells": [
                {
                    "cell_type": "code",
                    "source": ["print('hello')"],
                    "execution_count": 1,
                    "outputs": [],
                    "metadata": {},
                },
                {
                    "cell_type": "markdown",
                    "source": ["# Title"],
                    "metadata": {},
                },
            ],
            "metadata": {},
            "nbformat": 4,
        }

        self.notebook_path = self.test_dir / "test.ipynb"
        with open(self.notebook_path, "w") as f:
            json.dump(self.test_notebook, f)

    def tearDown(self):
        """Clean up test files."""
        shutil.rmtree(self.test_dir)

    def test_create_notebook_cell(self):
        """Test creating a notebook cell."""
        cell = NotebookCell(
            cell_type="code",
            source="print('test')",
            execution_count=1,
        )

        self.assertEqual(cell.cell_type, "code")
        self.assertEqual(cell.source, "print('test')")

    def test_notebook_reader_load(self):
        """Test loading a notebook."""
        reader = NotebookReader(self.notebook_path)
        notebook = reader.load()

        self.assertIn("cells", notebook)
        self.assertEqual(len(notebook["cells"]), 2)

    def test_notebook_reader_get_cells(self):
        """Test getting cells."""
        reader = NotebookReader(self.notebook_path)
        cells = reader.get_cells()

        self.assertEqual(len(cells), 2)
        self.assertEqual(cells[0].cell_type, "code")
        self.assertEqual(cells[1].cell_type, "markdown")

    def test_notebook_reader_get_cell(self):
        """Test getting a specific cell."""
        reader = NotebookReader(self.notebook_path)
        cell = reader.get_cell(0)

        self.assertIsNotNone(cell)
        self.assertEqual(cell.cell_type, "code")

    def test_notebook_reader_get_cell_invalid(self):
        """Test getting invalid cell."""
        reader = NotebookReader(self.notebook_path)
        cell = reader.get_cell(10)

        self.assertIsNone(cell)

    def test_notebook_reader_find_cells_by_type(self):
        """Test finding cells by type."""
        reader = NotebookReader(self.notebook_path)

        code_cells = reader.find_cells_by_type("code")
        self.assertEqual(len(code_cells), 1)

        markdown_cells = reader.find_cells_by_type("markdown")
        self.assertEqual(len(markdown_cells), 1)

    def test_notebook_reader_get_code_cells(self):
        """Test getting code cells."""
        reader = NotebookReader(self.notebook_path)
        cells = reader.get_code_cells()

        self.assertEqual(len(cells), 1)
        self.assertEqual(cells[0].cell_type, "code")

    def test_notebook_reader_get_markdown_cells(self):
        """Test getting markdown cells."""
        reader = NotebookReader(self.notebook_path)
        cells = reader.get_markdown_cells()

        self.assertEqual(len(cells), 1)
        self.assertEqual(cells[0].cell_type, "markdown")

    def test_notebook_editor_add_cell(self):
        """Test adding a cell."""
        editor = NotebookEditor(self.notebook_path)
        editor.add_cell("code", "x = 1")

        cells = editor.reader.get_cells()
        self.assertEqual(len(cells), 3)
        self.assertEqual(cells[2].source, "x = 1")

    def test_notebook_editor_add_cell_at_index(self):
        """Test adding cell at specific index."""
        editor = NotebookEditor(self.notebook_path)
        editor.add_cell("markdown", "## Section", index=0)

        cells = editor.reader.get_cells()
        self.assertEqual(len(cells), 3)
        self.assertEqual(cells[0].source, "## Section")

    def test_notebook_editor_update_cell(self):
        """Test updating a cell."""
        editor = NotebookEditor(self.notebook_path)
        result = editor.update_cell(0, "print('updated')")

        self.assertTrue(result)
        cells = editor.reader.get_cells()
        self.assertEqual(cells[0].source, "print('updated')")

    def test_notebook_editor_update_cell_invalid(self):
        """Test updating invalid cell."""
        editor = NotebookEditor(self.notebook_path)
        result = editor.update_cell(10, "test")

        self.assertFalse(result)

    def test_notebook_editor_delete_cell(self):
        """Test deleting a cell."""
        editor = NotebookEditor(self.notebook_path)
        result = editor.delete_cell(0)

        self.assertTrue(result)
        cells = editor.reader.get_cells()
        self.assertEqual(len(cells), 1)

    def test_notebook_editor_delete_cell_invalid(self):
        """Test deleting invalid cell."""
        editor = NotebookEditor(self.notebook_path)
        result = editor.delete_cell(10)

        self.assertFalse(result)

    def test_notebook_editor_move_cell(self):
        """Test moving a cell."""
        editor = NotebookEditor(self.notebook_path)
        result = editor.move_cell(0, 1)

        self.assertTrue(result)
        cells = editor.reader.get_cells()
        self.assertEqual(cells[0].cell_type, "markdown")
        self.assertEqual(cells[1].cell_type, "code")

    def test_notebook_editor_clear_outputs(self):
        """Test clearing outputs."""
        editor = NotebookEditor(self.notebook_path)
        editor.clear_outputs()

        cells = editor.reader.get_cells()
        code_cells = [c for c in cells if c.cell_type == "code"]

        for cell in code_cells:
            self.assertIsNone(cell.execution_count)
            self.assertEqual(cell.outputs, [])

    def test_notebook_editor_save(self):
        """Test saving notebook."""
        editor = NotebookEditor(self.notebook_path)
        editor.add_cell("code", "test = 1")
        editor.save()

        # Reload and verify
        with open(self.notebook_path) as f:
            saved = json.load(f)

        self.assertEqual(len(saved["cells"]), 3)

    def test_notebook_tools_read_notebook(self):
        """Test reading notebook with tools."""
        notebook = NotebookTools.read_notebook(self.notebook_path)

        self.assertIn("cells", notebook)
        self.assertEqual(len(notebook["cells"]), 2)

    def test_notebook_tools_list_cells(self):
        """Test listing cells with tools."""
        cells = NotebookTools.list_cells(self.notebook_path)

        self.assertEqual(len(cells), 2)
        self.assertIn("index", cells[0])
        self.assertIn("type", cells[0])

    def test_notebook_tools_add_cell(self):
        """Test adding cell with tools."""
        NotebookTools.add_cell_to_notebook(
            self.notebook_path, "code", "x = 42"
        )

        reader = NotebookReader(self.notebook_path)
        cells = reader.get_cells()

        self.assertEqual(len(cells), 3)
        self.assertEqual(cells[2].source, "x = 42")


if __name__ == "__main__":
    unittest.main()
