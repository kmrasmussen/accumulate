from flask import Flask
from flask import request

app = Flask(__name__)

import asyncio

import websockets

import replicate
model = replicate.models.get("openai/whisper")
import json

import openai
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

def find(s, ch):
    return [i for i, ltr in enumerate(s) if ltr == ch]

async def handler(websocket):
    async for message in websocket:
        message_dict = json.loads(message)
        print(message)
        print(message_dict['type'])
        output = model.predict(audio=message_dict['content'],
                            model='base')
        transcript = output['transcription']
        print(transcript)
        await websocket.send(json.dumps(output))

async def main():
    async with websockets.serve(handler, "", 8001):
        await asyncio.Future()  # run forever

def get_gpt_reply(all_alice_transcripts, all_bob_replies, new_transcript):
    prompt = 'This is a conversation between the user and very happy, friendly and intelligent AI assistant.\n'
    gpt_input = prompt
    print('all Alice transcripts', all_alice_transcripts)
    print('all bob replies', all_bob_replies)
    for (alice_comment, bob_comment) in zip(all_alice_transcripts, all_bob_replies):
        gpt_input += 'User: ' + alice_comment + '\n'
        gpt_input += 'AI: ' + bob_comment + '\n'
    gpt_input += 'User: ' + new_transcript + '\n'
    gpt_input += 'AI: '
    print('gpt_input:', gpt_input)
    response = openai.Completion.create(
                engine="text-davinci-002",
                prompt=gpt_input,
                temperature=0.4,
                max_tokens=100
    )
    print('response', response)
    bob_reply = response.choices[0].text
    possible_end_locations = find(bob_reply, '.') + find(bob_reply, '?') + find(bob_reply, '!')
    print('possible end locs', possible_end_locations)
    print('bob reply before trim', bob_reply)
    if len(possible_end_locations) > 0:
        end_char_index = max(possible_end_locations) + 1
        print('end char index', end_char_index)
        bob_reply = bob_reply[:(end_char_index + 1)]
    #print(response)
    print('bob reply after trim', bob_reply)
    return bob_reply

    


if __name__ == "__main__":
    asyncio.run(main())

@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route('/upload_audio', methods=['POST'])
def upload_audio():
    print('Uploaded audio')   
    #print(request)
    #print(request.form)
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

from flask import send_from_directory

@app.route('/client/<path:path>')
def send_report(path):
    return send_from_directory('client', path)
