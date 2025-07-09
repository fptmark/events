Structure:
  Top level events dir
  app dir for python
  ui dir for Angular

Requirements:
1. Python 3
2. Angular 19.1
3. Mongo
4. ElasticSearch (optional)

Setup:
1. Install the python libraries using requirements.txt
2. Run the server:
     PYTHONPATH=. python app/main.py mongo.json - use es.json for ES


If you see no errors, you can verify the server is running from the browser URLS:
http://localhost:5500/api/metadata
http://localhost:5500/api/user/

Once that is running ok, you can fire up the angular code just using “ng serve” and then navigate to http://localhost:4200/

