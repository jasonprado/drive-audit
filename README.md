# drive-audit
Crawls files visible to a Google Drive service role and identifies files with
open sharing permissions. Results can be audited and approved in a Sheet.

## Setup
### Run once without OpenFAAS
* Create a [Google Workspaces service account](https://support.google.com/a/answer/7378726)
* Get google-credential.json for the service account
* Share the Drive folders you wish to crawl to the service account
* Create a new Sheet for the results. Note the ID.
* Copy `.env.example` to `.env` and edit it
* `python driveaudit/driveaudit.py`

### Run automatically in OpenFAAS and Kubernetes
Assuming you have `faas-cli` and `kubectl` configured and working.
* `faas-cli secret create drivebackup-config.env --from-file=.env`
* `faas-cli secret create drivebackup-google-credential.json --from-file=google-credential.json`
* `faas-cli deploy -f stack.yml`
* If `cron-connector` is installed, the function will execute daily.

### Build your own image
* `export DOCKER_USER=<your docker.io username>`
* `faas-cli publish -f stack.yml --platforms linux/arm/v7,linux/amd64`
* `faas-cli deploy -f stack.yml`
