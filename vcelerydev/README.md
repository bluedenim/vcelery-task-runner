# Publish Notes

## Test PyPI
```
rm -f dist/*
docker-compose run --rm app /bin/bash

python -m build

twine upload --repository-url https://test.pypi.org/legacy/ dist/*
(Enter API Token)
```

To test from another client app:
```
pip install --index-url https://test.pypi.org/simple/ \
--extra-index-url https://pypi.org/simple/ vcelery-task-runner==<release>
```


## PyPI
```
rm -f dist/*
docker-compose run --rm app /bin/bash

python -m build

twine upload dist/*
(Enter API Token)
```