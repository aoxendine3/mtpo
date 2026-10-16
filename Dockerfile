# MTPO Standalone Independent Verification Container
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    clang \
    make \
    python3 \
    python3-pip \
    python3-setuptools \
    z3 \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . /app

RUN make all
CMD ["make", "test"]
