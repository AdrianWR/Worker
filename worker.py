# -*- coding: utf-8 -*-
"""scielo_worker

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1sZCFg8z6AW2RxQ6xqHdrEv_je7y5tWt2

# **scielo.br** data mining with CENTAUR Miner
"""


from google.oauth2.service_account import Credentials
import pandas_gbq
import os

# Google BigQuery Authentication. At first, we'll try to fetch
# authentication data from a 'credentials.json' file at our 
# working directory. If this file doesn't exist, we authenticate
# with web login.

try:
    cred_file = os.environ["GOOGLE_APPLICATION_CREDENTIALS"]
    credentials = Credentials.from_service_account_file(cred_file)
except (KeyError, FileNotFoundError):
    print("Invalid credentials. Set GOOGLE_APPLICATION_CREDENTIALS to your credentials file.");
    exit(1);

# Main database schema, as extracted from Nature BREATE table
mining_schema = [
    {"name": "abstract",                "type": "STRING", "mode": "REQUIRED"  },
    {"name": "acquisition_date",        "type": "DATE"                        },
    {"name": "authors",                 "type": "STRING"                      },
    {"name": "body",                    "type": "STRING"                      },
    {"name": "date",                    "type": "DATE"                        },
    {"name": "doi",                     "type": "STRING"                      },
    {"name": "keywords",                "type": "STRING"                      },
    {"name": "link",                    "type": "STRING"                      },
    {"name": "organization_affiliated", "type": "STRING"                      },
    {"name": "pdf_link",                "type": "STRING"                      },
    {"name": "references",              "type": "STRING"                      },
    {"name": "source",                  "type": "STRING"                      },
    {"name": "title",                   "type": "STRING", "mode": "REQUIRED"  },
    {"name": "id",                      "type": "STRING", "mode": "REQUIRED"  }
]

url_schema = [
    {'name': 'article_url', 'type': 'STRING',   'mode': 'REQUIRED'},
    {'name': 'catalog_url', 'type': 'STRING',   'mode': 'REQUIRED'},
    {'name': 'is_pdf',      'type': 'INTEGER',  'mode': 'REQUIRED'},
    {'name': 'language',    'type': 'STRING'                      },
    {'name': 'status',      'type': 'STRING',   'mode': 'REQUIRED'},
    {'name': 'timestamp',   'type': 'DATETIME', 'mode': 'REQUIRED'},
    {'name': 'worker_id',   'type': 'STRING'                      },
    {'name': 'meta_info',   'type': 'STRING'                      }
]

# Project, dataset and table configuration
pandas_gbq.context.credentials = credentials
project_id   = os.environ["PROJECT_ID"]
url_table_id = os.environ["URL_TABLE_ID"]
mining_table_id = os.environ["DATA_TABLE_ID"]

"""# CENTAUR Miner Mining Class

## Collect URLS from Search Mechanism

Due to particularities with Scielo, I had to modify CENTAUR Miner `CollectURLS` function to work nicely with this database. First of all, Scielo *next page* button was not interactable by Selenium, so I had to wrap around the `go_to_page()` JavaScript function to navigate through the search results on Scielo. I decided to get the page number from the form sent to POST request on Scielo, instead of the counter. Moreover, the script wouldn't finish at the search end, so I had to detect an Element whose only appearance was at a search fail.

Finally, the results were stored as a JSON file, `articles.json`, to be mined later.

# Scielo Locations and Engine
"""

# Title                                                     ok
# DOI (Digital Object Identifier)                           ok
# Authors                                                   ok
# Abstract                                                  ok
# Date                                                      ok
# Source(what journal we got it from)                       ok
# Category (genomics for example)                           ok
# Licensing                                                 ok
# Date of the document acquisition                          ok
# Full body                                                 ok 
# Keywords                                                  ok
# References                                                ok
# Link                                                      ok
# PDF link                                                  ok
# Organization affiliated                                   ok
# Source impact factor (tiers)
# Search keyword (used to find this document)
# Quantity of citations

from dateutil.parser import parse
import centaurminer as mining
import time
import uuid

class ScieloLocations(mining.PageLocations):
    """Locations on the page to be gathered by Selenium webdriver
    
    The locations may be declared here as static variables of any type, to be retrieved
    as keys on the centaurminer.MiningEngine.results dictionary. Some examples of data that
    can be declared here:

    centaurminer.Metadata: Selenium retrieved elements from a page metadata
    centaurminer.Element: Selenium retrived elements from a page body.
    string: Strings declared here won't change, independently of the page searched.
    """

    source = mining.MetaData("citation_journal_title")
    date_publication = mining.Element("css_selector", "h3")
    body = mining.Element("css_selector", "#article-body, .index\,pt > p, .index\,en > p, .index\,es > p")
    abstract = mining.Element("css_selector", ".trans-abstract > p:not([class^=sec]), .trans-abstract > div.section")
    keywords = mining.Element("css_selector", ".trans-abstract > p:last-of-type")
    references = mining.Element("css_selector", "p.ref")
    organization_affiliated = mining.Element("css_selector", "p.aff").get_attribute('innerHTML')
    license = "https://scielo.org/en/about-scielo/open-access-statement/"
    id = mining.Complex()
    pass

class ScieloEngine(mining.MiningEngine):
    """Mining Engine to get data from elements declared on centaurminer.PageLocations

    Here it's possible to process elements retrieved from centaurminer.PageLocations
    before gathering the results as a dictionary. To modify a specific element, declare
    a new method in the form get_<key>.

    Example:
        def get_authors(self, element):
            return TagList(self.get(element, several=True))
    """

    #########################
    ### Utilities Methods ###
    #########################
    
    @staticmethod
    def TagList(str_list, tag="item"):
        """ Returns a string from a joined list with elements separated by HTML-like tags
        Note:
            This method is overwritting base class centaurminer.MiningEngine
            default `CollectURLs` method.
        Args:
            str_list (list):     List of strings to be joined with HTML-like tags.
            tag (str, optional): Tag used to separate the elements in the form <></>  
        Returns:
            A string containing the list elements separated by HTML-like tags,
            None if str_list is None or empty.
        """
        if str_list:
            return ''.join(map(lambda s: f'<{tag}>{s.strip()}</{tag}>', str_list))
        return None

    @staticmethod
    def __format_author(author):
        """Formats a single author entry in full name format."""
        author = ' '.join(author.split(",")[::-1])
        return author.title().strip()

    @staticmethod
    def __parse_keywords(keys):
        """Extract keywords from HTML element"""
        key_strings = [ 
                    "keywords",
                    "key words",
                    "palavras-chave",
                    "palavras chave",
                    "index terms",
                    "descritores"
                  ]
        if not keys:
            return None
        for i in key_strings:
            if keys.lower().startswith(i):
                keys = keys[len(i):]
        return keys.replace(':', ' ').replace(';',',').split(',')

    ##################################
    ### Element Processing Methods ###
    ##################################

    def get_id(self, element):
        """Return unique identifier for article ID."""
        return str(uuid.uuid4())


    def get_abstract(self, element):
        """Fetch abstract information from article URL."""
        return '\n'.join(self.get(element, several=True))


    def get_body(self, element):
        """Gather body text from article URL
        Note: 
            If body is retrieved from #article-body selector, it's safe
            to assume that it'll be pretty formatted. Otherwise, it's
            required to process <p> tags to retrieve body information.
        Args:
            element(:obj: `centaurminer.Element`): Page element to gather body data from.
        Return:
            String comprising whole body data
        """
        body = self.get(element, several=True)
        # Return if get from #article-body selector
        if len(body) == 1:
            return body[0]
        cleaned_paragraphs = []
        try:
            for idx, p in enumerate(body):
                if p.lower() in ["resumo", "abstract", "resumen"]:
                    abstract_index = idx
        # Clean up and join the paragraphs    
            for p in body[:abstract_index]:
                p = p.replace('&nbsp;',' ').strip()
                just_whitespace = all(char == " " for char in p)
                if not just_whitespace:
                    cleaned_paragraphs.append(p)
        except:
            pass
        if not len(cleaned_paragraphs):
            return None 
        return "\n".join(cleaned_paragraphs)


    def get_date_publication(self, element):
        """"Gather article date publication, in YYYY-MM-DD format
        Args:
            element(:obj: `centaurminer.Element`): Page element to
                gather body data from.
        Return:
            String representing date publication, in format YYYY-MM-DD.
        """
        try:
            return str((self.get(element).split('Epub')[1]).date())
        except (AttributeError, IndexError):
            return None

    def get_organization_affiliated(self, element):
        """Returns a string with article authors organizations, separated by HTML-like elements"""
        orgs = [o.split('</sup>')[-1] for o in self.get(element, several=True)]
        return self.TagList(orgs, "orgs")

    def get_references(self, element):
        """Returns a string with article references, separated by HTML-like elements"""
        reflist = self.get(element, several=True)
        refs = [r.replace('[ Links ]', '').strip('0123456789. ') for r in reflist]
        return self.TagList(refs)

    def get_authors(self, element):
        """Returns a string with article authors from search engine, separated by HTML-like elements"""
        authors = map(self.__format_author, self.get(element, several=True))
        return self.TagList(list(dict.fromkeys(authors)), 'author')

    def get_keywords(self, element):
        """Gather article keywords from centaurminer.Element object.
        Args:
            element(:obj: `centaurminer.Element`): Page element to gather keywords from.
        Returns:
            String comprising keywords separated by HTML-like tags.
        """
        keys = self.__parse_keywords(self.get(element))
        return self.TagList(keys, "keyword")

    def gather(self, url):
        """Retrieve mined information from a specific URL"""
        super().gather(url)
        self.results['acquisition_date'] = self.results.pop('date_aquisition')
        self.results['date']             = self.results.pop('date_publication')
        self.results['pdf_link']         = self.results.pop('extra_link')
        self.results['link']             = self.results.pop('url')
        if not self.results['abstract']:
            self.results['abstract'] = self.results['body']
            if not miner.results['abstract'] or not self.results['title']:
                self.results = None
        pass

"""# Worker

Here I'm trying to implement a scalable algorithm to mine data from URLs available at Google BigQuery. At first, the worklow is divided in three main steps:

1. Connect to Google Bigquery with own `credentials`, `project_id` and URL and mining job `table_id`.
2. Get not mined URLs from BigQuery, return them to a list and assign them to a worker machine and to _Working On_ status.
3. Mine these URLs to a new table and assign them to _Done_ status on the URLs table.
"""

import pandas as pd
import pandas_gbq
import datetime
import time
import uuid


class Worker():
    """Create and submit data mining jobs to Google Bigquery

    This class aims to create mining jobs in specified articles databases.
    It supports multithreading, so it might be usable on a cluster environment
    Pay attention to submit a valid pandas_gbq to client to dump data into
    the Google BigQuery
    """


    def __init__(self, miner):
      """Create job dispatcher object

      Args:
          miner (:obj: `centaurminer.Mining`): Mining Engine based on centaur
            Miner project. It should contains at least `abstract`, `title` and
            `id` elements declared. The `CollectURLs` method can be overwritten.
      """
      self.miner = miner
      

    def register_job(self, worker_id, limit):
        """Gather not mined URLs from BigQuery and subscribe them to a job
        Args:
            worker_id (string): Worker machine unique identifier.
            limit (int): Max number of URLs to gather.
        Returns:
            List of URLs available to mine data from, upon limit.
        """
        # Gather not mined urls
        df = pandas_gbq.read_gbq(
            f"""
            SELECT article_url, catalog_url, is_pdf, language, meta_info
            FROM (
                SELECT *, ROW_NUMBER() OVER
                (PARTITION BY article_url ORDER BY timestamp DESC) AS rn
                FROM {self.url_table}
            )
            WHERE rn = 1 AND status='Not Mined' AND is_pdf = 0
            ORDER BY timestamp
            LIMIT {limit};
            """,
            project_id = self.project_id)
        if len(df):
            # Add more information to dataframe
            df['status']    = 'Working On'
            df['worker_id'] = worker_id
            df['timestamp'] = datetime.datetime.utcnow()
            # Dump new dataframe to GBQ and return it to further processing.
            pandas_gbq.to_gbq(df, url_table_id, project_id, if_exists='append', table_schema=self.url_schema)
        return df


    def mine_from_list(self, urls, delay_time=1):
        """Mine all the elements in a list of urls.
        Args:
            urls (list): List of urls to catch data from.
            miner (:class:`centaurminer.MiningEngine`) An engine used to
                extract data from each url page.
            delay_time (int, optional): Delay time before mining the next
                article from list, in seconds.
        Return:
            List of dictionaries of data mined from urls.
        """
        data = []
        for i in urls:
            self.miner.gather(i)
            if self.miner.results:
                data.append(self.miner.results)
            time.sleep(delay_time)
        return data


    def job_executor(self, limit, delay_time=1, worker_id=uuid.uuid1()):
        """Get URLs and mine them to send to BigQuery
        Args:
            miner (:class:`centaurminer.MiningEngine`) An engine used to
                extract data from each url page.
            worker_id (string): Worker machine unique identifier.
            limit (int, optional): Max number of urls to mine data from.
            delay_time (int, optional): Delay time before mining the next
                article from list, in seconds.
        Returns:
            Number of URLs mined and processed
        """
        dataframe_to_mine = self.register_job(worker_id, limit)
        if not len(dataframe_to_mine):
            return 0
        # Mine data and send to BigQuery
        mined_data = pd.DataFrame(self.mine_from_list(list(dataframe_to_mine['article_url']), delay_time))
        pandas_gbq.to_gbq(mined_data, self.job_table, self.project_id, if_exists='append', table_schema=self.job_schema)
        # Update URL status on URL BigQuery Table
        url_df = dataframe_to_mine
        url_df['status'] = 'Done'
        url_df['worker_id'] = worker_id
        url_df['timestamp'] = datetime.datetime.utcnow()
        # Update URL status's on BigQuery and return number of URLs mined
        pandas_gbq.to_gbq(url_df, self.url_table, self.project_id, if_exists='append', table_schema=self.url_schema)
        return len(url_df)


    @classmethod
    def connect_to_gbq(cls, credentials, project_id, url_table_id, job_table_id,
                       url_schema=None, job_schema=None):
        """ Establish a connection with Google BigQuery
        Args:
            credentials (:obj: `google.auth.credentials.Credentials`):
                Google Authentication credentials object, required to
                authorize the data workflow between this class and the
                database. Can be declared from service or user account.
            project_id (string): Google Cloud project ID.
            url_table_id (string): Table information to read and write URL data
                on. Must be specified as `<dataset_name>.<table_name>`.
            job_table_id (string): Table information to read and write mining
                data on. Must be specified as `<dataset_name>.<table_name>`.
            schema (`list` of `dict`: optional): Optional databse schema to
                input while working with `pandas_gbq` module. If `None`, the
                schema will be inferred from `pandas.DataFrame` object.
        Example:
            URLBuilder.connect_to_gbq(google-credentials, 'MyProject',
              'my_dataset.my_url_table', 'my_dataset.my_job_table',
              [{'name': 'url', 'type': 'STRING'}]), [{'name': 'title', 'type': 'STRING'}]).
        Auth_docs:
            Reference for Google BigQuery Authentication, on this context:
            'https://pandas-gbq.readthedocs.io/en/latest/howto/authentication.html'
        """
        cls.credentials = credentials
        cls.project_id = project_id
        cls.url_table = url_table_id
        cls.job_table = job_table_id
        cls.url_schema = url_schema
        cls.job_schema = job_schema
        pass

"""## `Worker` Simple Example

Here's how a real approach could be done on a Deployment on GCP. Assigned the `ScieloEngine`, the GBQ connections and a instance of the `Worker` class, all left to do is to call the `job_executor` function with the amount of URLs required to gather data from.
"""

import sys

miner = ScieloEngine(ScieloLocations, driver_path='/usr/lib/chromium-browser/chromedriver')
Worker.connect_to_gbq(credentials, project_id, url_table_id, mining_table_id, url_schema, mining_schema)
worker = Worker(miner)

worker.job_executor(limit = sys.argv[1])