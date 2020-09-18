# AIvsCOVID19 Site Worker

## Motivation
This repository contains a simple setup to create a *Worker* instance to act in the context of Data Mining workflow in the AIvsCOVID19 project. The Site Worker is a special type of data mining Python script; given a table on the BigQuery with links to scientific articles on the web, the ` `e `Worker` will iterate through each record and then mine valuable information from each article, sending the results to another BigQuery table.

### Installation

Before proceeding, it's not advised to run this scraper on your local machine, as some websites may block yor IP address upon a number of requests on a particular domain. When data mining, be assured to follow very stricit ethical guidelines before running your process, to not clog up domain servers from scientific websites. **Be polite while mining data**.  

#### With Docker
The most common way to run this Worker script is to run it on a Docker container, as the dependencies will be updated to the latest working Python packages. To download the repository and build the Docker image, you can run the following command:

    git clone https://github.com/AdrianWR/worker.git
    docker build -t IMAGE_NAME worker

### Getting Started
At the moment of running the container, it's required to set up some environment variables at the runtime, related to the BigQuery authentication and authorization workflow. The followinf variables must be set:
- `PROJECT_ID`: Name of the Google Cloud project;
- `URL_TABLE_ID`: In the format `dataset_id`.`table_id`. Required to declare the dataset to retrieve article links from, to extract data further on. Example: *urls.articles*;
- `DATA_TABLE_ID`: In the format `dataset_id`.`table_id`. Required to declare the dataset to insert the information extracted from the articles. Example: *mining.my-website*;
- `GOOGLE_APPLICATION_CREDENTIALS`: Credentials file associated with the account with BigQuery permissions. On instructions with how to set up your credentials, follow [Service accounts](https://cloud.google.com/iam/docs/service-accounts). The following role permissions must be defined to the correct runtime of the Worker:


    - `bigquery.jobs.create`
    - `bigquery.tables.create`
    - `bigquery.tables.get`
    - `bigquery.tables.updateData`

To run the container on its own, it's possible to use the following command:
```
    docker run --rm -d
    --env PROJECT_ID="my-project"
    --env URL_TABLE_ID="my-url-dataset.my-links"
    --env DATA_TABLE_ID="my-data-dataset.my-website"
    --env GOOGLE_APPLICATION_CREDENTIALS=/credentials.json
    --mount type=bind,source="$(pwd)"/credentials.json,target=/credentials.json,readonly
    IMAGE_NAME LIMIT
```

The `LIMIT` variable is an integer, representing how many links to extract data from and send to the data BigQuery table.
