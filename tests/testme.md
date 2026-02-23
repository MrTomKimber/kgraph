# Tests
## To run tests in development, execute the following
pytest --cov=kgraph --cov-fail-under=75 -l

## And for a more verbose run, export the contents of stdio and include coverage pointers
pytest --cov=kgraph --cov-fail-under=75 --cov-report=term-missing -ls

