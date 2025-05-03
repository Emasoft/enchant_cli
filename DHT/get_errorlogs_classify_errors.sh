#!/usr/bin/env bash

# Return error if executed directly - MUST BE PLACED AT THE BEGINNING
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Error: This script cannot be executed directly. All DHT scripts can only be called by the DHT Launcher in the project root. Please run dhtl.sh (or dhtl.bat) followed by the action you want to execute. For more informations use dhtl.sh --help"
    exit 1
fi


# ------------------------------------------------------------------
# Ensure utility functions and constants are available
if ! declare -F print_info >/dev/null 2>&1; then
    if [ -f "$SCRIPT_DIR_LOCAL/get_errorlogs_utils.sh" ]; then
        # shellcheck disable=SC1090
        source "$SCRIPT_DIR_LOCAL/get_errorlogs_utils.sh"
    else
        echo "❌ Missing required helper: get_errorlogs_utils.sh" >&2
        exit 1
    fi
fi
# ------------------------------------------------------------------
# Auto-generated refactored helper script from get_errorlogs.sh
# Generated on 2025-04-19
classify_errors() {
    local log_file="$1"
    local output_file="$2"
    if [ ! -f "$log_file" ]; then
        print_error "Log file not found: $log_file"
        return 1
    fi
    # Clear or create output file
    > "$output_file"
    print_important "ERROR CLASSIFICATION SUMMARY" >> "$output_file"
    echo "Log file: $log_file" >> "$output_file"
    echo "Classification timestamp: $(date "+%Y-%m-%d %H:%M:%S")" >> "$output_file"
    echo "───────────────────────────────────────────────────────────────" >> "$output_file"
    echo "" >> "$output_file"
    # Track statistics
    local critical_count=0
    local severe_count=0
    local warning_count=0
    # Check for critical errors and extract relevant context
    print_critical "CRITICAL ERRORS:" >> "$output_file"
    echo "───────────────────────────────────────────────────────────────" >> "$output_file"
    # First, check if there are any critical errors
    if grep -q -E "$ERROR_PATTERN_CRITICAL" "$log_file"; then
        # Get critical errors with line numbers
        local critical_lines=$(grep -n -E "$ERROR_PATTERN_CRITICAL" "$log_file" | cut -d':' -f1 | head -20)
        critical_count=$(echo "$critical_lines" | wc -l | tr -d ' ')
        # Process each critical error line to extract meaningful context
        echo "$critical_lines" | while read -r line_num; do
            if [ -n "$line_num" ]; then
                # Get 2 lines before and 4 lines after the error for context
                local context_start=$((line_num > 2 ? line_num - 2 : 1))
                local context_end=$((line_num + 4))
                # Print the error line with context
                echo -e "\033[1;31m>>> Critical error at line $line_num:\033[0m" >> "$output_file"
                sed -n "${context_start},${context_end}p" "$log_file" | \
                sed "${line_num}s/^/\033[1;31m→ /" | \
                sed "${line_num}s/$/\033[0m/" >> "$output_file"
                # Extract stack trace if it exists
                if grep -q -A 5 -B 5 -E "^$line_num:" "$log_file"; then
                    echo -e "\n\033[1;31m>>> Stack trace:\033[0m" >> "$output_file"
                    grep -A 15 -E "(Traceback|Stack trace|Call stack|at .*\(.*:[0-9]+\)|File \".*\", line [0-9]+)" "$log_file" | \
                    grep -A 15 -B 1 -E "^$line_num:" | head -15 >> "$output_file"
                fi
                echo "───────────────────────────────────────────────────────────────" >> "$output_file"
            fi
        done
    else
        echo "None found" >> "$output_file"
    fi
    echo "" >> "$output_file"
    # Check for severe errors (excluding those already identified as critical)
    print_severe "SEVERE ERRORS:" >> "$output_file"
    echo "───────────────────────────────────────────────────────────────" >> "$output_file"
    if grep -q -E "$ERROR_PATTERN_SEVERE" "$log_file" && ! grep -q -E "$ERROR_PATTERN_CRITICAL" "$log_file"; then
        # Get severe errors with line numbers, excluding critical patterns
        local severe_lines=$(grep -n -E "$ERROR_PATTERN_SEVERE" "$log_file" | grep -v -E "$ERROR_PATTERN_CRITICAL" | cut -d':' -f1 | head -15)
        severe_count=$(echo "$severe_lines" | wc -l | tr -d ' ')
        # Process each severe error line
        echo "$severe_lines" | while read -r line_num; do
            if [ -n "$line_num" ]; then
                # Get 1 line before and 3 lines after the error for context
                local context_start=$((line_num > 1 ? line_num - 1 : 1))
                local context_end=$((line_num + 3))
                # Print the error line with context
                echo -e "\033[1;35m>>> Severe error at line $line_num:\033[0m" >> "$output_file"
                sed -n "${context_start},${context_end}p" "$log_file" | \
                sed "${line_num}s/^/\033[1;35m→ /" | \
                sed "${line_num}s/$/\033[0m/" >> "$output_file"
                echo "───────────────────────────────────────────────────────────────" >> "$output_file"
            fi
        done
    else
        echo "None found" >> "$output_file"
    fi
    echo "" >> "$output_file"
    # Check for warnings (excluding those already identified as critical or severe)
    print_warning "WARNINGS:" >> "$output_file"
    echo "───────────────────────────────────────────────────────────────" >> "$output_file"
    if grep -q -E "$ERROR_PATTERN_WARNING" "$log_file" && ! grep -q -E "$ERROR_PATTERN_CRITICAL|$ERROR_PATTERN_SEVERE" "$log_file"; then
        # Get warnings with line numbers, excluding critical and severe patterns
        local warning_lines=$(grep -n -E "$ERROR_PATTERN_WARNING" "$log_file" | grep -v -E "$ERROR_PATTERN_CRITICAL|$ERROR_PATTERN_SEVERE" | cut -d':' -f1 | head -10)
        warning_count=$(echo "$warning_lines" | wc -l | tr -d ' ')
        # Process each warning line
        echo "$warning_lines" | while read -r line_num; do
            if [ -n "$line_num" ]; then
                # Get just the warning line itself with minimal context
                echo -e "\033[1;33m>>> Warning at line $line_num:\033[0m" >> "$output_file"
                sed -n "${line_num}p" "$log_file" | \
                sed "s/^/\033[1;33m→ /" | \
                sed "s/$/\033[0m/" >> "$output_file"
            fi
        done
    else
        echo "None found" >> "$output_file"
    fi
    # Add error summary statistics
    echo "" >> "$output_file"
    echo "───────────────────────────────────────────────────────────────" >> "$output_file"
    print_important "ERROR SUMMARY STATISTICS:" >> "$output_file"
    echo "───────────────────────────────────────────────────────────────" >> "$output_file"
    echo "Critical Errors: $critical_count" >> "$output_file"
    echo "Severe Errors: $severe_count" >> "$output_file"
    echo "Warnings: $warning_count" >> "$output_file"
    echo "Total Issues: $((critical_count + severe_count + warning_count))" >> "$output_file"
    # Try to identify root cause if possible
    echo "" >> "$output_file"
    print_important "POSSIBLE ROOT CAUSES:" >> "$output_file"
    echo "───────────────────────────────────────────────────────────────" >> "$output_file"
    # Check for common root causes
    if grep -q -E "No space left on device|disk space|quota exceeded" "$log_file"; then
        echo "✱ Disk space issue detected - runner may have run out of disk space" >> "$output_file"
    fi
    if grep -q -E "memory allocation|out of memory|cannot allocate|allocation failed|OOM|Killed" "$log_file"; then
        echo "✱ Memory issue detected - process may have run out of memory" >> "$output_file"
    fi
    if grep -q -E "network.*timeout|connection.*refused|unreachable|DNS|proxy|firewall" "$log_file"; then
        echo "✱ Network connectivity issue detected - check network settings or dependencies" >> "$output_file"
    fi
    if grep -q -E "permission denied|access denied|unauthorized|forbidden|EACCES" "$log_file"; then
        echo "✱ Permission issue detected - check access rights or secrets" >> "$output_file"
    fi
    if grep -q -E "version mismatch|incompatible|requires version|dependency" "$log_file"; then
        echo "✱ Dependency or version compatibility issue detected" >> "$output_file"
    fi
    if grep -q -E "import error|module not found|cannot find module|unknown module" "$log_file"; then
        echo "✱ Missing import or module - check package installation" >> "$output_file"
    fi
    if grep -q -E "timeout|timed out|deadline exceeded|cancelled" "$log_file"; then
        echo "✱ Operation timeout detected - workflow may have exceeded time limits" >> "$output_file"
    fi
    if grep -q -E "syntax error|parsing error|unexpected token" "$log_file"; then
        echo "✱ Syntax error detected - check recent code changes" >> "$output_file"
    fi
    if ! grep -q -E "space left|memory|network|permission|version|import|timeout|syntax" "$log_file"; then
        echo "No specific root cause identified automatically." >> "$output_file"
        echo "Check the detailed error messages above for more information." >> "$output_file"
    fi
    # Create errors file with context for the most significant errors
    local error_file="${log_file}.errors"
    > "$error_file"
    grep -n -B 5 -A 10 -E "$ERROR_PATTERN_CRITICAL" "$log_file" > "$error_file" 2>/dev/null || true
    grep -n -B 3 -A 8 -E "$ERROR_PATTERN_SEVERE" "$log_file" | grep -v -E "$ERROR_PATTERN_CRITICAL" >> "$error_file" 2>/dev/null || true
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
    return 0
}
# Function to find local logs after last commit