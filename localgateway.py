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
def benchmarker_runner(controller, size, nodenumbers):
    #pretty straightforward
    packet = {'bm':size,'u':randomword(4)}
    for nodenumber in nodenumbers:
        yield from controller.node_to_node(packet, controller.comm.address_book[nodenumber])
        yield from asyncio.sleep(5)#allow time to settle down
@asyncio.coroutine
def bandtest_runner(controller):
    yield from asyncio.sleep(30)
    candidates = [i for i in controller.neighbors if i['value']<65]
    print('candidates: ',candidates)
    for entry in candidates:
        node = entry['target']
        statpackage = yield from controller.bandwidth_measurer(node)
        yield from asyncio.sleep(5)
    print('done bandtesting')
@asyncio.coroutine
def fn_runner(controller, nodenumbers):
    packet = {'fn':0,'u':randomword(4)}
    for nodenumber in nodenumbers:
        yield from controller.node_to_node(packet, controller.comm.address_book[nodenumber])
        yield from asyncio.sleep(5) #allow time to settle down
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
benchmark_own = {}
def benchmark_prep(data):
    print('in bench: ',data,benchmark_own)
    uname = data['u']
    node = int(uname[0:2])
    size = uname.split('bnch')[-1] #'92randbnch10'
    t = data['res']['t']
    if node == '99' or node==99:
        benchmark_own[size]=t
    baseline = benchmark_own.get(size,0)
    if baseline:
        comped = round(baseline/t ,2)
        return {'node':nine_to_zero(node),'t':comped,'size':int(size),'exists':1}
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
class QueryWrapper:
    def __init__(self,controller,loop):
        self.controller = controller
        self.loop = loop
    async def run_benchmark(self, sid, data):
        nodenumbers = data['nodes']
        size = data['size']
        print('calling benchmark runner: ',data)
        await benchmarker_runner(self.controller, size, nodenumbers)
    async def run_finder(self, sid, data):
        nodenumbers = data['nodes']
        await fn_runner(self.controller, nodenumbers)
    async def fetch(self,client, data):
        async with client.post("http://192.168.1.200:5000/solve", data =data) as resp:
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
        txt_response = await self.post_solve(post_data)
        response = json.loads(txt_response)
        optimal_sensenodes = no_zeroes(response['sol']['S'])
        optimal_mapnodes = no_zeroes(response['sol']['M'])
        optimal_rednodes = no_zeroes(response['sol']['R'])
        optimal_code = replace_nodes(query['code'], optimal_sensenodes,optimal_mapnodes,optimal_rednodes)
        print('code: ',optimal_code)
        await asyncio.sleep(0)
        all_nodes = uqify(optimal_mapnodes +optimal_mapnodes+optimal_rednodes)
        send_data = {'u':userid,'f':optimal_code}
        #write record to file
        usense.append_record('dag_stats',response)
        await asyncio.sleep(0)
        for node in all_nodes:
            await self.controller.node_to_node(send_data, controller.comm.address_book[node])
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