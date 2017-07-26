import uasync_sense as usense
from aiohttp import web
import socketio
import asyncio
import functools
def benchmarker_runner():
	#pretty straightforward
	pass
def neighbor_searcher():
	pass
	#need to send remote_at_command
def result_prep(data):
	u = {}
	username_job = data['u']
	l = len(username_job)
	job_id = username_job[l-5::]
	username = [0:l-5]
	result = json.dumps(data['res'])
	u['request']=result
	u['username'] = username
	u['job_name'] = job_id
	return u
def benchmark_prep(data):
	uname = data['u']
	node = uname[0:2]
	size = uname[11::] #'92benchmark10'
	t = data['t']
	return {'node':node,'t':t,'size':size}
def is_benchmark(data):
	return 'benchmark' in data['u']
@asyncio.coroutine
def res_reader(socket, q):
	while True:
		data = yield from q.get()
		##here - check benchmark vs res
		if is_benchmark(data):
			yield from socket.emit('BM', benchmark_prep(data))
		else:
			yield from socket.emit('full_result_return', result_prep(data))
@asyncio.coroutine
def at_reader(socket, q):
	while True:
		data = yield from q.get()
		if data['command'] == "FN":
			#find base node
			#find neighbor address
			#find rssi
			upsert_data = {'source':1,'target':1,'value':1}
			yield from socket.emit('FN',upsert_data)
@asyncio.coroutine
def query_passer(controller, sid, data)
	query = json.loads(data)
	job = query['job']
	uname = query['username']
	userid = uname+job
	exec(query['code'])
	code_class = locals()['SenseReduce']()
	#here we should make call to dag-plan to get the nodes - TODO
	all_nodes = code_class.sense_nodes +code_class.reduce_nodes + code_class.map_nodes
	send_data = {'u':userid, 'f':query['code']}
	for node in all_nodes:
		yield controller.node_to_node(send_data, controller.comm.address_book[node])

if __name__ == "__main__":
	sio = socketio.AsyncServer()
	loop = asyncio.get_event_loop()
	app = web.Application(loop=loop)
	sio.attach(app) 
	### now start adding tasks to base loop ###
	comm = usense.Comm()
	controller = usense.ControlTasks(loop, comm)
    loop.add_reader(comm.uart.fd, usense.handle_stdin, comm, loop)
    query_gateway = functools.partial(query_passer, controller)
    sio.on('queryToGateway')(query_gateway)
    tasks = [controller.radio_listener(), controller.queue_placer(), controller.benchmark(),
             controller.function_definer(), controller.worker(), 
             at_reader(sio, controller.comm.at_queue), res_reader(sio, controller.comm.res_queue)]
    for task in tasks:
        asyncio.ensure_future(task)
    web.run_app(app)