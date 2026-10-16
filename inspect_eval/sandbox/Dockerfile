# Image in which the generated tests are executed (one container per sample and epoch).
# Same Python and libraries as the study's image (study/Dockerfile), pinned to the
# versions it resolved at the time this evaluation was written.
FROM python:3.13-slim
RUN pip install --no-cache-dir hypothesis==6.168.5 pytest==9.1.1
RUN useradd -m runner && mkdir /work && chown runner /work
USER runner
WORKDIR /work
