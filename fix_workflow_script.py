#!/usr/bin/env python
"""
Simple, direct script to fix get_errorlogs.sh
"""

def fix_script():
    script_path = "/Users/emanuelesabetta/Code/ENCHANT_BOOK_MANAGER/enchant_cli/get_errorlogs.sh"
    
    with open(script_path, 'r') as file:
        content = file.read()
    
    # Create a clean display_workflow_summary function
    display_function = """
# Function to display workflow summary
display_workflow_summary() {
    echo ""
    echo -e "\\033[1;33m🔶 WORKFLOW SUMMARY 🔶\\033[0m"
    if [ -n "\$recent_failure_count" ] && [ "\$recent_failure_count" -gt 0 ]; then
        echo -e "\\033[1;31m❌ GITHUB JOBS SUMMARY: \$recent_success_count/\$all_runs_count WORKFLOWS COMPLETED SUCCESSFULLY, \$recent_failure_count WITH ERRORS\\033[0m"
    else
        echo -e "\\033[1;32m✅ GITHUB JOBS COMPLETED SUCCESSFULLY\\033[0m"
    fi
}
"""
    
    # Find a good place to insert our function - before the Constants section
    constants_pos = content.find("# Constants for log settings")
    if constants_pos > 0:
        content = content[:constants_pos] + display_function + "\n" + content[constants_pos:]
    
    # Now fix the summary-only option
    summary_only_section = """if [ "$1" = "--summary-only" ]; then
    # Get workflow stats but only display the summary
    get_workflow_stats
    display_workflow_summary
    exit 0
fi
"""
    
    # Find and replace the summary-only section
    summary_start = content.find('if [ "$1" = "--summary-only" ]')
    if summary_start > 0:
        summary_end = content.find("fi", summary_start) + 2
        content = content[:summary_start] + summary_only_section + content[summary_end:]
    
    # Add display_workflow_summary call to the auto-detection section
    auto_detection_text = """    # Show workflow files with YAML syntax errors
    if [ -n "$yaml_errors" ] && [ "$yaml_errors" -gt 0 ]; then
        print_warning "Found $yaml_errors workflow files with YAML syntax errors"
        # Add to failure count
        recent_failure_count=$((recent_failure_count + yaml_errors))
    fi
    
    # Show the summary and exit
    display_workflow_summary
    exit 0"""
    
    # Find the YAML errors section and add our summary call
    yaml_errors_pos = content.find('if [ -n "$yaml_errors" ] && [ "$yaml_errors" -gt 0 ]')
    if yaml_errors_pos > 0:
        # Find the end of this section
        section_end = content.find("fi", yaml_errors_pos) + 2
        content = content[:yaml_errors_pos] + auto_detection_text + content[section_end:]
    
    # Remove any duplicate summary code at the end
    end_pattern_start = content.rfind("# Add single final status summary")
    if end_pattern_start > 0:
        end_pattern_end = content.find("exit 0", end_pattern_start)
        if end_pattern_end > 0:
            content = content[:end_pattern_start] + "exit 0" + content[end_pattern_end+6:]
    
    # Clean up any remaining summary text at end of script
    no_summary_start = content.rfind("# No summary at the end")
    if no_summary_start > 0:
        no_summary_end = content.find("exit 0", no_summary_start)
        if no_summary_end > 0:
            content = content[:no_summary_start] + "exit 0" + content[no_summary_end+6:]
    
    # Write the updated content back to the file
    with open(script_path, 'w') as file:
        file.write(content)
    
    print("Script successfully updated.")

if __name__ == "__main__":
    fix_script()