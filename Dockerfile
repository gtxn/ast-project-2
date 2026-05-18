FROM --platform=linux/amd64 theosotr/sqlite3-reducer

USER root

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/reducer

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY sqlite_reducer/ /opt/reducer/sqlite_reducer/
COPY queries/ /opt/reducer/queries/
COPY reducer.py /opt/reducer/reducer.py

ENV PYTHONPATH=/opt/reducer

RUN printf '#!/bin/sh\nexec python3 /opt/reducer/reducer.py "$@"\n' \
    > /usr/bin/reducer && chmod +x /usr/bin/reducer

ENTRYPOINT ["/usr/bin/reducer"]
CMD []