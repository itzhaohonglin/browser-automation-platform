# Import Data Directory

This directory is used for batch importing tasks from a text or CSV file.

## Usage

1. Create a text (.txt) or CSV (.csv) file with one registration number per line
2. Place it in this directory
3. Run `batch_import.bat` from the parent directory
4. Enter the filename when prompted

## File Format

One registration number per line. Lines starting with `#` are ignored.

### Example File Content (jobs.txt)

```
滇械注准20192140008
京械注准20210001234
沪械注准20200005678
```

### CSV Format Example

A CSV file with one registration number per line works the same way:

```csv
滇械注准20192140008
京械注准20210001234
```

**Notes**:
- The file must be UTF-8 encoded
- Excel (.xlsx) is not supported - save as CSV instead
- The NHSA config must be initialized first (run `init_config.bat` from the parent directory)

## Getting config_id

The import uses the NHSA registration query config created by `init_config.bat`
(usually config_id = 44). To verify:

1. Start the service: `startup.bat`
2. Visit: http://127.0.0.1:8000/static/index.html
3. Go to "Configuration Management"
4. Check the ID column

## More Information

See the full documentation: `docs\CLIENT_DATA_IMPORT_GUIDE.md`
