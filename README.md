# fabric8-gemini-server
Fabric8-server analytics powered services to initiate and report the readiness of
all registered services

### ENDPOINTS

#### POST: /api/v1/register
```
{
	"git_url" : <some_url>,
	"git_sha" : <some_sha>,
	"email_ids" : <some_email>
}

```

##### Result :
`Status: 200 OK`
```
{
  "data": {
    "email_ids": <some_email>,
    "git_sha": <some_sha>,
    "git_url": <some_url>,
    "last_scanned_at": "Mon, 05 Mar 2018 00:00:00 GMT"
  },
  "success": true,
  "summary": "<some_url> successfully registered"
}
```
### Footnotes

#### Coding standards

- You can use scripts `run-linter.sh` and `check-docstyle.sh` to check if the code follows [PEP 8](https://www.python.org/dev/peps/pep-0008/) and [PEP 257](https://www.python.org/dev/peps/pep-0257/) coding standards. These scripts can be run w/o any arguments:

```
./run-linter.sh
./check-docstyle.sh
```

The first script checks the indentation, line lengths, variable names, white space around operators etc. The second
script checks all documentation strings - its presence and format. Please fix any warnings and errors reported by these
scripts.

#### Code complexity measurement

The scripts `measure-cyclomatic-complexity.sh` and `measure-maintainability-index.sh` are used to measure code complexity. These scripts can be run w/o any arguments:

```
./measure-cyclomatic-complexity.sh
./measure-maintainability-index.sh
```

The first script measures cyclomatic complexity of all Python sources found in the repository. Please see [this table](https://radon.readthedocs.io/en/latest/commandline.html#the-cc-command) for further explanation how to comprehend the results.

The second script measures maintainability index of all Python sources found in the repository. Please see [the following link](https://radon.readthedocs.io/en/latest/commandline.html#the-mi-command) with explanation of this measurement.

