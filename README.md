## Flask Calendar App with ElasticSearch

### User registration and login validation through MySQL, and document data storage in MongoDB
### ElasticSearch with paginition feature

## Getting Started

* the app was tested under python 3.6
* pip install -r /path/to/requirements.txt
* Install ElasticSearch locally, and run elasticsearch.bat in the bin folder. Listen at Port 9200
* Configure .env file by specifying the following env variables with real settings.
      SECRET_KEY=''
      SQLALCHEMY_DATABASE_URI=''
      MONGO_DBNAME=''
      MONGO_URI = ''
* The app will create `users` table in MySQL, and Calendar collection in MongoDB. Make sure the schema has no conflictions with existing ones.

### Congratulations!
You've successfully set up the Flask Calendar App with ElasticSearch project on your local development machine! Enjoy!

## Authors
* __Qingguo Chen__  email: qchen325@gatech.edu
