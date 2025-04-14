import pytest
import os
import sys
from click.testing import CliRunner
from pathlib import Path
from unittest.mock import patch, MagicMock, ANY
import logging

# Add src directory to Python path
SRC_DIR = str(Path(__file__).parent.parent / "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

# Import CLI main function and version
from enchant_cli.enchant_cli import main as cli_main
from enchant_cli import __version__
from enchant_cli.translation_service import OPENROUTER_API_KEY # Check if API key is set

# Marker for tests requiring the API key (for potential integration tests later)
needs_api_key = pytest.mark.skipif(
    not OPENROUTER_API_KEY,
    reason="Requires OPENROUTER_API_KEY environment variable"
)

# --- Fixtures ---

@pytest.fixture
def runner():
    """Provides a Click test runner."""
    return CliRunner()

@pytest.fixture
def mock_translator():
    """Mocks the ChineseAITranslator class."""
    # Set TEST_ENV to ensure test configuration is used if translator is instantiated
    os.environ["TEST_ENV"] = "true"
    with patch('enchant_cli.enchant_cli.ChineseAITranslator', autospec=True) as mock_class:
        # Configure the mock instance that will be created
        mock_instance = mock_class.return_value
        # Mock the main translate method to return predictable output and cost
        mock_instance.translate.return_value = ("Mocked translation", 0.001)
        yield mock_instance # Yield the mock *instance* for assertions
    # Clean up environment variable
    if "TEST_ENV" in os.environ:
        del os.environ["TEST_ENV"]

@pytest.fixture(autouse=True)
def setup_logging(caplog):
    """Ensure logs are captured at DEBUG level for all tests."""
    caplog.set_level(logging.DEBUG)

# --- Basic CLI Tests ---

def test_cli_version(runner):
    """Test the --version option."""
    result = runner.invoke(cli_main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output
    assert "enchant_cli" in result.output.lower()

def test_cli_help(runner):
    """Test the --help option."""
    result = runner.invoke(cli_main, ["--help"])
    assert result.exit_code == 0
    assert "Usage: enchant_cli" in result.output # Check for correct program name
    assert "--batch" in result.output
    assert "--max-chars" in result.output
    assert "--output" in result.output

def test_cli_missing_filepath(runner):
    """Test calling CLI without the required filepath argument."""
    result = runner.invoke(cli_main)
    assert result.exit_code != 0
    assert "Missing argument 'FILEPATH'" in result.output

def test_cli_nonexistent_filepath(runner):
    """Test calling CLI with a filepath that does not exist."""
    result = runner.invoke(cli_main, ["nonexistent_file.txt"])
    assert result.exit_code != 0
    assert "Invalid value for 'FILEPATH'" in result.output
    assert "does not exist" in result.output

# --- Single File Translation Tests (Mocked) ---

def test_cli_single_file_success(runner, tmp_path, mock_translator):
    """Test successful single file translation using mocked translator."""
    input_content = "你好世界"
    input_file = tmp_path / "input.txt"
    output_file = tmp_path / "output.txt"
    input_file.write_text(input_content, encoding='utf-8')

    result = runner.invoke(cli_main, [str(input_file), "-o", str(output_file)])

    assert result.exit_code == 0, f"CLI failed with output:\n{result.output}"
    assert "Book imported successfully." in result.output
    assert f"Output will be saved to: {output_file}" in result.output
    assert f"Translated book saved successfully to {output_file}" in result.output
    assert "$0.001000" in result.output # Check cost from mock (less strict check for table format)

    # Verify translator was called correctly
    mock_translator.translate.assert_called()
    # Check if the first argument passed to translate contains the input content
    # Note: The actual call might be on a processed/split version of the content
    # This basic check verifies it was called at least once.
    # For more detailed checks, inspect call_args_list.

    # Verify output file content
    assert output_file.exists()
    assert output_file.read_text(encoding='utf-8') == "\nMocked translation\n" # Mock adds newline

def test_cli_single_file_default_output(runner, tmp_path, mock_translator):
    """Test single file translation using the default output filename."""
    input_content = "你好"
    input_file = tmp_path / "test.txt"
    default_output_file = Path.cwd() / "translated_test.txt" # Default location
    input_file.write_text(input_content, encoding='utf-8')

    # Ensure default output file doesn't exist before test
    if default_output_file.exists():
        default_output_file.unlink()

    result = runner.invoke(cli_main, [str(input_file)])

    assert result.exit_code == 0
    assert f"Output will be saved to: {default_output_file}" in result.output
    assert default_output_file.exists()
    assert default_output_file.read_text(encoding='utf-8') == "\nMocked translation\n" # Expect leading newline

    # Clean up the default output file
    default_output_file.unlink()

def test_cli_single_file_verbose(runner, tmp_path, mock_translator, caplog):
    """Test verbose flag enables DEBUG logging."""
    input_content = "你好"
    input_file = tmp_path / "input_v.txt"
    output_file = tmp_path / "output_v.txt"
    input_file.write_text(input_content, encoding='utf-8')

    result = runner.invoke(cli_main, [str(input_file), "-o", str(output_file), "--verbose"])

    assert result.exit_code == 0
    assert "DEBUG" in caplog.text
    # Check for specific debug messages from CLI or translator init
    assert "CLI Arguments:" in caplog.text or "Initializing ChineseAITranslator" in caplog.text

def test_cli_single_file_double_translate(runner, tmp_path, mock_translator):
    """Test --double-translate flag is passed to the translator."""
    input_content = "你好"
    input_file = tmp_path / "input_d.txt"
    output_file = tmp_path / "output_d.txt"
    input_file.write_text(input_content, encoding='utf-8')

    result = runner.invoke(cli_main, [str(input_file), "-o", str(output_file), "--double-translate"])

    assert result.exit_code == 0
    # Verify the translate method was called with double_translation=True
    mock_translator.translate.assert_called_with(ANY, double_translation=True, is_last_chunk=ANY)

def test_cli_single_file_max_chars(runner, tmp_path, mock_translator, caplog):
    """Test --max-chars option influences splitting (indirectly tested)."""
    # We can't easily assert the exact splitting, but we can check the option is parsed.
    input_content = "你好世界，这是一个较长的句子，用于测试分块。" * 10
    input_file = tmp_path / "input_mc.txt"
    output_file = tmp_path / "output_mc.txt"
    input_file.write_text(input_content, encoding='utf-8')

    # Reset side_effect to default behavior (always returns "Mocked translation", 0.001)
    # The default is set in the mock_translator fixture.
    mock_translator.translate.side_effect = None
    # Set side_effect to return different costs for different calls if needed
    # For this test, we assume 3 chunks based on the input and max_chars=100
    # Let's make the mock return the same thing but allow us to check call count
    mock_translator.translate.return_value = ("Mocked translation", 0.001)


    result = runner.invoke(cli_main, [str(input_file), "-o", str(output_file), "--max-chars", "100", "--verbose"]) # Add verbose to check logs

    assert result.exit_code == 0
    # Check if multiple chapters/chunks were processed (indicated by multiple calls or logs)
    # If translate is called multiple times, it suggests splitting occurred.
    # The exact number depends on the splitting logic, let's assume it's > 1
    assert mock_translator.translate.call_count > 1
    # Check logs for chapter processing messages
    # Since all chunks return the same mock, just check for that
    assert "Mocked translation" in output_file.read_text(encoding='utf-8')
    assert mock_translator.translate.call_count > 1 # Verify splitting happened
    assert "TRANSLATING CHAPTER 1" in caplog.text # Check log output
    assert "TRANSLATING CHAPTER 2" in caplog.text # Check log output
    # Calculate expected cost based on actual calls
    expected_cost = mock_translator.translate.call_count * 0.001
    # Check for the cost value within the output, ignoring surrounding table chars
    assert f"${expected_cost:.6f}" in result.output # Check the specific cost value appears

def test_cli_single_file_split_mode(runner, tmp_path, mock_translator, caplog):
    """Test --split-mode option."""
    input_content = "你好。\n第二行。"
    input_file = tmp_path / "input_sm.txt"
    output_file = tmp_path / "output_sm.txt"
    input_file.write_text(input_content, encoding='utf-8')

    result = runner.invoke(cli_main, [
        str(input_file),
        "-o", str(output_file),
        "--split-mode", "SPLIT_POINTS", # Use non-default
        "--verbose" # To check logs
    ])

    assert result.exit_code == 0
    # Check logs or debug output to confirm the split mode was used if possible
    # This might require adding specific logging in the main script's import/split logic
    assert "split_mode=SPLIT_POINTS" in caplog.text

# --- Batch Mode Tests (Mocked) ---

def test_cli_batch_success(runner, tmp_path, mock_translator):
    """Test successful batch processing of multiple files."""
    input_dir = tmp_path / "batch_in"
    output_dir = tmp_path / "batch_out"
    input_dir.mkdir()
    output_dir.mkdir() # Create output dir explicitly for clarity

    file1 = input_dir / "file1.txt"
    file2 = input_dir / "file2_测试.txt"
    non_txt_file = input_dir / "ignore.md"
    file1.write_text("内容一", encoding='utf-8')
    file2.write_text("内容二", encoding='utf-8')
    non_txt_file.write_text("Markdown", encoding='utf-8')

    result = runner.invoke(cli_main, ["--batch", str(input_dir), "-o", str(output_dir)])

    assert result.exit_code == 0, f"CLI failed with output:\n{result.output}"
    # assert f"Found 2 .txt files in '{input_dir}'" in result.output # This is logged, not printed
    # assert f"Output directory set to: {output_dir}" in result.output # This is logged, not printed
    assert "Processing file: file1.txt" in result.output
    assert "Processing file: file2_测试.txt" in result.output
    assert "ignore.md" not in result.output # Should ignore non-txt
    assert "Batch Processing Summary" in result.output
    assert "Processed: 2" in result.output
    assert "Skipped:   0" in result.output # Assuming import doesn't fail
    assert "Failed:    0" in result.output

    # Verify translator calls (one per chunk per file)
    # Exact count depends on splitting, but should be >= 2
    assert mock_translator.translate.call_count >= 2

    # Verify output files (names might be complex due to parsing)
    # Check for *any* .txt files in the output dir
    output_files = list(output_dir.glob("*.txt"))
    assert len(output_files) == 2 # Should only have the combined files now
    for f in output_files:
        assert f.read_text(encoding='utf-8') == "\nMocked translation\n"

def test_cli_batch_default_output_dir(runner, tmp_path, mock_translator):
    """Test batch processing using the default output directory."""
    input_dir = tmp_path / "batch_in_default"
    default_output_dir = input_dir / "translated"
    input_dir.mkdir()

    file1 = input_dir / "file_a.txt"
    file1.write_text("内容A", encoding='utf-8')

    result = runner.invoke(cli_main, ["--batch", str(input_dir)]) # No -o option

    assert result.exit_code == 0
    # assert f"Output directory set to: {default_output_dir}" in result.output # This is logged, not printed
    assert default_output_dir.exists()
    assert default_output_dir.is_dir()

    # Check output file exists within the default directory
    output_files = list(default_output_dir.glob("*.txt"))
    assert len(output_files) == 1 # Should only have the combined file now
    assert output_files[0].read_text(encoding='utf-8') == "\nMocked translation\n"

def test_cli_batch_empty_dir(runner, tmp_path, mock_translator):
    """Test batch processing with an empty input directory."""
    input_dir = tmp_path / "batch_empty"
    input_dir.mkdir()

    result = runner.invoke(cli_main, ["--batch", str(input_dir)])

    assert result.exit_code == 0
    assert "No .txt files found" in result.output
    assert "Batch Processing Summary" not in result.output # Summary might not show if nothing processed
    assert mock_translator.translate.call_count == 0 # Translator should not be called

def test_cli_batch_with_failed_import(runner, tmp_path, mock_translator):
    """Test batch processing where one file fails to import."""
    input_dir = tmp_path / "batch_fail"
    output_dir = tmp_path / "batch_fail_out"
    input_dir.mkdir()
    output_dir.mkdir()

    file_ok = input_dir / "good.txt"
    file_bad = input_dir / "bad.txt" # Simulate failure for this one
    file_ok.write_text("好的内容", encoding='utf-8')
    file_bad.write_text("坏的内容", encoding='utf-8')

    # Patch import_book_from_txt to simulate failure for 'bad.txt'
    with patch('enchant_cli.enchant_cli.import_book_from_txt') as mock_import:
        def side_effect(file_path, **kwargs):
            if "bad.txt" in str(file_path):
                return None # Simulate import failure
            else:
                # Simulate successful import returning a dummy book_id
                return f"book_id_{Path(file_path).stem}"
        mock_import.side_effect = side_effect

        # Also mock save_translated_book to avoid the "Book not found" error
        with patch('enchant_cli.enchant_cli.save_translated_book', return_value=0.001) as mock_save:
            result = runner.invoke(cli_main, ["--batch", str(input_dir), "-o", str(output_dir)])

        assert result.exit_code == 0 # Batch should continue on single file failure
        assert "Processing file: good.txt" in result.output
        assert "Error processing good.txt" not in result.output # Ensure save wasn't the failure point
        assert "Processing file: bad.txt" in result.output
        assert "Skipping file bad.txt: Import failed." in result.output
        assert "Batch Processing Summary" in result.output
        assert "Processed: 1" in result.output
        assert "Skipped:   1" in result.output
        assert "Failed:    0" in result.output # Failure was skipped, not failed processing

        # Verify save was called only once (for the successful import)
        mock_save.assert_called_once()

        # Verify only output for the successful file exists (save is mocked, so check call args)
        output_files = list(output_dir.glob("*.txt"))
        assert len(output_files) == 0 # Mocked save doesn't create files
        assert "good" in mock_save.call_args[0][1] # Check output filename passed to mock_save

# --- Error Handling Tests ---

def test_cli_batch_flag_with_file_input(runner, tmp_path):
    """Test error when --batch is used but input is a file."""
    input_file = tmp_path / "not_a_dir.txt"
    input_file.touch()
    result = runner.invoke(cli_main, ["--batch", str(input_file)])
    assert result.exit_code != 0
    assert "Error: --batch flag requires 'filepath' to be a directory" in result.output

def test_cli_no_batch_flag_with_dir_input(runner, tmp_path):
    """Test error when input is a directory but --batch is missing."""
    input_dir = tmp_path / "is_a_dir"
    input_dir.mkdir()
    result = runner.invoke(cli_main, [str(input_dir)])
    assert result.exit_code != 0
    assert "Error: Expected 'filepath' to be a file" in result.output
    assert "(use --batch for directories)" in result.output

def test_cli_batch_output_is_file(runner, tmp_path):
    """Test error when --batch is used but --output is an existing file."""
    input_dir = tmp_path / "batch_in_err"
    output_file = tmp_path / "output_is_file.txt"
    input_dir.mkdir()
    output_file.touch() # Create the file

    result = runner.invoke(cli_main, ["--batch", str(input_dir), "-o", str(output_file)])
    assert result.exit_code != 0
    assert "Error: In batch mode, --output must be a directory" in result.output

def test_cli_single_output_is_dir(runner, tmp_path):
    """Test error when single file mode but --output is an existing directory."""
    input_file = tmp_path / "input_err.txt"
    output_dir = tmp_path / "output_is_dir"
    input_file.touch()
    output_dir.mkdir() # Create the directory

    result = runner.invoke(cli_main, [str(input_file), "-o", str(output_dir)])
    assert result.exit_code != 0
    assert "Error: In single file mode, --output must be a file path" in result.output

def test_cli_translator_init_failure(runner, tmp_path, monkeypatch):
    """Test CLI exit if translator initialization fails."""
    input_file = tmp_path / "input.txt"
    input_file.touch()

    # Mock translator __init__ to raise an exception
    with patch('enchant_cli.enchant_cli.ChineseAITranslator.__init__', side_effect=ValueError("API Key Missing")):
        result = runner.invoke(cli_main, [str(input_file)])

    assert result.exit_code != 0
    assert "Error: Failed to initialize translator: API Key Missing" in result.output

def test_cli_translation_failure_in_save(runner, tmp_path, mock_translator):
    """Test CLI behavior when translator.translate raises an exception during save."""
    input_content = "你好"
    input_file = tmp_path / "input_fail.txt"
    output_file = tmp_path / "output_fail.txt"
    input_file.write_text(input_content, encoding='utf-8')

    # Make the mock translator raise an error (simulate critical failure)
    # The translate method itself returns empty string / 0 cost on failure
    # We need save_translated_book to return None
    with patch('enchant_cli.enchant_cli.save_translated_book', return_value=None) as mock_save:
        result = runner.invoke(cli_main, [str(input_file), "-o", str(output_file), "--verbose"])

    # The main loop catches the None return value from save_translated_book
    assert result.exit_code == 1 # Should exit with error code
    assert "Critical error during translation or saving" in result.output
    assert not output_file.exists() # Output file should likely not be created or be empty
