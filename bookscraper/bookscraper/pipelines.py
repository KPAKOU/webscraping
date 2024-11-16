# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
from itemadapter import ItemAdapter


#class BookscraperPipeline:
#   def process_item(self, item, spider):
#        return item


import boto3
import csv
from io import StringIO
import pandas as pd

class S3Pipeline:
    def __init__(self, aws_access_key_id, aws_secret_access_key, bucket_name, file_format):
        self.s3 = boto3.client(
            's3',
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key
        )
        self.bucket_name = bucket_name
        self.file_format = file_format
        self.items = []  # Stock des items en mémoire

    @classmethod
    def from_crawler(cls, crawler):
       return cls(
           aws_access_key_id=crawler.settings.get('ACCESS_KEY'),
           aws_secret_access_key=crawler.settings.get('SECRET_ACCESS'),
           bucket_name=crawler.settings.get('BUCKET_NAME'),
           file_format=crawler.settings.get('FILE_FORMAT')  # JSON ou CSV
       )

    def process_item(self, item, spider):
        # Ajout de chaque item dans la liste
        self.items.append(dict(item))
        return item

    def close_spider(self, spider):
        # Appel de la fonction d'upload à la fin du scraping
        if self.file_format == 'csv':
            self.upload_csv()
    def upload_csv(self):
        object_name = 'books_data.csv'
        try:
            # Check if file exists
            self.s3.head_object(Bucket=self.bucket_name, Key=object_name)
            existing_data = self.download_existing_csv(object_name)
        except self.s3.exceptions.ClientError:
            existing_data = pd.DataFrame()

        # Convert new data to DataFrame
        new_data = pd.DataFrame(self.items)
        
        # Combine new data with existing data, avoiding duplicates
        combined_data = pd.concat([existing_data, new_data], ignore_index=True)

        # Upload updated data
        csv_buffer = StringIO()
        combined_data.to_csv(csv_buffer, index=False)
        self.s3.put_object(Bucket=self.bucket_name, Key=object_name, Body=csv_buffer.getvalue())
        print(f"Fichier CSV {object_name} mis à jour et uploadé sur S3.")
    def download_existing_csv(self, object_name):
        response = self.s3.get_object(Bucket=self.bucket_name, Key=object_name)
        csv_content = response['Body'].read().decode('utf-8')
        return pd.read_csv(StringIO(csv_content))
