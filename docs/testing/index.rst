Testing Guide
============

This guide outlines the testing strategy and procedures for PulsarNet.

Test Categories
--------------

Unit Tests
~~~~~~~~~

Unit tests verify individual components and functions:

* Located in ``tests/unit/`` directory
* Run with ``pytest tests/unit/``
* Focus on isolated component testing
* Mock external dependencies

Key areas covered:

* Protocol implementations
* Device management functions
* Storage operations
* Configuration validation

Integration Tests
~~~~~~~~~~~~~~~~

Integration tests verify component interactions:

* Located in ``tests/integration/`` directory
* Run with ``pytest tests/integration/``
* Test multiple components together
* Verify module interactions

Areas covered:

* Backup workflow end-to-end
* Device discovery and management
* Storage and retention policies
* Scheduler operations

UI Tests
~~~~~~~~

UI tests verify the graphical interface:

* Located in ``tests/ui/`` directory
* Run with ``pytest tests/ui/``
* Use pytest-qt for Qt widget testing

Areas covered:

* Dialog interactions
* Form validation
* Event handling
* User workflows

Running Tests
------------

Complete Test Suite
~~~~~~~~~~~~~~~~~~

Run all tests with:

.. code-block:: bash

   pytest

Specific Test Categories
~~~~~~~~~~~~~~~~~~~~~~~

Run specific test categories:

.. code-block:: bash

   pytest tests/unit/  # Unit tests only
   pytest tests/integration/  # Integration tests only
   pytest tests/ui/  # UI tests only

Test Configuration
-----------------

Test configuration is managed through:

* ``pytest.ini`` - General pytest configuration
* ``conftest.py`` - Shared fixtures and settings
* ``.env.test`` - Test environment variables

Writing Tests
------------

Test Structure
~~~~~~~~~~~~~

.. code-block:: python

   def test_function_name():
       # Arrange
       # Set up test conditions

       # Act
       # Perform the action being tested

       # Assert
       # Verify the results

Best Practices
~~~~~~~~~~~~~

* Follow AAA pattern (Arrange-Act-Assert)
* Use meaningful test names
* One assertion per test when possible
* Use appropriate fixtures
* Mock external dependencies
* Include edge cases
* Test error conditions

Continuous Integration
--------------------

Tests are automatically run on:

* Pull request creation
* Main branch commits
* Release tagging

Code Coverage
------------

Code coverage is tracked using pytest-cov:

.. code-block:: bash

   pytest --cov=pulsarnet

Coverage reports are generated for:

* Line coverage
* Branch coverage
* Function coverage

Troubleshooting Tests
-------------------

Common Issues
~~~~~~~~~~~~

1. **Test Dependencies**

   Ensure all test dependencies are installed:

   .. code-block:: bash

      pip install -r requirements-dev.txt

2. **Environment Setup**

   Verify test environment configuration:

   * Correct Python version
   * Required system libraries
   * Test database access

3. **UI Test Issues**

   For UI test failures:

   * Check Qt version compatibility
   * Verify display server access
   * Review widget hierarchy

Maintaining Tests
---------------

Regular Maintenance
~~~~~~~~~~~~~~~~~

* Update test data and fixtures
* Review and update mocks
* Maintain test documentation
* Clean up obsolete tests
* Update test dependencies

Test Quality Metrics
~~~~~~~~~~~~~~~~~~

* Coverage percentage
* Test execution time
* Number of flaky tests
* Assertion density
* Code duplication in tests