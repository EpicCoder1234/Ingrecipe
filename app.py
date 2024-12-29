from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
import datetime
from functools import wraps
import requests
from bs4 import BeautifulSoup

app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://ingrecipe_data_user:yKVffwrDkDMPdZUpYfSX1g0xBrhceRDJ@dpg-ctorhq23esus73dcg9p0-a/ingrecipe_data'
db = SQLAlchemy(app)

# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    ingredients = db.Column(db.Text, nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(300))

# Authentication decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('x-access-token')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 403
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.filter_by(id=data['id']).first()
        except:
            return jsonify({'message': 'Token is invalid!'}), 403
        return f(current_user, *args, **kwargs)
    return decorated

# Routes
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    hashed_password = generate_password_hash(data['password'], method='sha256')
    new_user = User(username=data['username'], password=hashed_password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully!'}), 201

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    user = User.query.filter_by(username=data['username']).first()
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Login failed!'}), 401
    token = jwt.encode({'id': user.id, 'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24)}, app.config['SECRET_KEY'])
    return jsonify({'token': token})

@app.route('/recipes', methods=['GET'])
@token_required
def get_recipes(current_user):
    ingredients = request.args.get('ingredients', '').split(',')
    matching_recipes = Recipe.query.filter(
        db.or_(Recipe.ingredients.like(f"%{ingredient.strip()}%") for ingredient in ingredients)
    ).all()
    return jsonify([{
        'name': recipe.name,
        'ingredients': recipe.ingredients,
        'instructions': recipe.instructions,
        'image_url': recipe.image_url
    } for recipe in matching_recipes])

# Web Scraper
def scrape_recipes():
    url = "https://example-recipes-site.com"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    recipes = []
    for item in soup.find_all('div', class_='recipe-card'):
        name = item.find('h3').text
        ingredients = ', '.join([ing.text for ing in item.find_all('li', class_='ingredient')])
        instructions = item.find('div', class_='instructions').text
        image_url = item.find('img')['src'] if item.find('img') else None
        new_recipe = Recipe(name=name, ingredients=ingredients, instructions=instructions, image_url=image_url)
        recipes.append(new_recipe)
    db.session.bulk_save_objects(recipes)
    db.session.commit()

if __name__ == '__main__':
    db.create_all()
    app.run(debug=True)
