"""
pip install elasticsearch

document: https://www.elastic.co/guide/en/elasticsearch/reference/7.0/index.html

https://www.elastic.co/cn/downloads/elasticsearch

Run bin/elasticsearch (or bin\elasticsearch.bat on Windows)

Run curl http://localhost:9200/ or Invoke-RestMethod http://localhost:9200 with PowerShell

from elasticsearch import Elasticsearch
#client = Elasticsearch(host="127.0.0.1", port=9200)
client = Elasticsearch(['localhost:9200'])
"""

__author__ = 'Carson'

import json
from elasticsearch import Elasticsearch


if __name__ == '__main__':
    host = 'localhost:9200'
    conn = Elasticsearch([host])
    dict_info = conn.info()
    print(f"Elasticsearch VERSION: {dict_info['version']['number']}")