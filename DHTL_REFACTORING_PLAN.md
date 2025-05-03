# DHTL Refactoring Plan

## Overview

The Development Helper Toolkit Launcher (dhtl.sh) currently exceeds 150KB, making it difficult to manage and maintain. This refactoring plan outlines the approach to splitting it into smaller, more manageable files while maintaining functionality.

## Key Requirements

1. All individual files must be under 10KB
2. The refactored code must maintain identical functionality
3. The main dhtl.sh file should become an orchestrator
4. Process Guardian integration must be preserved
5. Error handling must work across file boundaries
6. Code must be organized logically by functionality

## Technical Approach

### Phase 1: Setup and Analysis

#### Tree-sitter Installation

We'll use tree-sitter to parse the Bash script and identify functions, variables, and code blocks:

```bash
# Install tree-sitter and Bash grammar
npm install -g tree-sitter-cli
npm install -g tree-sitter-bash

# For Python integration
pip install tree-sitter
```

#### Parsing Script Development

We'll create a Python script that:
1. Uses tree-sitter to parse dhtl.sh
2. Identifies all functions, variables, conditional blocks
3. Maps dependencies between functions
4. Outputs line ranges for extraction

```python
from tree_sitter import Language, Parser
import os

# Load Bash grammar
Language.build_library('build/bash.so', ['path/to/tree-sitter-bash'])
BASH = Language('build/bash.so', 'bash')

parser = Parser()
parser.set_language(BASH)

# Parse dhtl.sh
with open('dhtl.sh', 'r') as f:
    source_code = f.read()
    tree = parser.parse(bytes(source_code, 'utf8'))

# Extract functions and analyze
# ...
```

### Phase 2: Structure Analysis

We'll analyze the script structure to identify logical groupings:

#### Proposed File Structure

1. **dhtl.sh** - Main orchestrator (~5KB)
2. **dhtl_env.sh** - Environment setup functions (~8KB)
3. **dhtl_guardian.sh** - Process guardian functions (~8KB)
4. **dhtl_commands.sh** - Command execution functions (~9KB)
5. **dhtl_utils.sh** - Utility functions (~8KB)
6. **dhtl_platform.sh** - Platform-specific code (~5KB)
7. **dhtl_help.sh** - Help text and documentation (~5KB)

### Phase 3: Implementation

#### Function Extraction

For each function, we'll:
1. Determine its dependencies
2. Identify the appropriate target file
3. Extract the function with its context
4. Add proper header documentation

#### Orchestrator Design

The main dhtl.sh will be rewritten to:
1. Source all module files
2. Set up the environment
3. Parse command-line arguments
4. Route to appropriate command handlers
5. Ensure proper cleanup

Example structure:
```bash
#!/bin/bash
set -eo pipefail

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Import modules
source "$SCRIPT_DIR/dhtl_env.sh"
source "$SCRIPT_DIR/dhtl_guardian.sh"
source "$SCRIPT_DIR/dhtl_commands.sh"
source "$SCRIPT_DIR/dhtl_utils.sh"
source "$SCRIPT_DIR/dhtl_platform.sh"
source "$SCRIPT_DIR/dhtl_help.sh"

# Initialize environment
dhtl_init_environment

# Process arguments
dhtl_process_arguments "$@"

# Execute command
dhtl_execute_command

# Ensure cleanup
dhtl_cleanup
```

#### Cross-file Error Handling

We'll implement a robust error handling system:
```bash
# In dhtl_utils.sh
dhtl_error() {
    echo "❌ ERROR: $1" >&2
    export DHTL_ERROR_OCCURRED=1
    return 1
}

# In each module file
trap 'export DHTL_ERROR_OCCURRED=1' ERR

# In main script
if [[ -n "$DHTL_ERROR_OCCURRED" ]]; then
    dhtl_cleanup
    exit 1
fi
```

### Phase 4: Testing

We'll systematically test all commands to ensure equivalent behavior:

1. Create test scripts for each command
2. Compare output and exit codes with original script
3. Test error scenarios and edge cases
4. Verify process guardian integration works identically

### Phase 5: Documentation

We'll document the new architecture:

1. Update the module structure in code comments
2. Create module relationship diagrams
3. Document function purposes and dependencies
4. Provide guidelines for future modifications

## Implementation Timeline

1. **Week 1**: Setup tree-sitter and develop parsing script (Tasks #50-51)
2. **Week 1**: Analyze dhtl.sh structure and design new architecture (Tasks #52-53)
3. **Week 2**: Extract functions to module files (Tasks #54-58)
4. **Week 2**: Rewrite dhtl.sh as orchestrator (Task #59)
5. **Week 3**: Implement cross-file error handling (Task #60)
6. **Week 3**: Test and validate refactored code (Task #61)
7. **Week 4**: Document new architecture (Task #62)

## Risk Mitigation

1. **Functionality Changes**: We'll maintain a comprehensive test suite to detect any behavioral changes
2. **Script Size Control**: Regularly check file sizes to ensure they stay under 10KB
3. **Dependency Management**: Carefully track function dependencies during extraction
4. **Rollback Plan**: Maintain the original script for easy rollback if issues are detected

## Success Criteria

1. All files are under 10KB
2. All commands work identically to the original script
3. Process guardian integration is preserved
4. Error handling works across file boundaries
5. Code is organized logically by functionality

## Next Steps

After approval, we'll proceed with Task #50: Research and setup tree-sitter with Bash grammar.