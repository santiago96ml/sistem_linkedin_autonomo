import asyncio, json, sys
import websockets

async def test():
    try:
        print('Intentando conectar a ws://127.0.0.1:8001/ws/live/3')
        async with websockets.connect('ws://127.0.0.1:8001/ws/live/3') as ws:
            print('[OK] Conexion WS abierta exitosamente')
            await ws.send(json.dumps({"type": "press", "key": "a"}))
            print('[OK] Mensaje enviado')
            resp = await ws.recv()
            print('[OK] Datos recibidos:', resp[:100])
    except Exception as e:
        print('[ERROR] WS:', type(e).__name__, '-', str(e))

if __name__ == '__main__':
    asyncio.run(test())
