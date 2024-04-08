# HyperLeda database app

## Development

To install reqired modules:

```bash
make install
```

To start application:

```bash
make runserver
```

Tests are located in `tests/`, to run them and all linters:

```bash
make test-all
```

Before commit run:

```bash
make fix-lint
```

### How to contribute new code

1. Clone repository locally:
    ```bash
    git clone https://github.com/HyperLEDA/db-app.git
    ```

2. Create new branch for the new feature (substitute `{number}` for issue number associated with the feature):
    ```bash
    git branch issue-{number}
    git checkout issue-{number}
    ```

3. Write new code
4. Run `make test-all` and ensure that it completes successfully.
5. Add and commit changes:
    ```bash
    git add .
    git commit -m "some cool message that briefly describes what you changed and why"
    ```
6. Push changes to the repository:
    ```bash
    git push origin issue-{number}
    ```
7. Navigate to https://github.com and create pull request. You should see it [here](https://github.com/HyperLEDA/db-app/pulls).
8. Wait until all checks become successfull (or fix the code if they are not).
9. Request review from the team member or merge it with `master` if you are sure.
