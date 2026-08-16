=======
History
=======

0.3.0 (2026-08-16)
------------------

* Added: ``target`` accepts ``suffix=True``, matching a specifier at the *end* of a format spec rather than as the
  whole of it. This makes compound specifiers work — ``f"{x:.3ft}"`` resolves to the ``ft`` target with ``.3`` left
  over as an ordinary format spec. When several suffixes match, the longest wins.
* Added: a target may now take a third argument, which receives the standard format spec preceding the matched
  specifier. The two argument form receives the matched specifier, which is unchanged for exact matches.
* Added: ``Resolution``, the named tuple returned by ``compute_formatting_func`` and ``compute_target``, carrying
  the target, the matched specifier and the leftover standard spec. Both functions previously returned a bare
  callable.
* This is the unit-formatting use case the library was originally written for. It never worked before: specifier
  lookup was exact-match only, so ``f"{x:.3ft}"`` fell through to ``float.__format__`` and raised ``ValueError``.

Suffix matching is opt-in per target, and remains unavailable on ``formatmethod`` and on the ``formattable``
keyword arguments. Note that suffix matching is done on raw spec text, so a suffix colliding with a built-in
presentation type (``b c d e E f F g G n o s x X %``) will capture ordinary format specs.

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
