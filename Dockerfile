FROM continuumio/miniconda3

# Set the working directory in the container
WORKDIR /app

# Copy the environment.yml file into the container
COPY environment.yml .

# Create the Conda environment
RUN conda env create -f environment.yml

# Activate the environment and ensure it's activated when a shell is started
RUN echo "source activate bioextremes" > ~/.bashrc

# Update the PATH environment variable
ENV PATH=/opt/conda/envs/my_env/bin:$PATH

# Copy the rest of your application code into the container
COPY . .

RUN rm -rf .git

# Make your CLI scripts executable
RUN chmod +x /app/bin/*.py

ENV PYTHONPATH="/app"

# Set the default command to start an interactive shell
CMD ["/bin/bash"]
