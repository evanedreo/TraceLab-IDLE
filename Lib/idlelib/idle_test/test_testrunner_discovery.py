"""Test testrunner_discovery module."""

import os
import tempfile
import unittest

from idlelib.testrunner_discovery import discover_tests


class TestDiscoverTests(unittest.TestCase):
    """Tests for discover_tests function (AST-based discovery)."""
    
    def setUp(self):
        """Create a temporary directory for test fixture files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
    
    def _write_temp_file(self, filename: str, code: str) -> str:
        """Write Python code to a temporary file and return its path.
        
        Args:
            filename: Name of the file (e.g., 'simple.py')
            code: Python code to write
        
        Returns:
            Absolute path to the created file
        """
        path = os.path.join(self.temp_dir.name, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(code)
        return path
    
    def test_discovers_single_test_class(self):
        """Test discovery of a simple unittest.TestCase with multiple methods."""
        code = '''\
import unittest

class TestExample(unittest.TestCase):
    def test_foo(self):
        pass
    
    def test_bar(self):
        pass
'''
        path = self._write_temp_file('simple.py', code)
        results = discover_tests(path)
        
        # Should find 2 test methods
        self.assertEqual(len(results), 2)
        
        # Check structure of results
        for result in results:
            self.assertIn('id', result)
            self.assertIn('module', result)
            self.assertIn('class', result)
            self.assertIn('method', result)
        
        # Verify content
        ids = {r['id'] for r in results}
        self.assertIn('simple.TestExample.test_bar', ids)
        self.assertIn('simple.TestExample.test_foo', ids)
    
    def test_empty_file_returns_empty_list(self):
        """Test that a file with no tests returns an empty list."""
        code = '# Just a comment\nprint("hello")\n'
        path = self._write_temp_file('empty.py', code)
        results = discover_tests(path)
        self.assertEqual(results, [])
    
    def test_ignores_non_testcase_classes(self):
        """Test that non-TestCase classes are ignored."""
        code = '''\
import unittest

class NotATest:
    """Regular class with test_* methods (should be ignored)."""
    def test_method(self):
        pass

class TestReal(unittest.TestCase):
    """Actual test class."""
    def test_real(self):
        pass
'''
        path = self._write_temp_file('mixed.py', code)
        results = discover_tests(path)
        
        # Should only find the test in TestReal
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['class'], 'TestReal')
        self.assertEqual(results[0]['method'], 'test_real')
    
    def test_handles_malformed_file_gracefully(self):
        """Test that syntax errors are handled gracefully."""
        code = 'def broken( syntax error\n'
        path = self._write_temp_file('broken.py', code)
        results = discover_tests(path)
        # Should return empty list, not raise exception
        self.assertEqual(results, [])
    
    def test_dict_has_required_fields(self):
        """Test that returned dicts have all required fields."""
        code = '''\
import unittest

class TestExample(unittest.TestCase):
    def test_example(self):
        pass
'''
        path = self._write_temp_file('fields.py', code)
        results = discover_tests(path)
        
        self.assertEqual(len(results), 1)
        result = results[0]
        
        # Verify all required fields are present
        required_fields = {'id', 'module', 'class', 'method'}
        self.assertEqual(set(result.keys()), required_fields)
        
        # Verify values
        self.assertEqual(result['module'], 'fields')
        self.assertEqual(result['class'], 'TestExample')
        self.assertEqual(result['method'], 'test_example')
        self.assertEqual(result['id'], 'fields.TestExample.test_example')
    
    def test_results_sorted_by_id(self):
        """Test that results are sorted by ID for determinism."""
        code = '''\
import unittest

class TestZ(unittest.TestCase):
    def test_z(self):
        pass
    
    def test_a(self):
        pass

class TestA(unittest.TestCase):
    def test_b(self):
        pass
'''
        path = self._write_temp_file('sorted.py', code)
        results = discover_tests(path)
        
        # Extract IDs and verify they are sorted
        ids = [r['id'] for r in results]
        sorted_ids = sorted(ids)
        self.assertEqual(ids, sorted_ids)
    
    def test_discovers_testcase_without_import(self):
        """Test discovery when TestCase is used directly (not via unittest.*)."""
        code = '''\
from unittest import TestCase

class TestDirect(TestCase):
    def test_method(self):
        pass
'''
        path = self._write_temp_file('direct.py', code)
        results = discover_tests(path)
        
        # Should discover the test
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['class'], 'TestDirect')
    
    def test_discovers_qualified_testcase(self):
        """Test discovery when TestCase is qualified as unittest.TestCase."""
        code = '''\
import unittest

class TestQualified(unittest.TestCase):
    def test_qualified(self):
        pass
'''
        path = self._write_temp_file('qualified.py', code)
        results = discover_tests(path)
        
        # Should discover the test
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['class'], 'TestQualified')
    
    def test_ignores_non_test_methods(self):
        """Test that methods not starting with 'test_' are ignored."""
        code = '''\
import unittest

class TestExample(unittest.TestCase):
    def test_real_test(self):
        pass
    
    def helper_method(self):
        pass
    
    def setUp(self):
        pass
    
    def tearDown(self):
        pass
'''
        path = self._write_temp_file('methods.py', code)
        results = discover_tests(path)
        
        # Should only find test_real_test
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['method'], 'test_real_test')
    
    def test_nonexistent_file_returns_empty_list(self):
        """Test that a nonexistent file returns an empty list gracefully."""
        results = discover_tests('/nonexistent/path/file.py')
        self.assertEqual(results, [])


if __name__ == '__main__':
    unittest.main(verbosity=2)
