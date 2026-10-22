// The one job Noisefloor reads: runs CrashCart's tests on one commit of noisefloor-demo.
// Created at start-up by Configuration as Code; the pipeline itself is jenkins/Jenkinsfile.
pipelineJob('crashcart-tests') {
    description('Runs CrashCart unit, API and demo tests on one commit and publishes JUnit ' +
                'results. Noisefloor ingests the history of this job.')
    parameters {
        stringParam('COMMIT_SHA', '', 'Commit to build. Empty means the tip of noisefloor-demo.')
    }
    definition {
        cps {
            script(new File('/opt/noisefloor/Jenkinsfile').text)
            sandbox(true)
        }
    }
}
