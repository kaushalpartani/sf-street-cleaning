# sf-street-cleaning
Click a neighborhood, find a street, and add a reminder to your calendar! Data sourced from DataSF.

This project uses poetry for dependency management.

```
poetry install
```

Running transformations locally requires the `DATA_PATH` env var. Run the transformations script from within the virtual env.
```commandline
export DATA_PATH="/Users/kaushal/workplace/sf-street-cleaning/data"
python transformations.py
```

## TODO
- [ ] Update cicd to remove the pin on poetry version and use a 2.x version instead