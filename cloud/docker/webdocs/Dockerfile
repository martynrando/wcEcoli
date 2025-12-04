# Container image: docs-flask
# This Dockerfile builds a container image to serve project documentation
# via a simple Flask web interface.
#
# To build this image locally from the project root directory:
#
#     > docker build -f docker/docs/Dockerfile -t ${USER}-docs-flask .
#
# After building, you can start a new container from the image:
#
#     > docker run --name docsserver -p 5000:5000 -it --rm ${USER}-docs-flask
#
# Then open http://localhost:5000 in your browser to view the documentation.

# Base image: use official Python slim image
FROM python:3.11-slim

# Record Docker Image metadata in ENV variables, viewable by `docker inspect`
ARG git_hash=""
ARG git_branch=""
ARG timestamp=""
ENV IMAGE_GIT_HASH="$git_hash" \
    IMAGE_GIT_BRANCH="$git_branch" \
    IMAGE_TIMESTAMP="$timestamp"

# Metadata labels
LABEL application="Project Documentation Server" \
      maintainer="eoin.martynrando@unimelb.edu.au" \
      license="MIT" \
      organization="MACSYS / University of Melbourne" \
      repository="https://github.com/martynrando/wcecoli"

# Set working directory in the container
COPY . /wcEcoli
WORKDIR /wcEcoli

RUN make clean compile
ENV PYTHONPATH=/wcEcoli

# Install Flask
RUN pip install --no-cache-dir flask

# Expose port for the Flask app
EXPOSE 5000

# Create directories for logs or cached files if needed
RUN mkdir -p /docs/logs

# Display a welcome message when starting the container
RUN (echo 'echo "Welcome to the Project Documentation Server!"' >> ~/.bashrc)

# Command to run the Flask app
CMD ["python", "docs/webdocs/app.py"]