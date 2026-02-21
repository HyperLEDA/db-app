### Running checks and tests

To check the code against static checks and possibly some tests, run:

```shell
make check
```

Sometimes some errors this command produces (such as import sorting) can be fixed automatically using:

```shell
make fix
```

If the check command fails, make sure to always run the fix command first prior to trying to fix changes yourself.
