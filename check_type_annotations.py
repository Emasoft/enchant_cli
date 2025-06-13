#!/usr/bin/env python3
import ast
import sys

def check_annotations(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read(), filename=filename)
    
    issues = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            # Skip __init__ methods that implicitly return None
            if node.name == '__init__':
                continue
            
            # Skip very simple getter/setter methods
            if node.name in ('__get__', '__set__', '__eq__', '__repr__', '__str__'):
                continue
                
            # Check for missing return type annotation
            if node.returns is None:
                issues.append({
                    'file': filename,
                    'line': node.lineno,
                    'function': node.name,
                    'issue': 'Missing return type annotation'
                })
            
            # Check parameters
            for arg in node.args.args:
                if arg.annotation is None and arg.arg != 'self' and arg.arg != 'cls':
                    issues.append({
                        'file': filename,
                        'line': node.lineno,
                        'function': node.name,
                        'parameter': arg.arg,
                        'issue': f'Missing type annotation for parameter: {arg.arg}'
                    })
    
    return issues

# Check each file
files = ['cli_translator.py', 'translation_service.py', 'enchant_cli.py', 'make_epub.py']
all_issues = []

for file in files:
    try:
        issues = check_annotations(file)
        all_issues.extend(issues)
    except Exception as e:
        print(f'Error checking {file}: {e}', file=sys.stderr)

# Sort by file and line number
all_issues.sort(key=lambda x: (x['file'], x['line']))

# Print report
current_file = None
for issue in all_issues:
    if issue['file'] != current_file:
        if current_file is not None:
            print()
        print(f"=== {issue['file']} ===")
        current_file = issue['file']
    
    if 'parameter' in issue:
        print(f"Line {issue['line']}: {issue['function']}() - {issue['issue']}")
    else:
        print(f"Line {issue['line']}: {issue['function']}() - {issue['issue']}")