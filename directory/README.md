run 
FLASK_APP=directory/web.py flask run --reload 

post 
curl -X POST -H "Content-Type: application/json" -d @directory/example.json http://localhost:5000/store