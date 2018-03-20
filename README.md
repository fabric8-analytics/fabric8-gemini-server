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
