# Local Jenkins

Jenkins runs in Docker and builds CrashCart's `noisefloor-demo` branch. Everything is set up
from the files in this folder, so a fresh start needs no clicking through setup screens.

| File | What it does |
|---|---|
| `Dockerfile` | Jenkins LTS plus uv and Python 3.14, with the files below baked in |
| `plugins.txt` | Plugins to install |
| `casc.yaml` | Configuration as Code: the admin user, one executor, and the job |
| `jobs/crashcart_tests.groovy` | Creates the `crashcart-tests` job, which takes a `COMMIT_SHA` parameter |
| `Jenkinsfile` | The job's steps: checkout, install, unit tests, start the backend, API tests, demo tests, publish JUnit |

## Start it

From the repo root:

```powershell
Copy-Item .env.example .env      # then set JENKINS_ADMIN_PASSWORD in .env
docker compose up -d --build
```

Open http://localhost:8080 and sign in with the user and password from `.env`.

## Why one executor

Each build starts its own CrashCart backend on port 8000, so two builds at once would clash.
One executor also keeps timings comparable from build to build, which runtime regression
detection depends on.
