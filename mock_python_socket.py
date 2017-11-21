from aiohttp import web
import socketio
import asyncio as asyncio
import functools
import time
def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = yield from method(*args, **kw)
        te = time.time()
        ex_time = te-ts
        return ex_time,result
    return timed
sio = socketio.AsyncServer()
loop = asyncio.get_event_loop()
app = web.Application(loop=loop)
sio.attach(app)

class Connector:
	def __init__(self, d):
		self.d = d
	async def connect(self,sid, environ):
		print(self.d)
		await sio.emit(self.d, {'payload':5})
@asyncio.coroutine
@timeit
def timer(level=0):
	time.sleep(0.5)
	yield from asyncio.sleep(1)
	if level == 1:
		return 2
	else:
		a= yield from timer(level=level+1)
		return a
@asyncio.coroutine
def message(sid, data):
	yield from asyncio.sleep(0)
	print('message: ', data)

async def intermittent():
	while True:
		await asyncio.sleep(2)
		a,b=await timer()
		print(a,b)
		await sio.emit('hello')
if __name__ == '__main__':
	#loop.add_reader('')
	sio.on('connect')(Connector('hello').connect)
	sio.on('fromlocal')(message)
	asyncio.ensure_future(intermittent())
	web.run_app(app, port = 3556)



