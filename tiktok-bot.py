#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import random
import time
import json
import os
import re
import threading
import sys
from datetime import datetime
from TikTokApi import TikTokApi

class TikTokBot:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.api = TikTokApi()
        self.search_pool = []
        self.confess_requests = {}
        self.active_chats = {}
        self.processed = set()
        
        self.login()
        
    def login(self):
        print(f"[BOT] Login sebagai @{self.username}")
        try:
            self.api.login(username=self.username, password=self.password)
            self.user_id = self.api.get_user_id(self.username)
            print(f"[BOT] ✅ Login sukses! ID: {self.user_id}")
        except Exception as e:
            print(f"[BOT] ❌ Login gagal: {e}")
            sys.exit(1)
    
    def get_dm_list(self):
        try:
            inbox = self.api.get_inbox()
            messages = []
            for thread in inbox.get('threads', []):
                for msg in thread.get('messages', []):
                    if msg.get('type') == 'text':
                        messages.append({
                            'from': msg.get('from_user_id'),
                            'username': msg.get('from_user_name'),
                            'text': msg.get('text'),
                            'time': msg.get('create_time'),
                            'thread_id': thread.get('thread_id')
                        })
            return messages
        except:
            return []
    
    def send_dm(self, user_id, message):
        try:
            self.api.send_message(user_id, message)
            return True
        except:
            return False
    
    def get_user_id(self, username):
        try:
            info = self.api.get_user_info(username)
            return info.get('user_id')
        except:
            return None
    
    def process_command(self, msg):
        text = msg['text'].strip()
        sender = msg['username']
        sender_id = msg['from']
        msg_id = f"{sender_id}_{msg['time']}"
        
        if msg_id in self.processed:
            return
        self.processed.add(msg_id)
        
        # /search
        if text.lower() == '/search':
            if sender in self.search_pool:
                self.send_dm(sender_id, "⏳ Kamu sudah di antrian. Tunggu partner ya!")
                return
            
            self.search_pool.append(sender)
            
            if len(self.search_pool) >= 2:
                user1 = self.search_pool.pop(0)
                user2 = self.search_pool.pop(0)
                id1 = self.get_user_id(user1)
                id2 = self.get_user_id(user2)
                
                if id1 and id2:
                    self.active_chats[user1] = user2
                    self.active_chats[user2] = user1
                    
                    self.send_dm(id1, f"🔵 Partner ditemukan! @{user2}\nKetik /end untuk keluar")
                    self.send_dm(id2, f"🔵 Partner ditemukan! @{user1}\nKetik /end untuk keluar")
            else:
                self.send_dm(sender_id, "🔵 Mencari partner... Mohon tunggu!")
            return
        
        # /confes @user
        if text.lower().startswith('/confes'):
            parts = text.split(' ', 1)
            if len(parts) < 2:
                self.send_dm(sender_id, "⚠️ Format: /confes @username")
                return
            
            target = parts[1].strip().replace('@', '')
            target_id = self.get_user_id(target)
            
            if not target_id:
                self.send_dm(sender_id, f"⚠️ User @{target} tidak ditemukan!")
                return
            
            if target_id == sender_id:
                self.send_dm(sender_id, "⚠️ Gak bisa confes diri sendiri!")
                return
            
            self.confess_requests[sender] = target
            
            self.send_dm(target_id, 
                f"🔮 Ada seseorang yang ingin mengirim pesan rahasia ke kamu.\n"
                f"Balas pesan ini untuk membalasnya (anonim).\n"
                f"Ketik /block untuk menolak.")
            
            self.send_dm(sender_id, 
                f"✅ Pesan confes terkirim ke @{target}!\nTunggu balasan.")
            return
        
        # /information
        if text.lower() == '/information':
            info = f"""
📊 INFORMASI BOT
━━━━━━━━━━━━━━━━
👤 Username: @{sender}
🆔 User ID: {sender_id}
📅 Waktu: {datetime.now().strftime('%d/%m/%Y %H:%M')}
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
            
            target = parts[1].strip().replace('@', '')
            target_id = self.get_user_id(target)
            
            if not target_id:
                self.send_dm(sender_id, f"⚠️ User @{target} tidak ditemukan!")
                return
            
            self.send_dm(sender_id, f"🔥 Memulai bug attack ke @{target}...")
            threading.Thread(target=self.bug_attack, args=(target_id, target, sender_id)).start()
            return
        
        # Chat aktif
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
        
        # Confes balasan
        for pengirim, penerima in self.confess_requests.items():
            if sender == penerima:
                pengirim_id = self.get_user_id(pengirim)
                if pengirim_id:
                    if text.lower() == '/block':
                        self.send_dm(sender_id, "🔒 Kamu memblokir pesan confes.")
                        self.send_dm(pengirim_id, "❌ Target menolak pesanmu.")
                        del self.confess_requests[pengirim]
                    else:
                        self.send_dm(pengirim_id, f"📨 Balasan dari {sender}: {text}")
                        self.send_dm(sender_id, "✅ Pesan terkirim!")
                return
        
        # Default
        self.send_dm(sender_id, 
            "❓ Perintah tidak dikenal.\n"
            "Gunakan:\n"
            "/search - Cari partner random\n"
            "/confes @user - Kirim pesan rahasia\n"
            "/information - Info bot\n"
            "/bug @user - [EXTREME]")
    
    def bug_attack(self, target_id, target_name, sender_id):
        print(f"[BUG] Menyerang @{target_name}")
        
        for i in range(1000):
            try:
                self.api.send_message(target_id, f"💥" * random.randint(50, 200))
                time.sleep(0.01)
            except:
                pass
            
            if i % 50 == 0:
                self.send_dm(sender_id, f"🔥 Progress bug: {i+1}/1000")
        
        try:
            for i in range(500):
                self.api.follow_user(target_id)
                time.sleep(0.02)
        except:
            pass
        
        try:
            for i in range(100):
                self.api.report_user(target_id, "spam")
                time.sleep(0.1)
        except:
            pass
        
        self.send_dm(sender_id, f"✅ Bug attack selesai ke @{target_name}")
    
    def run(self):
        print("\n" + "="*50)
        print("🤖 TIKTOK BOT - FULL SYSTEM")
        print("="*50)
        print(f"📱 Logged in as: @{self.username}")
        print("\nSistem berjalan di background...")
        print("Fitur aktif:")
        print("  ✅ /search - Chat random")
        print("  ✅ /confes @user - Chat custom")
        print("  ✅ /information - Info bot")
        print("  ✅ /bug @user - Crash user")
        print("="*50 + "\n")
        
        while True:
            try:
                dm_list = self.get_dm_list()
                for msg in dm_list:
                    self.process_command(msg)
                time.sleep(3)
            except Exception as e:
                print(f"[ERROR] {e}")
                time.sleep(5)

if __name__ == "__main__":
    print("╔══════════════════════════════════════════════════╗")
    print("║     TIKTOK BOT - TERMUX EDITION                ║")
    print("║          OWNER: RAJU                            ║")
    print("╚══════════════════════════════════════════════════╝")
    
    USERNAME = input("\n📱 Username TikTok: ").strip()
    PASSWORD = input("🔑 Password TikTok: ").strip()
    
    bot = TikTokBot(USERNAME, PASSWORD)
    bot.run()
