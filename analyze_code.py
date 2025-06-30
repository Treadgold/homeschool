#!/usr/bin/env python3
"""
Code Analysis Tool - Maps all links and finds unused code
"""

import ast
import os
import re
import json
from pathlib import Path
from collections import defaultdict


def analyze_code():
    """Analyze code structure and find unused components"""
    print("🔍 Code Analysis Tool")
    print("=" * 50)
    
    app_dir = Path("app")
    if not app_dir.exists():
        print("❌ 'app' directory not found")
        return
    
    # Find all Python files
    python_files = list(app_dir.rglob("*.py"))
    print(f"📂 Found {len(python_files)} Python files")
    
    # Analyze routes
    routes = find_routes(python_files)
    print(f"🛣️  Found {len(routes)} routes")
    
    # Analyze imports
    imports = analyze_imports(python_files)
    print(f"📦 Found {sum(len(v) for v in imports.values())} imports")
    
    # Find potentially unused files
    unused = find_unused_files(python_files, imports)
    print(f"💀 Found {len(unused)} potentially unused files")
    
    # Generate report
    report = {
        "routes": routes,
        "imports": {k: list(v) for k, v in imports.items()},
        "unused_files": unused,
        "file_count": len(python_files)
    }
    
    with open("code_analysis.json", "w") as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📋 Report saved to: code_analysis.json")
    
    # Print summary
    if routes:
        print(f"\n🛣️  Routes:")
        for route, info in list(routes.items())[:10]:
            print(f"   {route} ({info['method']}) - {info['file']}")
    
    if unused:
        print(f"\n💀 Potentially unused files:")
        for file in unused[:5]:
            print(f"   - {file}")


def find_routes(python_files):
    """Find FastAPI routes"""
    routes = {}
    route_pattern = r'@(?:app|router)\.(get|post|put|delete|patch)\(["\']([^"\']+)["\']'
    
    for py_file in python_files:
        try:
            with open(py_file, 'r') as f:
                content = f.read()
            
            matches = re.finditer(route_pattern, content)
            for match in matches:
                method = match.group(1)
                path = match.group(2)
                routes[path] = {
                    "method": method,
                    "file": str(py_file.relative_to(Path(".")))
                }
        except Exception as e:
            print(f"   ⚠️  Error reading {py_file}: {e}")
    
    return routes


def analyze_imports(python_files):
    """Analyze import statements"""
    imports = defaultdict(set)
    
    for py_file in python_files:
        try:
            with open(py_file, 'r') as f:
                content = f.read()
            
            tree = ast.parse(content)
            file_key = str(py_file.relative_to(Path(".")))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports[file_key].add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports[file_key].add(node.module)
        except Exception as e:
            print(f"   ⚠️  Error parsing {py_file}: {e}")
    
    return imports


def find_unused_files(python_files, imports):
    """Find potentially unused files"""
    all_modules = set()
    
    # Collect all imported modules
    for file_imports in imports.values():
        for imp in file_imports:
            if imp.startswith('app.'):
                all_modules.add(imp)
    
    unused = []
    for py_file in python_files:
        rel_path = str(py_file.relative_to(Path(".")))
        module_path = rel_path.replace('/', '.').replace('.py', '')
        
        # Skip special files
        if (rel_path.endswith('__init__.py') or 
            rel_path.endswith('main.py') or 
            'test_' in rel_path):
            continue
        
        # Check if this module is imported anywhere
        if module_path not in all_modules:
            # Simple check - if file is very small and not imported, might be unused
            try:
                size = py_file.stat().st_size
                if size < 2000:  # Less than 2KB
                    unused.append(rel_path)
            except:
                pass
    
    return unused


if __name__ == "__main__":
    analyze_code() 