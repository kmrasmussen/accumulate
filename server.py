from flask import Flask
from flask import request, send_from_directory
import json
import openai
import os
import replicate

app = Flask(__name__)

model = replicate.models.get("openai/whisper")
openai.api_key = os.getenv("OPENAI_API_KEY")

SETTINGS = {
    'prompt': 'This is a conversation between the user and very happy, friendly and intelligent AI assistant.\n',
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
    return reply

@app.route('/upload_audio', methods=['POST'])
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

    return_dict = {
        'transcript': transcript,
        'reply': bob_reply
    }
    print(return_dict)
    return json.dumps(return_dict)

@app.route('/client/<path:path>')
def send_report(path):
    return send_from_directory('client', path)

# login functionality
@app.route('/login', methods=['POST'])
def login():
    print('Login request')
    print('Username', request.form['username'])
    print('Password', request.form['password'])
    return_dict = {
        'success': True
    }
    print(return_dict)
    return json.dumps(return_dict)