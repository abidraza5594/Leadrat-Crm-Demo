"""Quantized CPU embeddings without loading PyTorch into the web server."""
import threading
import numpy as np
from .config import ROOT

class Encoder:
    def __init__(self):
        import onnxruntime as ort
        from tokenizers import Tokenizer
        from slm.setup_knowledge import FILES,verify
        folder=ROOT/'.models/knowledge'
        for remote,digest in FILES.items():
            from pathlib import Path
            if not verify(folder/Path(remote).name,digest):
                raise RuntimeError('Run python -m slm.setup_knowledge to prepare verified search files')
        self.tokenizer=Tokenizer.from_file(str(folder/'tokenizer.json'))
        self.tokenizer.enable_truncation(max_length=128)
        self.tokenizer.enable_padding(pad_id=1,pad_token='<pad>')
        options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
        self.session=ort.InferenceSession(str(folder/'model_quint8_avx2.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
        self.inputs={i.name for i in self.session.get_inputs()};self.lock=threading.Lock()

    def encode(self,texts,**kwargs):
        single=isinstance(texts,str);rows=[texts] if single else texts;vectors=[]
        with self.lock:
            for start in range(0,len(rows),16):
                encoded=self.tokenizer.encode_batch(rows[start:start+16])
                ids=np.asarray([r.ids for r in encoded],dtype=np.int64)
                mask=np.asarray([r.attention_mask for r in encoded],dtype=np.int64)
                data={'input_ids':ids,'attention_mask':mask,'token_type_ids':np.zeros_like(ids)}
                hidden=self.session.run(None,{k:v for k,v in data.items() if k in self.inputs})[0]
                weights=mask[...,None].astype(np.float32)
                pooled=(hidden*weights).sum(axis=1)/np.maximum(weights.sum(axis=1),1)
                pooled/=np.maximum(np.linalg.norm(pooled,axis=1,keepdims=True),1e-12)
                vectors.extend(pooled)
        array=np.asarray(vectors,dtype=np.float32)
        return array[0] if single else array
