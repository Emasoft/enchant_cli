#!/usr/bin/env python
"""
Fix the integer comparison issue with recent_failure_count
"""

def fix_script():
    script_path = "/Users/emanuelesabetta/Code/ENCHANT_BOOK_MANAGER/enchant_cli/get_errorlogs.sh"
    
    with open(script_path, "r") as file:
        content = file.read()
    
    # Fix the display_workflow_summary function to handle null/empty values
    display_function = """
# Function to display workflow summary
display_workflow_summary() {
    echo ""
    echo -e "\\033[1;33m🔶 WORKFLOW SUMMARY 🔶\\033[0m"
    
    # Ensure variables are initialized
    recent_failure_count=${recent_failure_count:-0}
    recent_success_count=${recent_success_count:-0}
    all_runs_count=${all_runs_count:-0}
    
    if [ "$recent_failure_count" -gt 0 ]; then
        echo -e "\\033[1;31m❌ GITHUB JOBS SUMMARY: $recent_success_count/$all_runs_count WORKFLOWS COMPLETED SUCCESSFULLY, $recent_failure_count WITH ERRORS\\033[0m"
    else
        echo -e "\\033[1;32m✅ GITHUB JOBS COMPLETED SUCCESSFULLY\\033[0m"
    fi
}
"""
    
    # Replace the existing display_workflow_summary function
    start = content.find("# Function to display workflow summary")
    if start > 0:
        end = content.find("}", start) + 1
        content = content[:start] + display_function.strip() + content[end:]
    
    # Write the updated content back to the file
    with open(script_path, "w") as file:
        file.write(content)
    
    print("Fixed integer comparison issue in display_workflow_summary.")

if __name__ == "__main__":
    fix_script()