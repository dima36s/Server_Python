import asyncio
import datetime
import pickle
import socket
import pr_pb2 as pr


async def server_main():
    HOST = "127.0.0.1"
    PORT = 5000
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))  # Метод используется для связывания сокета с определенным сетевым интерфейсом и номером порта
    server.listen(1)
    server.setblocking(False)

    while True:
        client, addr = await loop.sock_accept(server)
        if client:
            global client_count
            client_count += 1
            log_file = open('log.log', 'a', encoding='utf-8')
            log_file.write('{} Connection from {}\n'.format(datetime.datetime.now(), addr))
            log_file.close()
            print("----- Connected -----")
            loop.create_task(handler(client, addr))


async def handler(client, addr):
    global client_count
    with client:
        while True:
            data = await loop.sock_recv(client, 1000)
            if not data:
                break
            message = pr.WrapperMessage()
            message.ParseFromString(pickle.loads(data))  # парсинг байтовой строки от клиента в WrapperMessage
            print('Data received: {!r}'.format(message))
            resp = pr.WrapperMessage()
            if message.request_for_slow_response.time_in_seconds_to_sleep != 0:
                resp.slow_response.connected_client_count = client_count
                await asyncio.sleep(message.request_for_slow_response.time_in_seconds_to_sleep)
            else:
                resp.fast_response.current_date_time = str(datetime.datetime.now())
            data2 = pickle.dumps(resp.SerializeToString())
            print('Send: {!r}'.format(data2))
            await loop.sock_sendall(client, data2)
        client_count -= 1
    print("----- Disconnected -----")
    f = open('log.log', 'a', encoding='utf-8')
    f.write('{} Close connection from {}\n'.format(datetime.datetime.now(), addr))
    f.close()


if __name__ == '__main__':
    global client_count
    client_count = 0
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    file = open('log.log', 'w')
    file.close()
    loop.create_task(server_main())
    loop.run_forever()
