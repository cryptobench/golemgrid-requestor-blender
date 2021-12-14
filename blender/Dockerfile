# Dockerfile for tasks requiring Blender.
# Blender setup is based on
# https://github.com/ikester/blender-docker/blob/master/Dockerfile

FROM python:3.9

RUN apt-get update && \
    apt-get install -y \
    curl \
    bzip2 \
    libfreetype6 \
    libgl1-mesa-dev \
    libglu1-mesa \
    libxi6 \
    libxrender1 && \
    apt-get -y autoremove && \
    rm -rf /var/lib/apt/lists/*




RUN curl -s https://ftp.nluug.nl/pub/graphics/blender/release/Blender3.0/blender-3.0.0-linux-x64.tar.xz --output blender.tar.xz && tar -xf blender.tar.xz && mv blender-3.0.0-linux-x64 /blender
COPY run.sh /blender/run.sh
COPY cubes.blend /blender/cubes.blend
ENV PATH=/blender:/usr/bin/:$PATH
ENTRYPOINT ["tail"]
CMD ["-f","/dev/null"]
