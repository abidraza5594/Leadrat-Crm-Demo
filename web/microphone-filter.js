/* Local microphone cleanup. Only the resulting audio stream goes to Soniox. */
(() => {
  'use strict';
  const base='/vendor/noise-suppressor/';
  let assets=null;
  function warm() {
    if(!window.AudioWorkletNode)return Promise.resolve(null);
    if(!assets)assets=import(base+'index.js').then(async module=>({module,wasm:await module.loadRnnoise({
      url:base+'rnnoise.wasm',simdUrl:base+'rnnoise_simd.wasm'
    })})).catch(()=>{assets=null;return null;});
    return assets;
  }
  function create() {
    const AudioContext=window.AudioContext || window.webkitAudioContext;
    let context=null,source=null,filter=null,denoiser=null,destination=null,closed=false;
    const close=()=>{
      if(closed)return;closed=true;
      denoiser?.destroy();
      [source,filter,denoiser,destination].forEach(node=>{try{node?.disconnect();}catch{}});
      destination?.stream.getTracks().forEach(track=>track.stop());
      if(context && context.state!=='closed')context.close().catch(()=>{});
    };
    // Create/resume inside the microphone click so audio processing is gesture-authorized.
    try{if(AudioContext && window.AudioWorkletNode){context=new AudioContext({sampleRate:48000,latencyHint:'interactive'});context.resume().catch(()=>{});}}catch{}
    return {close,async process(stream){
      if(!context?.audioWorklet || closed){close();return stream;}
      let timeout;
      try{
        const loaded=await Promise.race([
          Promise.all([warm(),context.audioWorklet.addModule(base+'rnnoise/workletProcessor.js'),context.resume()]),
          new Promise((_,reject)=>{timeout=setTimeout(()=>reject(new Error('Noise filter unavailable')),1500);})
        ]);
        if(closed || !loaded[0] || context.state!=='running' || context.sampleRate!==48000)throw new Error('Noise filter unavailable');
        source=context.createMediaStreamSource(stream);
        filter=context.createBiquadFilter();filter.type='highpass';filter.frequency.value=80;filter.Q.value=.707;
        denoiser=new loaded[0].module.RnnoiseWorkletNode(context,{wasmBinary:loaded[0].wasm,maxChannels:1});
        denoiser.channelCount=1;denoiser.channelCountMode='explicit';
        destination=context.createMediaStreamDestination();
        source.connect(filter);filter.connect(denoiser);denoiser.connect(destination);
        denoiser.onprocessorerror=()=>{
          // Keep transcription usable if enhanced processing fails during a recording.
          if(closed)return;
          filter.disconnect();denoiser.disconnect();filter.connect(destination);
        };
        return destination.stream;
      }catch{close();return stream;}
      finally{clearTimeout(timeout);}
    }};
  }
  window.BeaconMicrophoneFilter={create,warm};
  warm();
})();
