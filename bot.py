#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import random
import threading
import sys
import json
import os
from datetime import datetime

# ===== KONFIGURASI =====
USERNAME = ""  # Isi nanti
PASSWORD = ""  # Isi nanti
VERSION = "2.0"

# ===== CLASS UTAMA =====
class TikTokBot:
    def __init__(self):
        self.search_queue = []
        self.active_chats = {}
        self.confess_data = {}
        self.processed_msgs = set()
        self.running = True
        
        # Inisialisasi API
        self.init_api()
        
    def init_api(self):
        """Inisialisasi TikTok API"""
        try:
            from TikTokApi import TikTokApi
            self.api = TikTokApi()
            print("[✓] TikTok API loaded")
        except ImportError:
            print("[✗] TikTokApi not installed. Run: pip install TikTokApi")
            sys.exit(1)
            
    def login(self, username, password):
        """Login ke TikTok"""
        self.username = username
        self.password = password
        print(f"[BOT] Logging in as @{username}...")
        
        try:
            self.api.login(username=username, password=password)
            self.user_id = self.api.get_user_id(username)
            print(f"[BOT] ✅ Login success! ID: {self.user_id}")
            return True
        except Exception as e:
            print(f"[BOT] ❌ Login failed: {e}")
            return False
    
    def get_dms(self):
        """Ambil DM masuk"""
        try:
            inbox = self.api.get_inbox()
            messages = []
            for thread in inbox.get('threads', []):
                for msg in thread.get('messages', []):
                    if msg.get('type') == 'text':
                        messages.append({
                            'from_id': msg.get('from_user_id'),
                            'username': msg.get('from_user_name'),
                            'text': msg.get('text', ''),
                            'time': msg.get('create_time'),
                            'thread_id': thread.get('thread_id')
                        })
            return messages
        except Exception as e:
            print(f"[!] Error getting DMs: {e}")
            return []
    
    def send_dm(self, user_id, message):
        """Kirim DM"""
        try:
            self.api.send_message(user_id, message)
            return True
        except Exception as e:
            print(f"[!] Error sending DM: {e}")
            return False
    
    def get_user_id(self, username):
        """Cari user ID dari username"""
        try:
            info = self.api.get_user_info(username)
            return info.get('user_id')
        except:
            return None
    
    def handle_search(self, sender, sender_id):
        """Fitur /search - Cari partner random"""
        if sender in self.search_queue:
            self.send_dm(sender_id, "⏳ Kamu sudah di antrian. Tunggu ya!")
            return
        
        self.search_queue.append(sender)
        
        if len(self.search_queue) >= 2:
            user1 = self.search_queue.pop(0)
            user2 = self.search_queue.pop(0)
            id1 = self.get_user_id(user1)
            id2 = self.get_user_id(user2)
            
            if id1 and id2:
                self.active_chats[user1] = user2
                self.active_chats[user2] = user1
                
                self.send_dm(id1, f"🔵 Partner ditemukan! @{user2}\nKetik /end untuk keluar")
                self.send_dm(id2, f"🔵 Partner ditemukan! @{user1}\nKetik /end untuk keluar")
                print(f"[✓] Match: @{user1} <-> @{user2}")
        else:
            self.send_dm(sender_id, "🔵 Mencari partner... Mohon tunggu!")
    
    def handle_confess(self, sender, sender_id, target):
        """Fitur /confes @user - Kirim pesan rahasia"""
        target = target.strip().replace('@', '')
        target_id = self.get_user_id(target)
        
        if not target_id:
            self.send_dm(sender_id, f"⚠️ User @{target} tidak ditemukan!")
            return
        
        if target_id == sender_id:
            self.send_dm(sender_id, "⚠️ Gak bisa confes diri sendiri!")
            return
        
        self.confess_data[sender] = target
        
        self.send_dm(target_id, 
            f"🔮 Ada seseorang yang ingin mengirim pesan rahasia ke kamu.\n"
            f"Balas pesan ini untuk membalasnya (anonim).\n"
            f"Ketik /block untuk menolak.")
        
        self.send_dm(sender_id, 
            f"✅ Pesan confes terkirim ke @{target}!\nTunggu balasan.")
        print(f"[✓] Confess: @{sender} -> @{target}")
    
    def handle_bug(self, sender_id, target):
        """Fitur /bug @user - Crash akun target"""
        target = target.strip().replace('@', '')
        target_id = self.get_user_id(target)
        
        if not target_id:
            self.send_dm(sender_id, f"⚠️ User @{target} tidak ditemukan!")
            return
        
        self.send_dm(sender_id, f"🔥 Memulai bug attack ke @{target}...")
        print(f"[🔥] Bug attack started on @{target}")
        
        # Jalankan di thread terpisah
        threading.Thread(target=self.bug_attack, args=(target_id, target, sender_id)).start()
    
    def bug_attack(self, target_id, target_name, sender_id):
        """Eksekusi bug attack"""
        print(f"[BUG] Attacking @{target_name}")
        
        # 1. Spam DM
        for i in range(1000):
            try:
                self.api.send_message(target_id, f"💥" * random.randint(50, 200))
                time.sleep(0.01)
            except:
                pass
            if i % 50 == 0:
                self.send_dm(sender_id, f"🔥 Progress: {i+1}/1000")
        
        # 2. Follow spam
        try:
            for i in range(500):
                self.api.follow_user(target_id)
                time.sleep(0.02)
        except:
            pass
        
        # 3. Report spam
        try:
            for i in range(100):
                self.api.report_user(target_id, "spam")
                time.sleep(0.1)
        except:
            pass
        
        self.send_dm(sender_id, f"✅ Bug attack selesai ke @{target_name}")
        print(f"[✓] Bug attack completed on @{target_name}")
    
    def process_command(self, msg):
        """Proses perintah dari DM"""
        text = msg['text'].strip()
        sender = msg['username']
        sender_id = msg['from_id']
        msg_id = f"{sender_id}_{msg['time']}"
        
        # Cegah duplikat
        if msg_id in self.processed_msgs:
            return
        self.processed_msgs.add(msg_id)
        
        # ===== COMMAND HANDLER =====
        
        # /search
        if text.lower() == '/search':
            self.handle_search(sender, sender_id)
            return
        
        # /confes @user
        if text.lower().startswith('/confes'):
            parts = text.split(' ', 1)
            if len(parts) < 2:
                self.send_dm(sender_id, "⚠️ Format: /confes @username")
                return
            self.handle_confess(sender, sender_id, parts[1])
            return
        
        # /information
        if text.lower() == '/information':
            info = f"""
📊 INFORMASI BOT
━━━━━━━━━━━━━━━━
👤 Username: @{sender}
🆔 User ID: {sender_id}
📅 Waktu: {datetime.now().strftime('%d/%m/%Y %H:%M')}
📌 Version: {VERSION}
━━━━━━━━━━━━━━━━
🔹 /search - Cari partner random
🔹 /confes @user - Kirim pesan rahasia
🔹 /information - Info ini
🔹 /bug @user - [EXTREME]
━━━━━━━━━━━━━━━━
"""
            self.send_dm(sender_id, info)
            return
        
        # /bug @user
        if text.lower().startswith('/bug'):
            parts = text.split(' ', 1)
            if len(parts) < 2:
                self.send_dm(sender_id, "⚠️ Format: /bug @username")
                return
            self.handle_bug(sender_id, parts[1])
            return
        
        # ===== CHAT AKTIF =====
        if sender in self.active_chats:
            partner = self.active_chats[sender]
            partner_id = self.get_user_id(partner)
            
            if partner_id:
                if text.lower() == '/end':
                    self.send_dm(sender_id, "👋 Chat ended. Ketik /search untuk mulai lagi")
                    self.send_dm(partner_id, "👋 Partner meninggalkan chat.")
                    del self.active_chats[sender]
                    del self.active_chats[partner]
                else:
                    self.send_dm(partner_id, f"💬 {sender}: {text}")
            return
        
        # ===== CONFESS REPLY =====
        for pengirim, penerima in self.confess_data.items():
            if sender == penerima:
                pengirim_id = self.get_user_id(pengirim)
                if pengirim_id:
                    if text.lower() == '/block':
                        self.send_dm(sender_id, "🔒 Kamu memblokir pesan confes.")
                        self.send_dm(pengirim_id, "❌ Target menolak pesanmu.")
                        del self.confess_data[pengirim]
                    else:
                        self.send_dm(pengirim_id, f"📨 Balasan dari {sender}: {text}")
                        self.send_dm(sender_id, "✅ Pesan terkirim!")
                return
        
        # ===== DEFAULT =====
        self.send_dm(sender_id, 
            "❓ Perintah tidak dikenal.\n"
            "Gunakan:\n"
            "/search - Cari partner random\n"
            "/confes @user - Kirim pesan rahasia\n"
            "/information - Info bot\n"
            "/bug @user - [EXTREME]")
    
    def run(self):
        """Main loop"""
        print("\n" + "="*50)
        print("🤖 TIKTOK BOT v{}".format(VERSION))
        print("="*50)
        print(f"📱 Logged in as: @{self.username}")
        print("\nSistem berjalan di background...")
        print("Fitur aktif:")
        print("  ✅ /search - Chat random")
        print("  ✅ /confes @user - Chat custom")
        print("  ✅ /information - Info bot")
        print("  ✅ /bug @user - Crash user")
        print("="*50 + "\n")
        print("[BOT] Menunggu DM...")
        
        while self.running:
            try:
                dms = self.get_dms()
                for msg in dms:
                    self.process_command(msg)
                time.sleep(3)
            except KeyboardInterrupt:
                print("\n[BOT] Shutting down...")
                self.running = False
                break
            except Exception as e:
                print(f"[!] Error: {e}")
                time.sleep(5)

# ===== MAIN =====
if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════╗")
    print("║     TIKTOK BOT - TERMUX EDITION                ║")
    print("║          OWNER: RAJU                            ║")
    print("╚══════════════════════════════════════════════════╝")
    
    bot = TikTokBot()
    
    username = input("\n📱 Username TikTok: ").strip()
    password = input("🔑 Password TikTok: ").strip()
    
    if bot.login(username, password):
        bot.run()
    else:
        print("[✗] Gagal login. Cek username & password.")
