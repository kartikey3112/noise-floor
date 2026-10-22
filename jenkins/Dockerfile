# Jenkins controller that can build CrashCart: git, uv and Python 3.14, with plugins, the
# admin user and the job all set up from files, so a fresh start needs no clicking.
FROM jenkins/jenkins:2.580.1-lts-jdk21

# uv installs Python and packages. Pinned so every build of this image gets the same tools.
COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /usr/local/bin/

# Install Python 3.14 once, in a shared folder every job can use.
USER root
ENV UV_PYTHON_INSTALL_DIR=/opt/uv-python
RUN uv python install 3.14 && chmod -R a+rX /opt/uv-python
USER jenkins

# plugins.lock.txt pins every plugin, dependencies included, to the exact versions last tested.
# plugins.txt is the short list it was made from.
COPY --chown=jenkins:jenkins plugins.lock.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

COPY --chown=jenkins:jenkins casc.yaml /opt/noisefloor/casc.yaml
COPY --chown=jenkins:jenkins jobs/ /opt/noisefloor/jobs/
COPY --chown=jenkins:jenkins Jenkinsfile /opt/noisefloor/Jenkinsfile

# Configuration as Code reads casc.yaml at start; the setup wizard is skipped because of it.
# Jobs may only use the Python installed above, never download another one.
ENV CASC_JENKINS_CONFIG=/opt/noisefloor/casc.yaml \
    JAVA_OPTS="-Djenkins.install.runSetupWizard=false" \
    UV_PYTHON_DOWNLOADS=never
