from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager 
from flask import request, send_from_directory
import json
import os
import replicate
import openai

# create the extension
db = SQLAlchemy()
# create the app
app = Flask(__name__)
# configure the SQLite database, relative to the app instance folder
app.config['SECRET_KEY'] = '9OLWxND4o83j4K4iuopO'
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///project1.1.db"
# initialize the app with the extension
db.init_app(app)

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

from flask_login import UserMixin
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True) # primary keys are required by SQLAlchemy
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prev_post = db.Column(db.Integer, db.ForeignKey('post.id'))
    content = db.Column(db.Text)
    is_ai = db.Column(db.Boolean)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    time =  db.Column(db.DateTime, server_default=func.now())
    session_uuid = db.Column(db.String(100))

    parent = relationship(lambda: Post, remote_side=id, backref='sub_post')

class PostAudio(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('post.id'))
    audio = db.Column(db.Text)

@login_manager.user_loader
def load_user(user_id):
    # since the user_id is just the primary key of our user table, use it in the query for the user
    return User.query.get(int(user_id))

from flask import Blueprint, render_template, redirect, url_for, request, flash
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required

auth = Blueprint('auth', __name__)

@auth.route('/login')
def login():
    return render_template('login.html')

@auth.route('/login', methods=['POST'])
def login_post():
    email = request.form.get('email')
    password = request.form.get('password')
    remember = True if request.form.get('remember') else False

    user = User.query.filter_by(email=email).first()

    # check if user actually exists
    # take the user supplied password, hash it, and compare it to the hashed password in database
    if not user or not check_password_hash(user.password, password): 
        flash('Please check your login details and try again.')
        return redirect(url_for('auth.login')) # if user doesn't exist or password is wrong, reload the page

    # if the above check passes, then we know the user has the right credentials
    login_user(user, remember=remember)
    return redirect(url_for('main.profile'))

@auth.route('/signup')
def signup():
    return render_template('signup.html')

@auth.route('/signup', methods=['POST'])
def signup_post():

    email = request.form.get('email')
    name = request.form.get('name')
    password = request.form.get('password')

    user = User.query.filter_by(email=email).first() # if this returns a user, then the email already exists in database

    if user: # if a user is found, we want to redirect back to signup page so user can try again  
        flash('Email address already exists')
        return redirect(url_for('auth.signup'))

    # create new user with the form data. Hash the password so plaintext version isn't saved.
    new_user = User(email=email, name=name, password=generate_password_hash(password, method='sha256'))

    # add the new user to the database
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for('auth.login'))

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

app.register_blueprint(auth)

from flask import Blueprint, render_template
from flask_login import login_required, current_user

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return render_template('index.html')

@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html', name=current_user.name)

model = replicate.models.get("openai/whisper")
openai.api_key = os.getenv("OPENAI_API_KEY")

SETTINGS = {
    'prompt': 'This is a conversation between the user and very happy, friendly and intelligent and curious AI assistant.\n',
    'user_name': 'User',
    'ai_name': 'AI'
}

GPT_SETTINGS = {
    'engine': 'text-davinci-002',
    'temperature': 0.4,
    'max_tokens': 100
}

def find(s, ch):
    return [i for i, ltr in enumerate(s) if ltr == ch]

def cap_gpt_reply(reply):
    possible_end_locations = find(reply, '.') + find(reply, '?') + find(reply, '!')
    if len(possible_end_locations) > 0:
        end_char_index = max(possible_end_locations) + 1
        reply = reply[:(end_char_index + 1)]
    return reply

import re
# removes double newlines from text
def trim_double_newlines(input):
    return input.replace('\n\n', '')

def get_gpt_reply(all_user_transcripts, all_ai_replies, new_transcript, gpt_settings=GPT_SETTINGS):
    prompt = SETTINGS['prompt']
    gpt_input = prompt
    for (alice_comment, bob_comment) in zip(all_user_transcripts, all_ai_replies):
        gpt_input += SETTINGS['user_name'] + ': ' + alice_comment + '\n'
        gpt_input += SETTINGS['ai_name'] + ': ' + bob_comment + '\n'
    gpt_input += SETTINGS['user_name'] + ': ' + new_transcript + '\n'
    gpt_input += SETTINGS['ai_name'] + ': '
    response = openai.Completion.create(
                engine=gpt_settings['engine'],
                prompt=gpt_input,
                temperature=gpt_settings['temperature'],
                max_tokens=gpt_settings['max_tokens']
    )

    reply = cap_gpt_reply(response.choices[0].text)
    reply = trim_double_newlines(reply)
    return reply

@main.route('/upload_audio', methods=['POST'])
@login_required
def upload_audio():
    print('Uploaded audio')   
    print('All Alice transcripts', request.form['all_alice_transcripts'])
    print('All Bob replies', request.form['all_bob_replies'])
    print('Transcribing...')
    output = model.predict(audio=request.form['base64data'],
                            model='base')
    transcript = output['transcription']
    print('Transcript', transcript)
    bob_reply = get_gpt_reply(
        json.loads(request.form['all_alice_transcripts']),
        json.loads(request.form['all_bob_replies']),
        transcript
    )


    last_reply_db_id = int(request.form['last_reply_db_id'])
    print('Last reply db id', last_reply_db_id, type(last_reply_db_id))
    print(Post.query.get(last_reply_db_id))
    transcript_db_entry = Post(
        prev_post=None if last_reply_db_id == 0 else last_reply_db_id,
        content=transcript,
        is_ai=False,
        user_id=current_user.id,
        session_uuid=request.form['session_uuid']
    )
    db.session.add(transcript_db_entry)
    db.session.commit()
    print(transcript_db_entry)
    reply_db_entry = Post(
        prev_post=transcript_db_entry.id,
        content=bob_reply,
        is_ai=True,
        user_id=current_user.id,
        session_uuid=request.form['session_uuid']
    )
    db.session.add(reply_db_entry)
    db.session.commit()
    print(reply_db_entry)

    transcript_audio_entry = PostAudio(
        post_id=transcript_db_entry.id,
        audio=request.form['base64data']
    )
    db.session.add(transcript_audio_entry)
    db.session.commit()

    return_dict = {
        'transcript': transcript,
        'reply': bob_reply,
        'transcript_db_id': transcript_db_entry.id,
        'reply_db_id': reply_db_entry.id
    }
    print(return_dict)
    return json.dumps(return_dict)


@app.route('/static/<path:path>')
def send_report(path):
    return send_from_directory('static', path)

app.register_blueprint(main)

with app.app_context():
    db.create_all()

