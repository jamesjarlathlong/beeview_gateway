from aiohttp import web
import socketio
import asyncio
sio = socketio.AsyncServer()
loop = asyncio.get_event_loop()
app = web.Application(loop=loop)
sio.attach(app)


async def connect(sid, environ):
	await sio.emit('hello', {'payload':5})
@asyncio.coroutine
def message(sid, data):
	yield from asyncio.sleep(0)
	print('message: ', data)
@asyncio.coroutine
def intermittent(loop):
	while True:
		print('called: ',loop)
		yield from asyncio.sleep(1)
		yield from sio.emit('hello')
async def testing():
	while True:
		await asyncio.sleep(2)
		print('hello')
if __name__ == '__main__':
	#loop.add_reader('')
	sio.on('connect')(connect)
	sio.on('fromlocal')(message)
	asyncio.ensure_future(intermittent(loop))
	web.run_app(app)



