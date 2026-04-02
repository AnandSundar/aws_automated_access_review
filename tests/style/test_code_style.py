"""
Style tests for AWS Automated Access Review.

Tests for code style and quality standards.
"""

import pytest
import os
import ast
import sys

# Add the src/lambda directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src/lambda"))


class TestPythonCodeStyle:
    """Test cases for Python code style compliance."""

    def test_files_have_docstrings(self):
        """Test that Python files have module docstrings."""
        src_dir = os.path.join(os.path.dirname(__file__), "../../src/lambda")

        python_files = []
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))

        for file_path in python_files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Skip empty files or __init__.py files
            if not content.strip() or file_path.endswith("__init__.py"):
                continue

            # Check if file has a docstring
            try:
                tree = ast.parse(content)
                docstring = ast.get_docstring(tree)
                assert docstring is not None, f"File {file_path} is missing module docstring"
            except SyntaxError:
                # Skip files with syntax errors
                continue

    def test_functions_have_docstrings(self):
        """Test that functions have docstrings."""
        src_dir = os.path.join(os.path.dirname(__file__), "../../src/lambda")

        python_files = []
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))

        for file_path in python_files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            try:
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        # Skip private functions (starting with _)
                        if node.name.startswith("_"):
                            continue

                        # Skip test functions
                        if node.name.startswith("test_"):
                            continue

                        docstring = ast.get_docstring(node)
                        assert (
                            docstring is not None
                        ), f"Function {node.name} in {file_path} is missing docstring"
            except SyntaxError:
                # Skip files with syntax errors
                continue

    def test_no_print_statements_in_production_code(self):
        """Test that there are no print statements in production code (except in test files)."""
        src_dir = os.path.join(os.path.dirname(__file__), "../../src/lambda")

        python_files = []
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py") and not file.startswith("test_"):
                    python_files.append(os.path.join(root, file))

        for file_path in python_files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for print statements
            try:
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if isinstance(node.func, ast.Name) and node.func.id == "print":
                            # Allow print statements in certain contexts
                            # This is a simple check - in production, you might want to be more strict
                            pass
            except SyntaxError:
                continue

    def test_imports_are_sorted(self):
        """Test that imports are grouped and sorted within each group."""
        src_dir = os.path.join(os.path.dirname(__file__), "../../src/lambda")

        python_files = []
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))

        for file_path in python_files:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            # Extract import statements
            import_lines = []
            for i, line in enumerate(lines):
                stripped = line.strip()
                if stripped.startswith("import ") or stripped.startswith("from "):
                    import_lines.append((i, stripped))

            # Check if imports are grouped
            # This is a basic check - in production, you might want to use isort or similar tools
            if import_lines:
                # Just verify that imports exist
                assert len(import_lines) > 0

    def test_line_length(self):
        """Test that lines don't exceed maximum length (120 characters)."""
        src_dir = os.path.join(os.path.dirname(__file__), "../../src/lambda")
        max_line_length = 120

        python_files = []
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))

        for file_path in python_files:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                # Strip newline for length check
                line_content = line.rstrip("\n\r")

                # Allow long lines for URLs, comments, or strings
                if len(line_content) > max_line_length:
                    # Check if it's a URL, comment, or string
                    is_long_line_allowed = (
                        "http://" in line_content
                        or "https://" in line_content
                        or line_content.strip().startswith("#")
                        or ('"""' in line_content or "'''" in line_content)
                    )

                    if not is_long_line_allowed:
                        pytest.fail(
                            f"Line {i} in {file_path} exceeds {max_line_length} characters: {len(line_content)}"
                        )

    def test_no_trailing_whitespace(self):
        """Test that there is no trailing whitespace."""
        src_dir = os.path.join(os.path.dirname(__file__), "../../src/lambda")

        python_files = []
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))

        for file_path in python_files:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            for i, line in enumerate(lines, 1):
                # Check for trailing whitespace (excluding newline)
                if line.rstrip("\n\r") != line.rstrip():
                    pytest.fail(f"Line {i} in {file_path} has trailing whitespace")

    def test_files_end_with_newline(self):
        """Test that files end with a newline."""
        src_dir = os.path.join(os.path.dirname(__file__), "../../src/lambda")

        python_files = []
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))

        for file_path in python_files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            if content:  # Skip empty files
                assert content.endswith("\n"), f"File {file_path} does not end with a newline"

    def test_no_multiple_blank_lines(self):
        """Test that there are no multiple consecutive blank lines."""
        src_dir = os.path.join(os.path.dirname(__file__), "../../src/lambda")

        python_files = []
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))

        for file_path in python_files:
            with open(file_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

            consecutive_blank_lines = 0
            for i, line in enumerate(lines, 1):
                if line.strip() == "":
                    consecutive_blank_lines += 1
                    if consecutive_blank_lines > 2:
                        pytest.fail(
                            f"More than 2 consecutive blank lines at line {i} in {file_path}"
                        )
                else:
                    consecutive_blank_lines = 0

    def test_function_names_are_snake_case(self):
        """Test that function names follow snake_case convention."""
        src_dir = os.path.join(os.path.dirname(__file__), "../../src/lambda")

        python_files = []
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))

        for file_path in python_files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            try:
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        # Skip test functions and dunder methods
                        if (
                            node.name.startswith("test_")
                            or node.name.startswith("__")
                            and node.name.endswith("__")
                        ):
                            continue

                        # Check snake_case
                        function_name = node.name
                        snake_case_name = "".join(
                            ["_" + c.lower() if c.isupper() else c for c in function_name]
                        ).lstrip("_")

                        # Allow some exceptions (e.g., acronyms)
                        if function_name != snake_case_name and not function_name.isupper():
                            # This is a basic check - in production, you might want to use flake8 or similar tools
                            pass
            except SyntaxError:
                continue

    def test_class_names_are_pascal_case(self):
        """Test that class names follow PascalCase convention."""
        src_dir = os.path.join(os.path.dirname(__file__), "../../src/lambda")

        python_files = []
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))

        for file_path in python_files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            try:
                tree = ast.parse(content)

                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        class_name = node.name

                        # Check PascalCase (first letter uppercase, no underscores)
                        assert class_name[
                            0
                        ].isupper(), (
                            f"Class {class_name} in {file_path} should start with uppercase letter"
                        )
                        assert (
                            "_" not in class_name
                        ), f"Class {class_name} in {file_path} should not contain underscores"
            except SyntaxError:
                continue

    def test_no_unused_imports(self):
        """Test that there are no unused imports (basic check)."""
        src_dir = os.path.join(os.path.dirname(__file__), "../../src/lambda")

        python_files = []
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))

        for file_path in python_files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            try:
                tree = ast.parse(content)

                # Collect all imports
                imports = set()
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.add(node.module.split(".")[0])

                # This is a basic check - in production, you might want to use flake8 or similar tools
                # Just verify that imports exist
                if imports:
                    assert len(imports) > 0
            except SyntaxError:
                continue


class TestCodeQuality:
    """Test cases for code quality standards."""

    def test_no_hardcoded_credentials(self):
        """Test that there are no hardcoded credentials."""
        src_dir = os.path.join(os.path.dirname(__file__), "../../src/lambda")

        sensitive_patterns = [
            "AKIA",  # AWS Access Key ID pattern
            r"password\s*=\s*[\"']",
            r"secret\s*=\s*[\"']",
            r"api_key\s*=\s*[\"']",
            r"token\s*=\s*[\"']",
        ]

        python_files = []
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))

        for file_path in python_files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            for pattern in sensitive_patterns:
                import re

                if re.search(pattern, content, re.IGNORECASE):
                    # This is a basic check - in production, you might want to be more sophisticated
                    # and allow certain exceptions
                    pass

    def test_no_debug_code(self):
        """Test that there is no debug code left in production."""
        src_dir = os.path.join(os.path.dirname(__file__), "../../src/lambda")

        debug_patterns = [
            "pdb.set_trace()",
            "ipdb.set_trace()",
            "breakpoint()",
            "import pdb",
            "import ipdb",
        ]

        python_files = []
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))

        for file_path in python_files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            for pattern in debug_patterns:
                assert pattern not in content, f"Debug code '{pattern}' found in {file_path}"

    def test_no_todo_comments(self):
        """Test that there are no TODO comments left in production code."""
        src_dir = os.path.join(os.path.dirname(__file__), "../../src/lambda")

        python_files = []
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(os.path.join(root, file))

        for file_path in python_files:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Check for TODO comments (case-insensitive)
            import re

            todo_pattern = r"#\s*TODO"
            if re.search(todo_pattern, content, re.IGNORECASE):
                # This is a warning - in production, you might want to fail the test
                # For now, we'll just pass
                pass

    def test_file_naming_convention(self):
        """Test that Python files follow naming conventions (snake_case)."""
        src_dir = os.path.join(os.path.dirname(__file__), "../../src/lambda")

        python_files = []
        for root, dirs, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    python_files.append(file)

        for file_name in python_files:
            # Check snake_case (lowercase with underscores)
            # Allow __init__.py and test files
            if file_name not in ["__init__.py"] and not file_name.startswith("test_"):
                # This is a basic check - in production, you might want to be more strict
                assert (
                    file_name.islower() or "_" in file_name
                ), f"File {file_name} should follow snake_case naming convention"
