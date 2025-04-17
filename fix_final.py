#!/usr/bin/env python3
"""
Final simple script to add a workflow summary at the end
- Handles both the main script and --summary-only option
"""

from pathlib import Path


def fix_get_errorlogs():
    # Path to the script
    script_path = Path('/Users/emanuelesabetta/Code/ENCHANT_BOOK_MANAGER/enchant_cli/get_errorlogs.sh')
    
    # Read the file content
    content = script_path.read_text()
    
    # Replace the --summary-only option code
    summary_only_section = """if [ "$1" = "--summary-only" ]; then
    # Get workflow stats but only display the summary
    get_workflow_stats
    display_workflow_summary
    exit 0
fi"""
    
    if "if [ \"$1\" = \"--summary-only\" ]" in content:
        start = content.find("if [ \"$1\" = \"--summary-only\" ]")
        end = content.find("fi", start) + 2
        content = content[:start] + summary_only_section + content[end:]
    
    # Add a call to display_workflow_summary at the end of the auto-detection block
    # This is a simpler way to make sure the summary appears at the end of that section
    auto_detect_section = """    # Fetch the workflow stats, show a summary, and exit
    # This ensures when run without arguments, we show a final summary
    get_workflow_stats
    display_workflow_summary
    exit 0
fi"""
    
    # Replace the section
    if "if [ $# -eq 0 ]" in content:
        start = content.find("if [ $# -eq 0 ]")
        auto_detect_start = content.find("{", start) + 1
        auto_detect_end = content.find("fi", auto_detect_start)
        content = content[:auto_detect_end] + auto_detect_section + content[auto_detect_end+2:]
    
    # Remove any duplicated summary at the end of script
    if "# No summary at the end" in content:
        start = content.find("# No summary at the end")
        end = content.find("exit 0", start)
        content = content[:start] + "exit 0" + content[end+6:]
    
    # Write the updated content back to the script
    script_path.write_text(content)
    
    return "Fixed get_errorlogs.sh to show a consistent summary"


if __name__ == "__main__":
    result = fix_get_errorlogs()
    print(result)