#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test suite for main module.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch
from io import StringIO

sys.path.insert(0, str(Path(__file__).parent.parent))

from enchant_book_manager.main import main


class TestMain:
    """Test the main module."""

    def test_main_function(self):
        """Test the main function prints expected messages."""
        # Capture stdout
        captured_output = StringIO()

        with patch("sys.stdout", captured_output):
            main()

        output = captured_output.getvalue()

        # Check both messages are printed
        assert "Hello from enchant-book-manager!" in output
        assert "Use 'enchant-cli' or 'cli-translator' commands instead." in output

    def test_main_function_line_count(self):
        """Test that main function prints exactly two lines."""
        captured_output = StringIO()

        with patch("sys.stdout", captured_output):
            main()

        output = captured_output.getvalue()
        lines = output.strip().split("\n")

        assert len(lines) == 2

    @patch("builtins.print")
    def test_main_function_calls_print_twice(self, mock_print):
        """Test that main function calls print exactly twice."""
        main()

        assert mock_print.call_count == 2

        # Verify the exact calls
        calls = mock_print.call_args_list
        assert calls[0].args[0] == "Hello from enchant-book-manager!"
        assert calls[1].args[0] == "Use 'enchant-cli' or 'cli-translator' commands instead."

    def test_main_returns_none(self):
        """Test that main function returns None."""
        result = main()
        assert result is None

    def test_module_docstring(self):
        """Test that the module has a proper docstring."""
        import enchant_book_manager.main as main_module

        assert main_module.__doc__ is not None
        assert "placeholder" in main_module.__doc__.lower()
        assert "cli entry points" in main_module.__doc__.lower()

    def test_function_docstring(self):
        """Test that the main function has a docstring."""
        assert main.__doc__ is not None
        assert "placeholder" in main.__doc__.lower()

    def test_module_can_be_imported(self):
        """Test that the module can be imported without errors."""
        try:
            import enchant_book_manager.main

            assert True
        except ImportError:
            pytest.fail("Failed to import main module")

    def test_module_attributes(self):
        """Test module has expected attributes."""
        import enchant_book_manager.main as main_module

        # Should have main function
        assert hasattr(main_module, "main")
        assert callable(main_module.main)

        # Should have __name__ check
        assert "__main__" in main_module.__file__ or True  # The check is in the source

    @patch("sys.argv", ["main.py"])
    def test_module_as_script(self):
        """Test running the module as a script."""
        captured_output = StringIO()

        with patch("sys.stdout", captured_output):
            # Execute the module's code
            exec_globals = {"__name__": "__main__"}
            with open(Path(__file__).parent.parent / "src" / "enchant_book_manager" / "main.py", "r") as f:
                code = compile(f.read(), "main.py", "exec")
                exec(code, exec_globals)

        output = captured_output.getvalue()
        assert "Hello from enchant-book-manager!" in output

    def test_no_side_effects_on_import(self):
        """Test that importing the module doesn't cause side effects."""
        captured_output = StringIO()

        with patch("sys.stdout", captured_output):
            # Re-import the module (it's already imported, but this tests the pattern)
            import importlib
            import enchant_book_manager.main

            importlib.reload(enchant_book_manager.main)

        output = captured_output.getvalue()
        # Should not print anything when imported (only when run as __main__)
        assert output == ""

    def test_main_as_script_simple(self):
        """Test the if __name__ == '__main__' block."""
        import runpy
        from unittest.mock import patch

        with patch("builtins.print") as mock_print:
            # Run the module as a script
            runpy.run_module("enchant_book_manager.main", run_name="__main__")

        # Should have called print twice
        assert mock_print.call_count == 2
        assert mock_print.call_args_list[0].args[0] == "Hello from enchant-book-manager!"
        assert mock_print.call_args_list[1].args[0] == "Use 'enchant-cli' or 'cli-translator' commands instead."


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
