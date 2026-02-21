### Running checks and tests

To check the code against static checks, run:

```shell
make check
```

Sometimes errors this command produces (such as import sorting) can be fixed automatically using:

```shell
make fix
```

If the check command fails, make sure to always run the fix command first prior to trying to fix changes yourself.

### Logging

Unless specifically asked, do not add new logs to the code.

### Comments

Only add comments to code where non-obvious decisions were made. If the code is straightforward and self-explanatory, do not comment it.

Unless explicitly instructed otherwise, do not write docstrings for functions, classes, or modules.
