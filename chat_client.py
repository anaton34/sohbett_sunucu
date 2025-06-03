import socket
import threading
from datetime import datetime
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.clock import mainthread
from kivy.uix.spinner import Spinner

# Basit emoji listesi (istediğin kadar ekleyebilirsin)
EMOJIS = ['😀', '😂', '😎', '👍', '❤️', '🎉', '😢', '🤔']

class ChatClient(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'

        # Kullanıcı adı girişi popup ile al
        self.nickname = None
        self.show_nickname_popup()

        # Chat log - mesajlar
        self.chat_log = GridLayout(cols=1, size_hint_y=None, padding=5, spacing=5)
        self.chat_log.bind(minimum_height=self.chat_log.setter('height'))
        scroll = ScrollView(size_hint=(1, 0.7))
        scroll.add_widget(self.chat_log)

        # Mesaj input + emoji butonu + gönder butonu
        input_layout = BoxLayout(size_hint=(1, 0.1))

        self.message_input = TextInput(multiline=False)
        input_layout.add_widget(self.message_input)

        emoji_btn = Button(text='😊', size_hint=(0.1, 1))
        emoji_btn.bind(on_press=self.show_emoji_picker)
        input_layout.add_widget(emoji_btn)

        send_btn = Button(text='Gönder', size_hint=(0.2, 1))
        send_btn.bind(on_press=self.send_message)
        input_layout.add_widget(send_btn)

        # Alt kısım: Online kullanıcılar listesi + kullanıcı adı değiştirme butonu
        bottom_layout = BoxLayout(size_hint=(1, 0.2), padding=5, spacing=5)

        # Çevrimiçi kullanıcılar paneli
        user_list_layout = BoxLayout(orientation='vertical', size_hint=(0.3, 1))
        user_list_layout.add_widget(Label(text="Çevrimiçi Kullanıcılar:", size_hint=(1, 0.1)))
        self.user_list = GridLayout(cols=1, size_hint_y=None)
        self.user_list.bind(minimum_height=self.user_list.setter('height'))
        user_scroll = ScrollView()
        user_scroll.add_widget(self.user_list)
        user_list_layout.add_widget(user_scroll)

        bottom_layout.add_widget(user_list_layout)

        # Sağ taraf: nickname değiştirme ve özel mesaj için seçici
        right_layout = BoxLayout(orientation='vertical', size_hint=(0.7, 1), spacing=10)

        # Nickname değiştirme butonu
        change_nick_btn = Button(text="Nickname Değiştir", size_hint=(1, 0.2))
        change_nick_btn.bind(on_press=self.show_nickname_popup)
        right_layout.add_widget(change_nick_btn)

        # Özel mesaj için kullanıcı seçimi
        self.private_msg_spinner = Spinner(
            text='Genel',
            values=['Genel'],  # Bağlandıktan sonra sunucudan güncellenecek
            size_hint=(1, 0.2)
        )
        right_layout.add_widget(Label(text="Özel Mesaj Gönderilecek Kullanıcı:", size_hint=(1, 0.1)))
        right_layout.add_widget(self.private_msg_spinner)

        bottom_layout.add_widget(right_layout)

        self.add_widget(scroll)
        self.add_widget(input_layout)
        self.add_widget(bottom_layout)

        # Socket tanımı
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Sunucu IP ve portu
        self.server_ip = '192.168.45.100'  # buraya kendi sunucu IP'sini yaz
        self.server_port = 12345

        # Mesaj tarih formatı
        self.time_format = "%H:%M"

    def show_nickname_popup(self, *args):
        content = BoxLayout(orientation='vertical', padding=10, spacing=10)
        nick_input = TextInput(multiline=False, hint_text="Nickname Giriniz")
        btn_ok = Button(text="Tamam", size_hint=(1, 0.3))
        content.add_widget(nick_input)
        content.add_widget(btn_ok)
        popup = Popup(title="Kullanıcı Adı", content=content, size_hint=(0.5, 0.3), auto_dismiss=False)

        def on_ok(instance):
            nickname = nick_input.text.strip()
            if nickname:
                self.nickname = nickname
                popup.dismiss()
                self.connect_to_server()
            else:
                nick_input.hint_text = "Boş olamaz!"

        btn_ok.bind(on_press=on_ok)
        popup.open()

    def show_emoji_picker(self, instance):
        content = GridLayout(cols=5, padding=10, spacing=10)
        popup = Popup(title="Emoji Seç", content=content, size_hint=(0.6, 0.4))

        def select_emoji(btn):
            self.message_input.text += btn.text
            popup.dismiss()

        for emoji in EMOJIS:
            btn = Button(text=emoji, font_size=32)
            btn.bind(on_press=select_emoji)
            content.add_widget(btn)

        popup.open()

    def connect_to_server(self):
        try:
            self.client.connect((self.server_ip, self.server_port))
            self.add_chat_message(f"✅ Sunucuya bağlandı: {self.server_ip}:{self.server_port}", system=True)

            # Sunucuya nickname gönderilecek
            threading.Thread(target=self.handle_server_messages, daemon=True).start()
        except Exception as e:
            self.add_chat_message(f"❌ Sunucuya bağlanılamadı: {e}", system=True)

    def handle_server_messages(self):
        try:
            while True:
                msg = self.client.recv(2048).decode('utf-8')
                if msg == 'NICK':
                    self.client.send(self.nickname.encode('utf-8'))
                elif msg.startswith('USERLIST:'):
                    # Çevrimiçi kullanıcı listesi güncellemesi
                    users_str = msg[len('USERLIST:'):].strip()
                    users = users_str.split(',') if users_str else []
                    self.update_user_list(users)
                else:
                    self.add_chat_message(msg)
        except Exception as e:
            self.add_chat_message(f"⚠️ Bağlantı hatası: {e}", system=True)

    def send_message(self, instance):
        msg = self.message_input.text.strip()
        if msg:
            target_user = self.private_msg_spinner.text
            if target_user == 'Genel':
                full_msg = f"{self.nickname}: {msg}"
            else:
                # Özel mesaj formatı (sunucu buna göre ayarlanmalı)
                full_msg = f"PRIVATE::{target_user}::{self.nickname}: {msg}"
            try:
                self.client.send(full_msg.encode('utf-8'))
                self.message_input.text = ''
                # Mesaj gönderildi bildirimi
                self.add_chat_message(f"[{self.get_time()}] Sen -> {target_user}: {msg}", own=True)
            except Exception as e:
                self.add_chat_message(f"❌ Gönderilemedi: {e}", system=True)

    @mainthread
    def add_chat_message(self, msg, system=False, own=False):
        time_str = self.get_time()
        if system:
            label = Label(text=f"[{time_str}] {msg}", size_hint_y=None, height=30, color=(1,0,0,1))
        elif own:
            label = Label(text=f"[{time_str}] {msg}", size_hint_y=None, height=30, color=(0,0,1,1))
        else:
            label = Label(text=f"[{time_str}] {msg}", size_hint_y=None, height=30, color=(0,0,0,1))
        self.chat_log.add_widget(label)
        # Otomatik scroll en alta indir
        self.chat_log.parent.scroll_y = 0

    @mainthread
    def update_user_list(self, users):
        self.user_list.clear_widgets()
        self.private_msg_spinner.values = ['Genel'] + users
        for user in users:
            lbl = Label(text=user, size_hint_y=None, height=30)
            self.user_list.add_widget(lbl)

    def get_time(self):
        return datetime.now().strftime(self.time_format)

class ChatApp(App):
    def build(self):
        return ChatClient()

if __name__ == '__main__':
    ChatApp().run()
