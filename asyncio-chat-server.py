#!/usr/bin/env python3

import asyncio

class Connection:
    def __init__(self, reader, writer, server):
        self.reader, self.writer, self.server = reader, writer, server
        self.id = writer.get_extra_info('peername')
        self.messages = asyncio.Queue()

    async def read_loop(self):
        while True:
            msg = await self.reader.readline()
            if not msg:
                break
            await self.server.send_message(self.id, msg)

        self.finish()

    async def write_loop(self):
        try:
            while True:
                msg = await self.messages.get()
                self.writer.write(msg)
                await self.writer.drain()
                self.messages.task_done()
        except Exception as e:
            raise
        finally:
            self.writer.close()

    async def send_message(self, msg):
        await self.messages.put(msg)

    def finish(self):
        self.write_task.cancel()

    async def run(self):
        self.writer.write(f"Welcome {self.id}\n".encode())
        await self.writer.drain()

        self.server.register_connection(self.id, self)

        self.write_task = asyncio.create_task(self.write_loop())
        await asyncio.gather(asyncio.create_task(self.read_loop()), self.write_task, return_exceptions=True)

        self.server.remove_connection(self.id)

class ChatServer:
    def __init__(self, port: int):
        self.port = port
        self.connections = {}

    async def connection_handler(self, reader, writer):
        asyncio.create_task(Connection(reader, writer, self).run())

    def register_connection(self, id, connection):
        print(f"{id} joined the server")
        self.connections[id] = connection

    def remove_connection(self, id):
        print(f"{id} left the server")
        del self.connections[id]

    async def send_message(self, id, msg):
        await self.messages.put((id, f"{id}: {bytes.decode(msg)}".encode()))

    async def messages_loop(self):
        while True:
            src, msg = await self.messages.get()
            for dst, connection in self.connections.items():
                if src == dst:
                    continue
                await connection.send_message(msg)
            self.messages.task_done()

    async def run(self):
        self.messages = asyncio.Queue()
        server = await asyncio.start_server(self.connection_handler, '127.0.0.1', self.port)
        async with server:
            await asyncio.gather(self.messages_loop(), server.serve_forever())

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    try:
        asyncio.run(ChatServer(31337).run())
    except KeyboardInterrupt as e:
        loop.close()
