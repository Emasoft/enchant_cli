#!/usr/bin/env python3
"""
Script to enhance the get_errorlogs.sh script to provide better error summaries.
Integrates the check_summary_output.py functionality.
"""

import re
import sys
from pathlib import Path


def enhance_get_errorlogs_script():
    """
    Enhance the get_errorlogs.sh script to integrate the check_summary_output.py functionality.
    """
    # Path to the script
    script_path = Path('/Users/emanuelesabetta/Code/ENCHANT_BOOK_MANAGER/enchant_cli/get_errorlogs.sh')
    
    # Ensure the script exists
    if not script_path.exists():
        print("Error: get_errorlogs.sh not found", file=sys.stderr)
        return 1
    
    # Read the file content
    content = script_path.read_text()
    
    # Ensure check_summary_output.py is referenced for enhanced analysis
    if "check_summary_output.py" not in content:
        # Find the classify_errors function
        classify_errors_pattern = r'classify_errors\(\) \{.*?^\}'
        classify_errors_match = re.search(classify_errors_pattern, content, re.DOTALL | re.MULTILINE)
        
        if classify_errors_match:
            # Enhance the function to use check_summary_output.py if available
            original_function = classify_errors_match.group(0)
            
            # Find the point right before the final return statement
            return_index = original_function.rfind("return 0")
            if return_index > 0:
                enhanced_function = original_function[:return_index] + """
    # Use check_summary_output.py for enhanced analysis if available
    if [ -f "$SCRIPT_DIR/check_summary_output.py" ]; then
        print_info "Running enhanced error analysis..."
        if [ -x "$SCRIPT_DIR/check_summary_output.py" ]; then
            "$PYTHON_CMD" "$SCRIPT_DIR/check_summary_output.py" "$log_file" >> "$output_file"
        else
            chmod +x "$SCRIPT_DIR/check_summary_output.py"
            "$PYTHON_CMD" "$SCRIPT_DIR/check_summary_output.py" "$log_file" >> "$output_file"
        fi
    fi

""" + original_function[return_index:]
                
                content = content.replace(original_function, enhanced_function)
    
    # Ensure latest function uses enhanced analysis
    if "get_latest_logs" in content and "check_summary_output.py" not in content:
        # Find the get_latest_logs function
        latest_logs_pattern = r'get_latest_logs\(\) \{.*?^\}'
        latest_logs_match = re.search(latest_logs_pattern, content, re.DOTALL | re.MULTILINE)
        
        if latest_logs_match:
            # Enhance to use check_summary_output.py
            original_latest = latest_logs_match.group(0)
            
            # Find the point right before the final return statement
            return_index = original_latest.rfind("return 0")
            if return_index > 0:
                enhanced_latest = original_latest[:return_index] + """
    # Run enhanced analysis on the most recent log
    if [ ${#recent_logs[@]} -gt 0 ] && [ -f "$SCRIPT_DIR/check_summary_output.py" ]; then
        print_header "Enhanced Error Analysis"
        print_info "Running enhanced analysis on the most recent log..."
        most_recent_log="${recent_logs[0]}"
        
        if [ -x "$SCRIPT_DIR/check_summary_output.py" ]; then
            "$PYTHON_CMD" "$SCRIPT_DIR/check_summary_output.py" "$most_recent_log"
        else
            chmod +x "$SCRIPT_DIR/check_summary_output.py"
            "$PYTHON_CMD" "$SCRIPT_DIR/check_summary_output.py" "$most_recent_log"
        fi
    fi

""" + original_latest[return_index:]
                
                content = content.replace(original_latest, enhanced_latest)
    
    # Fix the display_workflow_summary function to handle null/empty values
    display_function_pattern = r'# Function to display workflow summary.*?^\}'
    display_function_match = re.search(display_function_pattern, content, re.DOTALL | re.MULTILINE)
    
    if display_function_match:
        new_display_function = """
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
        content = content.replace(display_function_match.group(0), new_display_function.strip())
    
    # Add a new PYTHON_CMD variable at the configuration section
    if "PYTHON_CMD=" not in content:
        # Find CONFIGURATION section
        config_section_pattern = r'#=========================================================================\n# CONFIGURATION.*?#========================================================================='
        config_section_match = re.search(config_section_pattern, content, re.DOTALL)
        
        if config_section_match:
            enhanced_config = config_section_match.group(0) + "\n\n# Python command path - auto-detected\nPYTHON_CMD=\"python3\"\n"
            content = content.replace(config_section_match.group(0), enhanced_config)
    
    # Add python detection in the script setup
    script_start_pattern = r'#=========================================================================\n# MAIN SCRIPT EXECUTION.*?#========================================================================='
    script_start_match = re.search(script_start_pattern, content, re.DOTALL)
    
    if script_start_match and "Detecting Python interpreter" not in content:
        enhanced_start = script_start_match.group(0) + """

# Detect and validate Python interpreter
print_info "Detecting Python interpreter..."
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    print_warning "No Python interpreter found. Enhanced analysis will not be available."
fi

# Verify Python version
if [ -n "$PYTHON_CMD" ]; then
    PY_VERSION=$($PYTHON_CMD --version 2>&1)
    print_success "Using Python: $PY_VERSION"
fi
"""
        content = content.replace(script_start_match.group(0), enhanced_start)
    
    # Initialize SCRIPT_DIR if not already defined
    if "SCRIPT_DIR=" not in content:
        script_init_pattern = r'set -o pipefail.*?# CONFIGURATION'
        script_init_match = re.search(script_init_pattern, content, re.DOTALL)
        
        if script_init_match:
            enhanced_init = script_init_match.group(0).replace("# CONFIGURATION", """# Get script directory for relative paths
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# CONFIGURATION""")
            content = content.replace(script_init_match.group(0), enhanced_init)
    
    # Write the updated content back to the script
    script_path.write_text(content)
    
    print("Successfully enhanced get_errorlogs.sh with improved error analysis capabilities")
    return 0


if __name__ == "__main__":
    sys.exit(enhance_get_errorlogs_script())