from flask import Flask, render_template, request
from flask import redirect, jsonify, url_for, flash
from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from models import Base, Sport, Item, User
from flask import session as login_session
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

app = Flask(__name__)

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']
APPLICATION_NAME = "Sport Menu Application"


# Connect to Database and create database session
engine = create_engine('sqlite:///sports.db?check_same_thread=False')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# Create anti-forgery state token
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(
        string.ascii_uppercase + string.digits) for x in range(32))
    login_session['state'] = state
    # return "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code, now compatible with Python3
    request.get_data()
    code = request.data.decode('utf-8')

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    # Submit request, parse response - Python3 compatible
    h = httplib2.Http()
    response = h.request(url, 'GET')[1]
    str_response = response.decode('utf-8')
    result = json.loads(str_response)

    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('User is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    # see if user exists, if it doesn't make a new one
    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ''' " style = "width: 300px; height: 300px;border-radius:
        150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '''
    flash("you are now logged in as %s" % login_session['username'])
    return output


# Create a new User
def createUser(login_session):
    newUser = User(name=login_session['username'], email=login_session[
                   'email'], picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


# Get users information
def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


# Get user id
def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None

# DISCONNECT - Revoke a current user's token and reset their login_session


@app.route('/gdisconnect')
def gdisconnect():
        # Only disconnect a connected user.
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        # Reset the user's sesson.
        login_session.clear()
        response = make_response(json.dumps('Successfully disconnected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        # Reset the user's sesson.
        login_session.clear()
        # For whatever reason, the given token was invalid.
        response = make_response(
            json.dumps('Failed to revoke token for given user.', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


# JSON APIs to view Sport Information
@app.route('/sport/<int:sport_id>/item/JSON')
def sportItemJSON(sport_id):
    sport = session.query(Sport).filter_by(id=sport_id).one()
    items = session.query(Item).filter_by(
        sport_id=sport_id).all()
    return jsonify(Item=[i.serialize for i in items])


@app.route('/sport/<int:sport_id>/item/<int:item_id>/JSON')
def ItemJSON(sport_id, item_id):
    item = session.query(Item).filter_by(id=item_id).one()
    return jsonify(Item=item.serialize)


@app.route('/sport/JSON')
def sportsJSON():
    sports = session.query(Sport).all()
    return jsonify(sports=[r.serialize for r in sports])


# Show all sports
@app.route('/')
@app.route('/sport/')
def showSports():
    sports = session.query(Sport).order_by(asc(Sport.name))
    items = session.query(Item).order_by(asc(Item.name)).limit(5)
    try:
        user = session.query(User).filter_by(
            email=login_session['email']).one()
    except:
        user = None
    return render_template(
        'sports.html', sports=sports, items=items, user=user)


# Create a new sport
@app.route('/sport/new/', methods=['GET', 'POST'])
def newSport():
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newSport = Sport(name=request.form['name'],
                         user_id=login_session['user_id'])
        session.add(newSport)
        flash('New Sport %s Successfully Created' % newSport.name)
        session.commit()
        return redirect(url_for('showSports'))
    else:
        return render_template('newSport.html')


# Edit a sport
@app.route('/sport/<int:sport_id>/edit/', methods=['GET', 'POST'])
def editSport(sport_id):
    editedSport = session.query(
        Sport).filter_by(id=sport_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if editedSport.user_id != login_session['user_id']:
        return """<script>function myFunction() {alert('You are not authorized
        to edit this sport.');}</script><body onload='myFunction()''>"""
    if request.method == 'POST':
        if request.form['name']:
            editedSport.name = request.form['name']
            flash('Sport Successfully Edited %s' % editedSport.name)
            return redirect(url_for('showSports'))
    else:
        return render_template('editSport.html', sport=editedSport)


# Delete a sport
@app.route('/sport/<int:sport_id>/delete/', methods=['GET', 'POST'])
def deleteSport(sport_id):
    sportToDelete = session.query(
        Sport).filter_by(id=sport_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if sportToDelete.user_id != login_session['user_id']:
        return """<script>function myFunction() {alert('You are not authorized
        to delete this sport.');}</script><body onload='myFunction()''>"""
    if request.method == 'POST':
        session.delete(sportToDelete)
        flash('%s Successfully Deleted' % sportToDelete.name)
        session.commit()
        return redirect(url_for('showSports', sport_id=sport_id))
    else:
        return render_template('deleteSport.html', sport=sportToDelete)


# Show a sport item
@app.route('/sport/<int:sport_id>/')
@app.route('/sport/<int:sport_id>/items/')
def showItems(sport_id):
    sport = session.query(Sport).filter_by(id=sport_id).one()
    items = session.query(Item).filter_by(
        sport_id=sport_id).all()
    user = session.query(User).filter_by(id=sport.user_id).one()
    return render_template('items.html', items=items, sport=sport, user=user)


@app.route('/sport/items/<int:item_id>')
def showItem(item_id):
    item = session.query(Item).filter_by(id=item_id).one()
    sport = session.query(Sport).filter_by(id=item.sport_id).one()
    return render_template('item.html', item=item, sport=sport)


# Create a new items
@app.route('/sport/<int:sport_id>/item/new/', methods=['GET', 'POST'])
def newItem(sport_id):
    sport = session.query(Sport).filter_by(id=sport_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newItem = Item(name=request.form['name'], description=request.form[
            'description'], price=request.form['price'], sport_id=sport_id,
            user_id=login_session['user_id'])
        session.add(newItem)
        session.commit()
        flash('New Item %s Successfully Created' % (newItem.name))
        return redirect(url_for('showItem', item_id=newItem.id))
    else:
        return render_template('newItem.html', sport_id=sport_id)


# Edit a item
@app.route('/sport/<int:sport_id>/item/<int:item_id>/edit', methods=[
    'GET', 'POST'])
def editItem(sport_id, item_id):
    editedItem = session.query(Item).filter_by(id=item_id).one()
    sport = session.query(Sport).filter_by(id=sport_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if editedItem.user_id != login_session['user_id']:
        return """<script>function myFunction() {alert('You are not authorized
        to edit this item.');}</script><body onload='myFunction()''>"""
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        session.add(editedItem)
        session.commit()
        flash('Item Successfully Edited')
        return redirect(url_for('showItem', item_id=item_id))
    else:
        return render_template(
            'editItem.html', sport_id=sport.id, item_id=item_id,
            item=editedItem)


# Delete a item
@app.route('/sport/<int:sport_id>/item/<int:item_id>/delete', methods=[
    'GET', 'POST'])
def deleteItem(sport_id, item_id):
    sport = session.query(Sport).filter_by(id=sport_id).one()
    itemToDelete = session.query(Item).filter_by(id=item_id).one()
    if 'username' not in login_session:
        return redirect('/login')
    if itemToDelete.user_id != login_session['user_id']:
        return """<script>function myFunction() {alert('You are not authorized
        to delete this item.');}</script><body onload='myFunction()''>"""
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Item Successfully Deleted')
        return redirect(url_for('showItems', sport_id=sport.id))
    else:
        return render_template('deleteItem.html', item=itemToDelete)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=5000)
