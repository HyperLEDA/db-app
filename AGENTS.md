## Development

### Running checks

To check the code against static checks, run:

```shell
make check
```

Sometimes errors this command produces (such as import sorting) can be fixed automatically using:

```shell
make fix
```

If the check command fails, make sure to always run the fix command first prior to trying to fix changes yourself.

### Scripts and Python Execution

This project uses `uv` for package management. `uv` manages virtual environments as well, meaning that simple running of `python` command will not work. Always use `uv run` instead of raw `python` or `python3`:

```bash
# Correct
uv run python script.py
uv run python -c "print('Hello World')"

# Incorrect
python script.py
python3 script.py
```

## Codestyle guidelines

### Logging

Unless specifically asked, do not add new logs to the code.

### Comments

Only add comments to code where non-obvious decisions were made. If the code is straightforward and self-explanatory, do not comment it.

Unless explicitly instructed otherwise, do not write docstrings for functions, classes, or modules.

### Type hints

Use type hints in function and class signatures as much as possible to improve code clarity and IDE support. In particular, always use type hint in following cases:

- Function parameters and return types
- Class attributes and methods
- Generic types and collections

Avoid using `Any` in type hints. Prefer more specific types or generic types when possible.

### Imports

Prefer importing modules rather than individual symbols from modules. This improves code readability and makes dependencies clearer. In particular:

```python
# prefer
import numpy as np
import pandas as pd

# avoid
from numpy import ndarray, array
from pandas import DataFrame
```

The only exception to the above rule is for imports from the `typing` or `collections.abc` package. These should be imported directly:

```python
from typing import Any
from collections.abc import Sequence
```

### Exporting symbols

When adding a new exportable function, class, or other symbol, add it to `__all__` inside the `__init__.py` of the corresponding directory. A symbol is deemed exportable only if it is used in other business logic of the project. If it is only used inside the same directory or in tests from the `tests/` directory, it should not be exported through `__all__`.

### Astropy Package Guidelines

When using `astropy` units, use runtime units determination instead of direct attribute access. In particular:

```python
from astropy import units as u

# prefer
u.Unit("kpc")
u.Unit("km/s")

# avoid
u.kpc
u.km / u.s
```
