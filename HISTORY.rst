=======
History
=======

0.2.0 (2026-08-16)
------------------

Behavior
~~~~~~~~

* Fixed: a bare ``@target`` (applied with no specifier) now registers the *empty* format specifier, matching both
  ``formatmethod`` and ``target``'s own docstring. Previously it registered nothing at all, so ``f"{obj}"`` silently
  fell through to the default ``__format__``.
* ``SimpleFormatterError`` is now exported from the package root, and ``__all__`` is declared.

Documentation
~~~~~~~~~~~~~

* Fixed the three failing module doctests. Two referenced a ``reg=`` keyword argument removed back in 2019.
* README rewritten. It now links the Stack Overflow question the library came from, records why custom specifiers on
  built-in types are out of scope, and documents the exact-match specifier limitation — a registered ``ft`` target
  does not match the specifier ``.3ft``. The previous README advertised compound specifiers that were never
  implemented.
* Documented the resolution order between ``formatmethod``, ``formattable``, ``target`` and the original
  ``__format__``.

Packaging and CI
~~~~~~~~~~~~~~~~

* Minimum supported Python is now 3.10. Tested against 3.10, 3.11, 3.12 and 3.13.
* Moved to a PEP 621 ``pyproject.toml``. Removed ``setup.py``, ``setup.cfg``, ``pytest.ini``, ``bumpversion``
  configuration, the universal-wheel setting and the ``pytest-runner`` dependency.
* Replaced Travis CI with GitHub Actions. Removed ``.travis.yml`` and the three ``requirements_*.txt`` files in
  favor of ``dev`` and ``docs`` extras.
* Updated the Read the Docs configuration to the current schema.

0.1.0 (2019-05-21)
------------------

* First release on Github.
