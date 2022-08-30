# pull official python alpine image
FROM ubuntu:latest
ARG DEBIAN_FRONTEND=noninteractive

COPY ./app /app

# Making source and static directory
RUN mkdir -p /requestor/scene
RUN mkdir -p /requestor/output

# Creating Work Directory
WORKDIR /app

COPY start.sh /requestor/start.sh
# Adding mandatory packages to docker
RUN apt update && apt install -y \
    curl \
    git \
    python3 \
    python3-pip
# Installing temporary packages required for installing requirements.pip 
RUN apt install -y build-essential \
    python3-dev \ 
    jq

# Update pip
RUN pip3 install fastapi uvicorn python-multipart requests aiohttp
RUN pip3 install git+https://github.com/golemfactory/yapapi.git
RUN mkdir -p $HOME/.local/share/ya-installer/terms
RUN touch $HOME/.local/share/ya-installer/terms/testnet-01.tag
ENV PATH=${PATH}:/root/.local/bin/:/root/.local/
RUN mkdir /root/.local/bin
COPY blender.py /requestor/blender.py
COPY data.config /requestor/data.config
COPY utils.py /requestor/utils.py
COPY /yagna-builds /yagna

EXPOSE 80

# CMD will run when this dockerfile is running
CMD ["bash", "-c", "/requestor/start.sh; uvicorn main:app --host 0.0.0.0 --port 80"]