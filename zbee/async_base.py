from zbee.base import XBeeBase
import asyncio as asyncio
import json as json
import time as time
import struct as struct
from zbee.frame import APIFrame
from zbee.python2to3 import byteToInt, intToByte
def assemble_result(pieces):
    """pieces is a list of result messages that need to be pieced together before returning"""
    return {k:v for sub in pieces for k,v in sub.items()}
def parse_raw(rf_data):
    """rf_data is like kv_whateverdata1203jjlong"""
    print('parsing: ',rf_data)
    data_size=17
    try:
        chunk_type = rf_data.split('_')[0]
        without_chunk_type = rf_data.replace(chunk_type+'_', '', 1)
        data = without_chunk_type[0:data_size].strip('#')
        c= int(without_chunk_type[data_size:data_size+2])
        idx = int(without_chunk_type[data_size+2:data_size+4])
        uname = without_chunk_type[data_size+4::]
        d = {chunk_type:data, 'c':c,'n':idx, 'u':uname}
        print('d: ',d)
        return d
    except Exception as e:
        print('e: ',e)
        return {}
class XBeeAsync(XBeeBase):
    """Subclass of XBeeBase that fits with asynchronous event loop"""
    @asyncio.coroutine
    def wait_read_multipleframes(self, dataq, intermediate_output_q, outputq):
        """gets data from dataq, calls assemble_chunks to piece it to a full rf message
        then additionally checks to see if it's a multi part result message before putting it 
        on the outputq
        """
        multiple_accumulator = {}
        while True:
            msg = yield from intermediate_output_q.get()
            print('got a intermediate msg: ', msg)
            #blah blah blah-ok i think this is a full packet so try to get rf data
            #then try to get 'res' field
            data = json.loads(msg.get('rf_data','{}'))
            res_chunk = data.get('res',None)
            if res_chunk:#exists put in dictionary
                #now check if full pieces
                num_reducers = res_chunk[0]
                reduce_data = json.loads(res_chunk[1])
                print('res chunk: ',reduce_data)
                username_job = data['u']
                previous = multiple_accumulator.get(username_job) 
                if not previous:
                    multiple_accumulator[username_job] = []
                multiple_accumulator[username_job].append(reduce_data)
                if len(multiple_accumulator[username_job]) == num_reducers:
                    pieced = assemble_result(multiple_accumulator[username_job])
                    rf_data = json.dumps({'res': pieced, 'u':username_job})
                    msg['rf_data'] = rf_data
                    yield from outputq.put(msg)
            else:
                yield from outputq.put(msg)
    @asyncio.coroutine
    def assemble_chunks(self, intermediate_output_q, dataq):
        chunk_def = {}
        while True:
            #print('got called')
            msg = yield from self.wait_read_frame(dataq)
            try:
                rf = msg['rf_data']
                data = parse_raw(json.loads(msg['rf_data'].decode('utf-8')))
                try:
                    idx = data['n']
                    del data['n']
                    chk = data['c']
                    del data['c']
                    job_id = data['u'] #a unique identifier with a 5 digit job id+ 2 digit node id if it's a kv
                    del data['u']

                    #print('reading multiple frames: ',idx, chk, job_id)
                    chunk_type = list(data.keys())[0] #if {'f':something} this gives 'f'
                    #print('chunk type: ', chunk_type)
                    #if key-value we may have concurrent messages arriving with 
                    #the same base job_id - so we added the nodeID at the front
                    #reset base_job_id for non kv chunktypes
                    try:
                        del base_job_id
                    except NameError:
                        pass
                    if chunk_type in ['kv']:
                        print('got a kv: ', job_id, data) 
                        #base_job_id = job_id[2::] # ie job_id = '91abcde'-actually even moreso it should have one per yield  
                        base_job_id = job_id[4::]             
                    try:
                        chunk_def[job_id]
                        #print('already a list')
                    except KeyError: #if the user+job id isn't in the dictionary
                        #print('key error excepted at first')
                        chunk_def[job_id] = {}
                    try:
                        chunk_def[job_id][chunk_type]
                    except KeyError:
                        chunk_def[job_id][chunk_type] = [None]*chk
                        #print('key error excepted')
                    chunk_def[job_id][chunk_type][idx] = (idx, data[chunk_type])
                    non_empty = [i for i in chunk_def[job_id][chunk_type] if i]                        
                    if len(non_empty) == chk:
                        print('matching length: ',non_empty)
                        chunk_def_list = sorted( chunk_def[job_id][chunk_type] )
                        chunk = ''.join( [i[1] for i in chunk_def_list] )
                        try:
                            chunk = json.loads(chunk)
                        except (TypeError,ValueError) as e:
                            #print('wasnt a dumped json',e)
                            pass
                        try:                      
                            rf_data = json.dumps({chunk_type: chunk,
                                                        'u':base_job_id})
                            msg['rf_data'] = rf_data
                        except NameError:
                            rf_data = json.dumps({chunk_type: chunk,
                                                        'u':job_id})
                            msg['rf_data'] = rf_data
                        del chunk_def[job_id][chunk_type]
                        if not chunk_def[job_id]:
                            del chunk_def[job_id]
                        yield from intermediate_output_q.put(msg) #put the pieced back together message on the output q                        
                except (KeyError, ValueError) as e: #no end message means a single transmission
                    #print('returning because of exception',e)
                    yield from intermediate_output_q.put(msg) #put a single back together message on the output q   
            except (KeyError, ValueError) as e:
                """think this is where I need to add AT command response handling
                although actually it gets put on the output q anyway"""
                yield from intermediate_output_q.put(msg)#put the ack message on the q
    
    @asyncio.coroutine
    def _wait_for_frame(self, dataq):
        """dataq is an asyncio Queue"""
        frame = APIFrame(escaped=self._escaped)  
        while True:                
                byte = yield from dataq.get()
                if byte != APIFrame.START_BYTE:
                    continue
                # Save all following bytes, if they are not empty
                if len(byte) == 1:
                    frame.fill(byte)                 
                while(frame.remaining_bytes() > 0):
                    #print('remaining: ', frame.remaining_bytes())
                    #z.send('tx', data=b'still bytes remaining', dest_addr_long=addr, dest_addr=b'\xff\xfe')
                    #led2.on()
                    byte = yield from dataq.get()#yield from dataq.get()
                    #print('got a byte: ', byte)
                    if len(byte) == 1:
                        frame.fill(byte)        
                try:
                    # Try to parse and return result
                    frame.parse()
                    # Ignore empty frames
                    if len(frame.data) == 0:
                        frame = APIFrame()
                        continue   
                    return frame
                except ValueError:
                    #print("Bad frame, so restart")
                    frame = APIFrame(escaped=self._escaped)  
    @asyncio.coroutine
    def wait_read_frame(self, dataq):       
        frame = yield from self._wait_for_frame(dataq)
        #print('frame: ', frame)
        return self._split_response(frame.data)
        
    def prepare_send(self, cmd, **kwargs):
        #helper function to prepare data for sending 
        data = self._build_command(cmd, **kwargs)
        frame = APIFrame(data, self._escaped).output()
        return frame
        
        
