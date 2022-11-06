//webkitURL is deprecated but nevertheless
URL = window.URL || window.webkitURL;

var gumStream; 						//stream from getUserMedia()
var rec; 							//Recorder.js object
var input; 							//MediaStreamAudioSourceNode we'll be recording

// shim for AudioContext when it's not avb. 
var AudioContext = window.AudioContext || window.webkitAudioContext;
var audioContext //audio context to help us record

var recordButton = document.getElementById("recordButton");
var stopButton = document.getElementById("stopButton");
var pauseButton = document.getElementById("pauseButton");

//add events to those 2 buttons
recordButton.addEventListener("click", startRecording);
stopButton.addEventListener("click", stopRecording);
pauseButton.addEventListener("click", pauseRecording);

function uuidv4() {
	return ([1e7]+-1e3+-4e3+-8e3+-1e11).replace(/[018]/g, c =>
	  (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
	);
  }

function startRecording() {
	console.log("recordButton clicked");

    var constraints = { audio: true, video:false }
	recordButton.disabled = true;
	stopButton.disabled = false;
	pauseButton.disabled = false

	navigator.mediaDevices.getUserMedia(constraints).then(function(stream) {
		console.log("getUserMedia() success, stream created, initializing Recorder.js ...");
		audioContext = new AudioContext();
		//document.getElementById("formats").innerHTML="Format: 1 channel pcm @ "+audioContext.sampleRate/1000+"kHz"
		gumStream = stream;
		input = audioContext.createMediaStreamSource(stream);
		rec = new Recorder(input,{numChannels:1})
		rec.record()
		console.log("Recording started");
	}).catch(function(err) {
	  	//enable the record button if getUserMedia() fails
    	recordButton.disabled = false;
    	stopButton.disabled = true;
    	pauseButton.disabled = true
	});
}

function pauseRecording(){
	console.log("pauseButton clicked rec.recording=",rec.recording );
	if (rec.recording){
		//pause
		rec.stop();
		pauseButton.innerHTML="Resume";
	}else{
		//resume
		rec.record()
		pauseButton.innerHTML="Pause";

	}
}

function stopRecording() {
	console.log("stopButton clicked");

	stopButton.disabled = true;
	recordButton.disabled = false;
	pauseButton.disabled = true;

	//reset button just in case the recording is stopped while paused
	pauseButton.innerHTML="Pause";
	
	//tell the recorder to stop the recording
	rec.stop();

	//stop microphone access
	gumStream.getAudioTracks()[0].stop();

	//create the wav blob and pass it on to createDownloadLink
	rec.exportWAV(createDownloadLink);


}

/*
const websocket = new WebSocket("ws://localhost:8001/"); 

websocket.addEventListener("message", ({ data }) => {
	const event = JSON.parse(data);
	console.log(event)
	console.log(event.transcription)
});
*/

var all_alice_transcripts = []
var all_bob_replies = []

function createDownloadLink(blob) {
	blob_uuid = uuidv4();
	console.log('blob')
	console.log(blob)
	var url = URL.createObjectURL(blob);
	console.log('url')
	console.log(url)
	var au = document.createElement('audio');
	var li = document.createElement('li');
	var link = document.createElement('a');
	var transcript = document.createElement('p');
	transcript.setAttribute("id", 'transcript_' + blob_uuid);
	var reply = document.createElement('p');
	reply.setAttribute("id", 'reply_' + blob_uuid);

	/*
	var reader = new FileReader();
	reader.readAsDataURL(blob); 
	reader.onloadend = function() {
		var base64data = reader.result;                
		console.log(base64data);
		const event = {type: "recording", content: base64data};
		websocket.send(JSON.stringify(event));
		console.log('sent websocket msg')
	}
	*/

	//name of .wav file to use during upload and download (without extendion)
	var filename = new Date().toISOString();

	//add controls to the <audio> element
	au.controls = true;
	au.src = url;

	//save to disk link
	link.href = url;
	link.download = filename+".wav"; //download forces the browser to donwload the file using the  filename
	link.innerHTML = "Save to disk";

	//add the new audio element to li
	//li.appendChild(au);
	
	//add the filename to the li
	//li.appendChild(document.createTextNode(filename+".wav "))

	//add the save to disk link to li
	//li.appendChild(link);
	
	//upload link
	var upload = document.createElement('a');
	upload.href="#";
	upload.innerHTML = "Upload";
	upload.addEventListener("click", upload)
	//li.appendChild(document.createTextNode (" "))//add a space in between
	//li.appendChild(upload)//add the upload link to li
	li.appendChild(transcript)
	li.appendChild(reply)

	//add the li element to the ol
	recordingsList.appendChild(li);

	var xhr=new XMLHttpRequest();
	xhr.onload=function(e) {
		if(this.readyState === 4) {
			console.log("Server returned: ",e.target.responseText);
			response_dict = JSON.parse(e.target.responseText)
			transcript_text = response_dict['transcript'] // response_dict['transcript']
			reply_text = response_dict['reply']
			document.getElementById('transcript_' + blob_uuid).innerHTML = 'User: ' + transcript_text
			document.getElementById('reply_' + blob_uuid).innerHTML = 'AI: ' + reply_text.replace('\n', '<br>')
			var msg = new SpeechSynthesisUtterance();
			var voices = window.speechSynthesis.getVoices();
			msg.voice = voices[10]; 
			msg.volume = 1; // From 0 to 1
			msg.rate = 1; // From 0.1 to 10
			msg.pitch = 0; // From 0 to 2
			msg.text = reply_text;
			msg.lang = 'en';
			speechSynthesis.speak(msg);
			
			all_alice_transcripts.push(transcript_text)
			all_bob_replies.push(reply_text)
		}
	};
	var reader = new FileReader();
	reader.readAsDataURL(blob); 
	reader.onloadend = function() {
		var base64data = reader.result;                
		//console.log(base64data);
		//const event = {type: "recording", content: base64data};
		//websocket.send(JSON.stringify(event));
		//console.log('sent websocket msg')
		var fd=new FormData();
		fd.append("base64data",base64data);
		fd.append("uuid", blob_uuid);
		fd.append('all_alice_transcripts', JSON.stringify(all_alice_transcripts))
		fd.append('all_bob_replies', JSON.stringify(all_bob_replies))
		//fd.append("audio_data",blob, filename);
		xhr.open("POST","http://127.0.0.1:5000/upload_audio",true);
		xhr.send(fd);
	}
}