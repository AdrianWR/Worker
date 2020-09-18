FROM python:3.6.9-buster
LABEL maintainer="adrian.w.roque@gmail.com"

WORKDIR /usr/src/app

ARG CHROMIUM_VERSION=83.0.4103.116-1~deb10u3
ARG CHROMEDRIVER_VERSION=83.0.4103.39
RUN apt-get update && apt-get install -y chromium=$CHROMIUM_VERSION
RUN curl -LO https://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip && \
    unzip chromedriver_linux64.zip -d /usr/lib/chromium-browser						&& \
    ln -s /usr/lib/chromium-browser/chromedriver /usr/local/bin

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install tqdm

COPY worker.py ./
ENV PROJECT_ID		for-adrian
ENV URL_TABLE_ID	urls.articles
ENV DATA_TABLE_ID	mining.scielo

ENTRYPOINT ["python", "./worker.py"]
#CMD ["protein", "medicine", "virus", "20"]
