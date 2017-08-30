import uasync_sense as usense
from aiohttp import web
import aiohttp
import socketio
import asyncio
import functools
import json
import random
import string
import requests
import re
def randomword(length):
   return ''.join(random.choice(string.ascii_lowercase) for i in range(length))
@asyncio.coroutine
def benchmarker_runner(controller, size, nodenumbers, cat):
    #pretty straightforward
    packet = {cat:size,'u':randomword(4)}
    for nodenumber in nodenumbers:
        yield from controller.node_to_node(packet, controller.comm.address_book[nodenumber])
        yield from asyncio.sleep(5)#allow time to settle down
@asyncio.coroutine
def bw_runner(controller, nodenumbers):
    for nodenumber in nodenumbers:
        statpackage = yield from controller.bandwidth_measurer(nodenumber)
        yield from asyncio.sleep(0) #allow time to settle down
@asyncio.coroutine
def fn_runner(controller, nodenumbers):
    packet = {'fn':0,'u':randomword(4)}
    for nodenumber in nodenumbers:
        yield from controller.node_to_node(packet, controller.comm.address_book[nodenumber])
        yield from asyncio.sleep(15) #allow time to settle down
    print('sent')
def result_prep(data):
    print('got a result: ',data)
    u = {}
    username_job = data['u']
    l = len(username_job)
    job_id = username_job[l-5::]
    username = username_job[2:l-5]
    result = json.dumps(data['res'])
    u['request']=result
    u['username'] = username
    u['job_name'] = job_id
    return u
def nine_to_zero(num):
    if num=='99':
        return 0
    if num==99:
        return 0
    else:
        return num
benchmark_own = {'100':0.02}
def benchmark_prep(data):
    print('in bench: ',data,benchmark_own)
    uname = data['u']
    node = int(uname[0:2])
    cat_size = uname.split('bnch')[-1] #'92randbnch110'
    cat = cat_size[0]
    size = cat_size[1::]
    t = data['res']['t']
    if node == '99' or node==99:
        benchmark_own[size]=t
        #t = 0.02
    baseline = benchmark_own.get(size,0)
    if baseline:
        comped = round(baseline/t ,2)
        return {'node':nine_to_zero(node),'t':comped,'raw_t':t,'bm':int(cat),'size':int(size),'exists':1}
def is_benchmark(data):
    return 'bnch' in data['u']
def is_neighbors(data):
    print('is nay: ', data)
    l = len(data['u'])
    return data['u'][l-2::]=='rs'
@asyncio.coroutine
def res_reader(socket, q):
    while True:
        data = yield from q.get()
        print('got res data', data)
        ##here - check benchmark vs res
        if is_benchmark(data):
            prepped = benchmark_prep(data)
            print('emitting: ',prepped)
            if prepped:
                yield from socket.emit('BM', prepped)
        elif is_neighbors(data):
            node = int(data['u'][0:2])
            entry = data['res']['rs']
            lst_of_pairs = entry.split('.')
            for pair in lst_of_pairs:
                lst = pair.split('_')
                processed = {'source':nine_to_zero(node),'target':nine_to_zero(int(lst[0])),'value':int(lst[1])}
                yield from socket.emit('FN',processed)
        else:
            yield from socket.emit('full_result_return', result_prep(data))
def uqify(lst):
    return list(set(lst))
def red_last(red,lst):
    for i in red:
        lst.remove(i)
        lst.append(i)
    return lst
#@asyncio.coroutine
def no_zeroes(lst):
    def translater(num):
        return 99 if num ==0 else num
    return [translater(i) for i in lst]
def no_99s(lst_of_lsts):
    def translated(num):
        return 0 if num==99 else num
    def translate_list(lst):
        return [translater(i) for i in lst]
    return [translate_list(lst) for lst in lst_of_lsts]
def replace_nodes(codestring, newsense, newmap, newreduce):
    with_sense = re.sub(r'sensenodes.*', r'sensenodes = {}'.format(newsense), codestring)
    with_map = re.sub(r'mapnodes.*', r'mapnodes = {}'.format(newmap), with_sense)
    with_red = re.sub(r'reducenodes.*', r'reducenodes = {}'.format(newreduce), with_map)
    return with_red
scuts = {"\n    def sampler(self,node):\n        acc = yield from node.testaccel(512)\n        return (node.ID,acc)\n    def mapper(self,node,d):\n        fts = np.fft(d[1]['x'])\n        c = lambda d: (d.real,d.imag)\n        yield(0,(d[0],c(fts[6])))\n    def reducer(self,node,k,vs):\n        ws = [complex(*i[1]) for i in vs]\n        G = np.spectral_mat(ws)\n        eig = np.pagerank(G)\n        c = lambda d: (round(d.real,2),round(d.imag,2))\n        ms = [(vs[idx][0],c(el)) for idx,el in enumerate(eig)]\n        yield(k,ms)":"fdd_single"
        ,"""
    def sampler(self,node):
        acc = yield from node.testaccel(512)
        return (node.ID,acc)
    def mapper(self,node,d):
        fts = np.fft(d[1]['x'])
        c = lambda d: (d.real,d.imag)
        k = hash(node.ID)%4
        yield(k,(d[0],c(fts[6])))
    def reducer(self,node,k,vs):
        ws = [complex(*i[1]) for i in vs]
        G = np.spectral_mat(ws)
        eig = np.pagerank(G)
        c = lambda d: (round(d.real,2),round(d.imag,2))
        ms = [(vs[idx][0],c(el)) for idx,el in enumerate(eig)]
        yield(k,ms)""":"dfdd"}
pat = re.compile(r'\s+')
shortcuts = {pat.sub('',k):v for k,v in scuts.items()}
def splitter(code,k):
    split = code.split(k)
    return split[0], k+split[1]
def check_shortcutted(optimised_code,rednode=None):
    #split into top and bottom
    top, bottom = splitter(optimised_code,"\n    def sampler(self,node):")
    #if bottom text in shortcutrs
    nospaces = pat.sub('',bottom)
    print('bottom: ',shortcuts,nospaces)
    sid = shortcuts.get(nospaces)
    if sid:
        print('got sid: ',sid)
        return sid, top
    else: 
        print('no sid: ',bottom)
        return None,optimised_code
def dis(sid,data):
    print('lost connection')
class QueryWrapper:
    def __init__(self,controller,loop):
        self.controller = controller
        self.loop = loop
    async def run_benchmark(self, sid, data):
        nodenumbers = data['nodes']
        size = data['size']
        cat = data['cat']
        print('calling benchmark runner: ',data)
        await sio.disconnect(sid)
        await benchmarker_runner(self.controller, size, nodenumbers, cat)
    async def run_finder(self, sid, data):
        nodenumbers = data['nodes']
        await sio.disconnect(sid)
        await fn_runner(self.controller, nodenumbers)
    async def run_bw(self, sid, data):
        print('running bw')
        nodenumbers = data['nodes']
        await sio.disconnect(sid)
        await bw_runner(self.controller, nodenumbers)
    async def fetch(self,client, data):
        async with client.post("http://127.0.0.1:5000/solve", data =data) as resp:
            print('got resp: ',resp)
            assert resp.status == 200
            return await resp.text()
    async def post_solve(self, data):
        async with aiohttp.ClientSession(loop=self.loop) as client:
            response_data = await self.fetch(client, data)
            print(response_data)
            return response_data
    async def query_passer(self,sid, data):
        query = data
        job = query['job']
        uname = query['username']
        userid = uname+job
        exec(query['code'])
        code_class = locals()['SenseReduce']()
        #here we should make call to dag-plan to get the nodes - TODO
        post_data = data={'user': userid, 'code': query['code']
                         ,'rssi':query.get('rssi'), 'px':query.get('px')}
        print('sending to dag engine')
        sio.disconnect(sid)
        txt_response = await self.post_solve(post_data)
        response = json.loads(txt_response)
        optimal_sensenodes = no_zeroes(response['sol']['S'])
        optimal_mapnodes = no_zeroes(response['sol']['M'])
        optimal_rednodes = no_zeroes(response['sol']['R'])
        optimal_code = replace_nodes(query['code'], optimal_sensenodes,optimal_mapnodes,optimal_rednodes)
        print('code: ',optimal_code)
        sid,trunc_code = check_shortcutted(optimal_code)
        await asyncio.sleep(0)
        nodes = uqify(optimal_rednodes+optimal_sensenodes +optimal_mapnodes)
        all_nodes = red_last(optimal_rednodes, nodes)
        send_data = {'u':userid,'f':trunc_code}
        if sid:
            send_data['f']=(optimal_rednodes,sid)
        #write record to file
        response['job']=userid
        response['code']=optimal_code
        usense.append_record('dag_stats',response)
        await asyncio.sleep(0)
        print('node!: ',all_nodes)
        for node in all_nodes:
            print('sending to: ',node)
            #await self.controller.node_to_node(send_data, controller.comm.address_book[node])
            await asyncio.sleep(0)
async def heartbeat():
    while True:
        await asyncio.sleep(3)
        print('im alive')
async def connect(sid, environ):
    print('got connection from remote, now subscribing')
    await sio.emit('localGatewaySubscribe')

if __name__ == "__main__":
    sio = socketio.AsyncServer()
    loop = asyncio.get_event_loop()
    app = web.Application(loop=loop)
    sio.attach(app) 
    sio.on('connect')(connect)
    ### now start adding tasks to base loop ###
    comm = usense.Comm()
    controller = usense.ControlTasks(loop, comm)
    loop.add_reader(comm.uart.fd, usense.handle_stdin, comm, loop)
    sio.on('queryToGateway')(QueryWrapper(controller,loop).query_passer)
    sio.on('runbenchmark')(QueryWrapper(controller,loop).run_benchmark)
    sio.on('runfinder')(QueryWrapper(controller,loop).run_finder)
    sio.on('runbandwidth')(QueryWrapper(controller,loop).run_bw)
    tasks = [controller.multiple_chunk_assembler(), controller.radio_listener()
            ,controller.queue_placer() ,res_reader(sio, controller.comm.res_queue)
            ,controller.at_reader(),controller.function_definer(), controller.worker()
            ,controller.benchmark()
            ,controller.report_neighbours(),controller.find_neighbours(),heartbeat()]
            #,bandtest_runner(controller)]
            #,fn_runner(controller, [17])]--need to replace with on demand
            #,benchmarker_runner(controller,50, [99,17]),]-need to replace with on demand

    for task in tasks:
        asyncio.ensure_future(task)
    web.run_app(app, port=5333)