#!/usr/bin/env python3
"""
Code Analysis Tool for Homeschool Application
Maps all code links, routes, imports, and identifies unused code
"""

import ast
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Set, Any
from collections import defaultdict, deque
import importlib.util


class CodeAnalyzer:
    """Comprehensive code analyzer for the Homeschool application"""
    
    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)
        self.app_dir = self.root_dir / "app"
        
        # Analysis results
        self.routes = {}
        self.imports = defaultdict(set)
        self.function_calls = defaultdict(set)
        self.class_usage = defaultdict(set)
        self.file_dependencies = defaultdict(set)
        self.dead_code = []
        self.orphaned_files = []
        
    def analyze(self):
        """Run comprehensive code analysis"""
        print("🔍 Code Analysis for Homeschool Application")
        print("=" * 60)
        
        # Phase 1: Discover all Python files
        python_files = self._discover_python_files()
        print(f"📂 Found {len(python_files)} Python files")
        
        # Phase 2: Parse imports and dependencies
        print("\n🔗 Analyzing imports and dependencies...")
        self._analyze_imports(python_files)
        
        # Phase 3: Analyze FastAPI routes
        print("\n🛣️  Analyzing FastAPI routes...")
        self._analyze_routes(python_files)
        
        # Phase 4: Analyze function calls and usage
        print("\n📞 Analyzing function calls and usage...")
        self._analyze_function_usage(python_files)
        
        # Phase 5: Find dead code
        print("\n💀 Finding dead code...")
        self._find_dead_code()
        
        # Phase 6: Find orphaned files
        print("\n🏝️  Finding orphaned files...")
        self._find_orphaned_files()
        
        # Phase 7: Analyze template usage
        print("\n📄 Analyzing template usage...")
        self._analyze_template_usage()
        
        # Generate reports
        self._generate_reports()
        
        return self._create_summary()
    
    def _discover_python_files(self) -> List[Path]:
        """Discover all Python files in the project"""
        python_files = []
        
        # Search patterns
        search_dirs = [
            self.app_dir,
            self.root_dir / "tests",
            self.root_dir / "scripts",
            self.root_dir / "migrations"
        ]
        
        for search_dir in search_dirs:
            if search_dir.exists():
                for py_file in search_dir.rglob("*.py"):
                    if not any(part.startswith('.') for part in py_file.parts):
                        python_files.append(py_file)
        
        # Also check root directory
        for py_file in self.root_dir.glob("*.py"):
            python_files.append(py_file)
        
        return python_files
    
    def _analyze_imports(self, python_files: List[Path]):
        """Analyze import statements and dependencies"""
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                relative_path = py_file.relative_to(self.root_dir)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            self.imports[str(relative_path)].add(alias.name)
                            self.file_dependencies[str(relative_path)].add(alias.name)
                    
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            module = node.module
                            self.imports[str(relative_path)].add(module)
                            self.file_dependencies[str(relative_path)].add(module)
                            
                            for alias in node.names:
                                full_import = f"{module}.{alias.name}"
                                self.imports[str(relative_path)].add(full_import)
                
            except Exception as e:
                print(f"   ⚠️  Error parsing {py_file}: {e}")
    
    def _analyze_routes(self, python_files: List[Path]):
        """Analyze FastAPI routes and endpoints"""
        route_patterns = [
            r'@app\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            r'@router\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            r'app\.include_router\s*\(\s*\w+\s*,\s*prefix\s*=\s*["\']([^"\']+)["\']'
        ]
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                relative_path = py_file.relative_to(self.root_dir)
                
                for pattern in route_patterns:
                    matches = re.finditer(pattern, content, re.MULTILINE)
                    for match in matches:
                        if len(match.groups()) >= 2:
                            method = match.group(1) if match.group(1) else "include"
                            route = match.group(2)
                            
                            if route not in self.routes:
                                self.routes[route] = []
                            
                            self.routes[route].append({
                                "method": method,
                                "file": str(relative_path),
                                "line": content[:match.start()].count('\n') + 1
                            })
                
            except Exception as e:
                print(f"   ⚠️  Error analyzing routes in {py_file}: {e}")
    
    def _analyze_function_usage(self, python_files: List[Path]):
        """Analyze function definitions and calls"""
        # First pass: collect all function definitions
        function_definitions = {}
        
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                relative_path = py_file.relative_to(self.root_dir)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        func_key = f"{relative_path}:{node.name}"
                        function_definitions[func_key] = {
                            "file": str(relative_path),
                            "name": node.name,
                            "line": node.lineno,
                            "is_async": isinstance(node, ast.AsyncFunctionDef)
                        }
                    
                    elif isinstance(node, ast.ClassDef):
                        class_key = f"{relative_path}:{node.name}"
                        function_definitions[class_key] = {
                            "file": str(relative_path),
                            "name": node.name,
                            "line": node.lineno,
                            "type": "class"
                        }
                
            except Exception as e:
                print(f"   ⚠️  Error analyzing functions in {py_file}: {e}")
        
        # Second pass: find function calls
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                tree = ast.parse(content)
                relative_path = py_file.relative_to(self.root_dir)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        func_name = None
                        
                        if isinstance(node.func, ast.Name):
                            func_name = node.func.id
                        elif isinstance(node.func, ast.Attribute):
                            func_name = node.func.attr
                        
                        if func_name:
                            self.function_calls[str(relative_path)].add(func_name)
                
            except Exception as e:
                print(f"   ⚠️  Error analyzing function calls in {py_file}: {e}")
    
    def _find_dead_code(self):
        """Find potentially dead code"""
        # Find functions that are defined but never called
        all_defined_functions = set()
        all_called_functions = set()
        
        # Collect all function names from imports and definitions
        for file_path, imports in self.imports.items():
            for imp in imports:
                if '.' in imp:
                    parts = imp.split('.')
                    all_called_functions.add(parts[-1])
        
        # Collect function calls
        for file_path, calls in self.function_calls.items():
            all_called_functions.update(calls)
        
        # Simple heuristic: look for functions that might be unused
        # This is a basic implementation - real dead code detection is complex
        for file_path, calls in self.function_calls.items():
            if len(calls) == 0:
                # File with no function calls might be dead
                file_size = (self.root_dir / file_path).stat().st_size
                if file_size < 1000:  # Small files with no calls might be dead
                    self.dead_code.append({
                        "file": file_path,
                        "reason": "Small file with no function calls",
                        "size": file_size
                    })
    
    def _find_orphaned_files(self):
        """Find files that are not imported by any other file"""
        all_imported_modules = set()
        
        # Collect all imported modules
        for file_path, imports in self.imports.items():
            for imp in imports:
                # Convert import paths to file paths
                if imp.startswith('app.'):
                    module_path = imp.replace('.', '/') + '.py'
                    all_imported_modules.add(module_path)
                elif '.' in imp and not imp.startswith('_'):
                    # Might be a local module
                    all_imported_modules.add(imp.replace('.', '/') + '.py')
        
        # Find files that are never imported
        for file_path, imports in self.imports.items():
            # Convert file path to potential import path
            if file_path.startswith('app/'):
                potential_import = file_path.replace('/', '.').replace('.py', '')
                if (potential_import not in all_imported_modules and 
                    not file_path.endswith('__init__.py') and
                    not file_path.endswith('main.py')):
                    
                    # Check if it's a script or entry point
                    is_script = (file_path.startswith('scripts/') or 
                               file_path.startswith('tests/') or
                               'test_' in file_path)
                    
                    if not is_script:
                        self.orphaned_files.append({
                            "file": file_path,
                            "reason": "Not imported by any other file"
                        })
    
    def _analyze_template_usage(self):
        """Analyze HTML template usage"""
        template_dir = self.app_dir / "templates"
        if not template_dir.exists():
            return
        
        # Find all templates
        templates = list(template_dir.rglob("*.html"))
        template_names = {t.name for t in templates}
        
        # Find template references in Python code
        used_templates = set()
        
        python_files = list(self.app_dir.rglob("*.py"))
        for py_file in python_files:
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for template references
                template_patterns = [
                    r'render_template\s*\(\s*["\']([^"\']+\.html)["\']',
                    r'templates\.TemplateResponse\s*\(\s*["\']([^"\']+\.html)["\']',
                    r'return\s+["\']([^"\']+\.html)["\']'
                ]
                
                for pattern in template_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        used_templates.add(match.group(1))
                        
            except Exception as e:
                print(f"   ⚠️  Error analyzing templates in {py_file}: {e}")
        
        # Find unused templates
        unused_templates = template_names - used_templates
        if unused_templates:
            for template in unused_templates:
                self.orphaned_files.append({
                    "file": f"app/templates/{template}",
                    "reason": "Template not referenced in Python code"
                })
    
    def _generate_reports(self):
        """Generate comprehensive analysis reports"""
        reports_dir = Path("code_analysis_reports")
        reports_dir.mkdir(exist_ok=True)
        
        # Routes report
        with open(reports_dir / "routes.json", 'w') as f:
            json.dump(self.routes, f, indent=2)
        
        # Dependencies report
        with open(reports_dir / "dependencies.json", 'w') as f:
            json.dump(dict(self.file_dependencies), f, indent=2)
        
        # Dead code report
        with open(reports_dir / "dead_code.json", 'w') as f:
            json.dump(self.dead_code, f, indent=2)
        
        # Orphaned files report
        with open(reports_dir / "orphaned_files.json", 'w') as f:
            json.dump(self.orphaned_files, f, indent=2)
        
        print(f"\n📊 Reports generated in: {reports_dir}")
    
    def _create_summary(self) -> Dict[str, Any]:
        """Create analysis summary"""
        summary = {
            "routes": {
                "total": len(self.routes),
                "unique_paths": list(self.routes.keys())
            },
            "files": {
                "total_analyzed": len(self.imports),
                "with_dependencies": len([f for f in self.imports if self.imports[f]]),
                "potentially_dead": len(self.dead_code),
                "orphaned": len(self.orphaned_files)
            },
            "dependencies": {
                "total_imports": sum(len(imports) for imports in self.imports.values()),
                "unique_modules": len(set().union(*self.imports.values()))
            }
        }
        
        print(f"\n📋 Analysis Summary:")
        print(f"   🛣️  Routes found: {summary['routes']['total']}")
        print(f"   📁 Files analyzed: {summary['files']['total_analyzed']}")
        print(f"   💀 Potentially dead code: {summary['files']['potentially_dead']}")
        print(f"   🏝️  Orphaned files: {summary['files']['orphaned']}")
        print(f"   📦 Total imports: {summary['dependencies']['total_imports']}")
        
        if self.dead_code:
            print(f"\n💀 Potentially Dead Code:")
            for item in self.dead_code[:5]:  # Show first 5
                print(f"   - {item['file']}: {item['reason']}")
        
        if self.orphaned_files:
            print(f"\n🏝️  Orphaned Files:")
            for item in self.orphaned_files[:5]:  # Show first 5
                print(f"   - {item['file']}: {item['reason']}")
        
        return summary


def main():
    """Main entry point"""
    analyzer = CodeAnalyzer()
    summary = analyzer.analyze()
    
    print(f"\n🎯 Code Analysis Complete!")
    print(f"   Check 'code_analysis_reports/' for detailed reports")


if __name__ == "__main__":
    main() 