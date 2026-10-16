/* Microphone audio goes to Soniox with a short-lived, single-use credential. */
(() => {
  'use strict';
  const UTTERANCE_PAUSE_MS=2000;
  class SonioxInput {
    constructor({getKey, onText, onUtterance, onState, onError}) {
      Object.assign(this,{getKey,onText,onUtterance,onState,onError});this.generation=0;this.final='';
    }
    flushUtterance(){
      clearTimeout(this.utteranceTimer);
      const text=this.final.trim();this.final='';
      if(text)this.onUtterance(text);
    }
    async start(language='en') {
      this.abort();const generation=this.generation;this.onState('connecting');
      const filter=this.filter=window.BeaconMicrophoneFilter?.create();
      try {
        const supported=navigator.mediaDevices.getSupportedConstraints?.() || {};
        const stream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true,
          autoGainControl:false,channelCount:1,...(supported.voiceIsolation?{voiceIsolation:true}:{})}});
        if(generation!==this.generation){stream.getTracks().forEach(t=>t.stop());return;}
        this.stream=stream;
        const [cleanStream,config]=await Promise.all([filter?filter.process(stream):stream,this.getKey()]);
        if(generation!==this.generation)return;
        const socket=this.socket=new WebSocket(config.url,['soniox-api-key',config.api_key]);
        const mime=['audio/webm;codecs=opus','audio/ogg;codecs=opus','audio/mp4'].find(t=>MediaRecorder.isTypeSupported(t));
        if(!mime)throw new Error('This browser cannot record a supported audio format. Please type your question.');
        const recorder=this.recorder=new MediaRecorder(cleanStream,{mimeType:mime});
        this.final='';
        const fail=message=>{if(generation!==this.generation)return;this.abort();this.onError(message);};
        this.connectTimer=setTimeout(()=>fail('Speech connection timed out. Tap the microphone to retry.'),10000);
        socket.onopen=()=>{
          if(generation!==this.generation){socket.close();return;}
          clearTimeout(this.connectTimer);
          socket.send(JSON.stringify({model:config.model,audio_format:'auto',language_hints:[language,language==='en'?'hi':'en'],
            enable_endpoint_detection:true,max_endpoint_delay_ms:1000}));
          recorder.start(100);this.onState('listening');
          this.maxTimer=setTimeout(()=>this.stop(),config.max_seconds*1000);
        };
        recorder.ondataavailable=e=>{
          if(socket.readyState===WebSocket.OPEN && e.data.size){
            if(socket.bufferedAmount>1024*1024){fail('The speech connection is too slow. Your typed text is preserved.');return;}
            socket.send(e.data);
          }
        };
        recorder.onstop=()=>{stream.getTracks().forEach(t=>t.stop());filter?.close();if(socket.readyState===WebSocket.OPEN)socket.send('');};
        socket.onmessage=e=>{
          if(generation!==this.generation)return;
          let data;try{data=JSON.parse(e.data);}catch{fail('Invalid speech response. Please try again.');return;}
          if(data.error_code){fail('Soniox could not transcribe this audio. Check the connection or account, then try again.');return;}
          // Keep short pauses within one question; new speech cancels the pending send.
          if((data.tokens||[]).some(token=>!['<end>','<fin>'].includes(token.text) && token.text?.trim()))clearTimeout(this.utteranceTimer);
          let interim='',endpoint=false;
          for(const token of data.tokens||[]){
            if(['<end>','<fin>'].includes(token.text)){endpoint=true;continue;}
            if(token.is_final)this.final+=token.text;else interim+=token.text;
          }
          this.onText((this.final+interim).trim());
          if(data.finished)this.flushUtterance();
          else if(endpoint){
            clearTimeout(this.utteranceTimer);
            this.utteranceTimer=setTimeout(()=>{if(generation===this.generation)this.flushUtterance();},UTTERANCE_PAUSE_MS);
          }
          if(data.finished){this.abort();}
        };
        socket.onerror=()=>fail('Speech connection failed. You can still type.');
        socket.onclose=()=>{
          if(generation!==this.generation)return;
          this.flushUtterance();
          this.abort();
        };
      }catch(e){if(generation===this.generation){this.abort();this.onError(e.name==='NotAllowedError'?'Allow microphone access, then tap the microphone again.':e.message);}}
    }
    stop(){
      if(this.recorder?.state==='recording'){
        this.recorder.stop();this.onState('finishing');
        this.closeTimer=setTimeout(()=>{this.flushUtterance();this.abort();},2500);
      }else this.abort();
    }
    abort(){
      this.generation++;clearTimeout(this.connectTimer);clearTimeout(this.maxTimer);clearTimeout(this.closeTimer);clearTimeout(this.utteranceTimer);
      if(this.recorder){this.recorder.onstop=null;this.recorder.ondataavailable=null;if(this.recorder.state==='recording')this.recorder.stop();}
      this.stream?.getTracks().forEach(t=>t.stop());
      this.filter?.close();this.filter=null;
      if(this.socket){this.socket.onclose=null;this.socket.onerror=null;this.socket.onmessage=null;this.socket.close();}
      this.stream=this.socket=this.recorder=null;this.final='';this.onState('off');
    }
  }
  window.BeaconSonioxInput=SonioxInput;
})();
