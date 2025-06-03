import socket
import threading

# Bağlı istemciler ve nickname'leri
clients = []
nicknames = []

# Mesajları tüm kullanıcılara gönder
def broadcast(message):
    for client in clients:
        try:
            client.send(message)
        except:
            pass

def handle(client):
    while True:
        try:
            # Mesajı al
            message = client.recv(1024)
            if not message:
                break
            broadcast(message)
        except:
            # Bağlantı koptu
            if client in clients:
                index = clients.index(client)
                clients.remove(client)
                nickname = nicknames[index]
                nicknames.remove(nickname)
                broadcast(f"{nickname} ayrıldı.".encode('utf-8'))
                client.close()
                break

def receive():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(('0.0.0.0', 12345))  # Tüm IP’lerden bağlanılır, port 12345
    server.listen()

    print("Sunucu başlatıldı, bağlantılar bekleniyor...")

    while True:
        client, address = server.accept()
        print(f"Bağlantı kuruldu: {str(address)}")

        client.send('NICK'.encode('utf-8'))  # İstemciden nickname iste

        nickname = client.recv(1024).decode('utf-8')
        nicknames.append(nickname)
        clients.append(client)

        print(f"Nickname: {nickname}")
        broadcast(f"{nickname} sohbete katıldı!".encode('utf-8'))
        client.send("Bağlandınız!".encode('utf-8'))

        thread = threading.Thread(target=handle, args=(client,))
        thread.start()

if __name__ == '__main__':
    receive()

