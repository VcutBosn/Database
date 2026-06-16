#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import random
import hashlib
import threading
import requests
import re
import sqlite3
from datetime import datetime

# ==================== KONFIG ====================
CONFIG = {
    "email": "toyaparkerreal2982@gmail.com",
    "password": "yayaaja123_.",
    "username": "iyanlagibobo1"
}

# ==================== DATABASE ====================
class Database:
    def __init__(self):
        self.conn = sqlite3.connect('bot.db')
        self.c = self.conn.cursor()
        self.c.execute('''CREATE TABLE IF NOT EXISTS users
                         (id TEXT, username TEXT, blocked INTEGER DEFAULT 0)''')
        self.c.execute('''CREATE TABLE IF NOT EXISTS chats
                         (id TEXT, user1 TEXT, user2 TEXT)''')
        self.conn.commit()
    
    def add_user(self, uid, username):
        self.c.execute('INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)', (uid, username))
        self.conn.commit()
    
    def is_blocked(self, uid):
        self.c.execute('SELECT blocked FROM users WHERE id = ?', (uid,))
        r = self.c.fetchone()
        return r and r[0] == 1
    
    def block(self, uid):
        self.c.execute('UPDATE users SET blocked = 1 WHERE id = ?', (uid,))
        self.conn.commit()
    
    def create_chat(self, cid, u1, u2):
        self.c.execute('INSERT INTO chats (id, user1, user2) VALUES (?, ?, ?)', (cid, u1, u2))
        self.conn.commit()
    
    def delete_chat(self, cid):
        self.c.execute('DELETE FROM chats WHERE id = ?', (cid,))
        self.conn.commit()
    
    def get_partner(self, uid):
        self.c.execute('SELECT id, user1, user2 FROM chats WHERE user1 = ? OR user2 = ?', (uid, uid))
        r = self.c.fetchone()
        if r:
            return r[1] if r[1] != uid else r[2]
        return None

# ==================== BOT ====================
class Bot:
    def __init__(self):
        self.db = Database()
        self.s = requests.Session()
        self.s.headers.update({
            'User-Agent': 'Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36',
            'Accept': 'application/json'
        })
        self.waiting = []
        self.chats = {}
        self.reports = {}
    
    def login(self):
        try:
            r = self.s.get('https://www.tiktok.com/')
            csrf = None
            for c in self.s.cookies:
                if c.name == 'csrfToken':
                    csrf = c.value
                    break
            if not csrf:
                match = re.search(r'csrfToken:\s*"([^"]+)"', r.text)
                csrf = match.group(1) if match else ''
            
            r = self.s.post('https://www.tiktok.com/api/v1/auth/login', json={
                'email': CONFIG['email'],
                'password': CONFIG['password'],
                'csrfToken': csrf
            })
            if r.status_code == 200 and r.json().get('data', {}).get('user'):
                print(f"Login as @{CONFIG['username']}")
                return True
            return False
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    def send(self, target, msg):
        try:
            r = self.s.get('https://www.tiktok.com/api/v1/user/detail/', params={'username': target})
            uid = r.json().get('data', {}).get('user', {}).get('id')
            if not uid:
                return False
            r = self.s.post('https://www.tiktok.com/api/v1/message/send', json={
                'recipient_id': uid,
                'text': msg,
                'type': 'text'
            })
            return r.status_code == 200
        except:
            return False
    
    def get_inbox(self):
        try:
            r = self.s.get('https://www.tiktok.com/api/v1/inbox/list', params={'limit': 20})
            msgs = r.json().get('data', {}).get('messages', [])
            result = []
            for m in msgs:
                sender = m.get('sender', {}).get('unique_id', '')
                text = m.get('text', '')
                if sender and text:
                    result.append({'sender': sender, 'text': text})
            return result
        except:
            return []
    
    def follow(self, target):
        try:
            r = self.s.get('https://www.tiktok.com/api/v1/user/detail/', params={'username': target})
            uid = r.json().get('data', {}).get('user', {}).get('id')
            if not uid:
                return False
            r = self.s.post('https://www.tiktok.com/api/v1/follow/', json={'user_id': uid})
            return r.status_code == 200
        except:
            return False
    
    def unfollow(self, target):
        try:
            r = self.s.get('https://www.tiktok.com/api/v1/user/detail/', params={'username': target})
            uid = r.json().get('data', {}).get('user', {}).get('id')
            if not uid:
                return False
            r = self.s.post('https://www.tiktok.com/api/v1/unfollow/', json={'user_id': uid})
            return r.status_code == 200
        except:
            return False
    
    def like(self, url):
        try:
            match = re.search(r'/video/(\d+)', url)
            if not match:
                return False
            vid = match.group(1)
            r = self.s.post('https://www.tiktok.com/api/v1/like/', json={'video_id': vid})
            return r.status_code == 200
        except:
            return False

# ==================== MENU ====================
def menu():
    return """MENU BOT

/search - Chat random
/chat @user - Chat custom
/follow @user - Follow
/unfollow @user - Unfollow
/like <url> - Like video
/next - Ganti partner
/end - Keluar chat
/report - Lapor partner
/info - Info bot

[SEARCH] [CHAT] [FOLLOW]
[LIKE] [INFO] [HELP]"""

# ==================== HANDLE ====================
def handle(bot, sender, uid, text):
    cmd = text.lower().strip()
    
    if bot.db.is_blocked(uid):
        return
    
    bot.db.add_user(uid, sender)
    
    if cmd in ['/menu', '/help', '/start']:
        bot.send(sender, menu())
    
    elif cmd == '/search':
        if bot.waiting:
            partner = bot.waiting.pop(0)
            cid = hashlib.md5(f"{uid}{partner}{time.time()}".encode()).hexdigest()[:16]
            bot.db.create_chat(cid, uid, partner)
            bot.chats[uid] = partner
            bot.chats[partner] = uid
            bot.send(sender, "Partner ditemukan!")
            pname = bot.db.c.execute('SELECT username FROM users WHERE id = ?', (partner,)).fetchone()
            if pname:
                bot.send(pname[0], "Partner ditemukan!")
        else:
            bot.waiting.append(uid)
            bot.send(sender, "Mencari partner...")
    
    elif cmd.startswith('/chat @'):
        target = cmd.replace('/chat @', '').strip()
        if not target:
            bot.send(sender, "Format: /chat @username")
            return
        cid = hashlib.md5(f"{uid}{target}{time.time()}".encode()).hexdigest()[:16]
        bot.db.create_chat(cid, uid, target)
        bot.chats[uid] = target
        bot.send(sender, f"Chat dengan @{target} dimulai.")
        bot.send(target, f"@{sender} chat denganmu.")
    
    elif cmd.startswith('/follow @'):
        target = cmd.replace('/follow @', '').strip()
        if bot.follow(target):
            bot.send(sender, f"Follow @{target} sukses")
        else:
            bot.send(sender, "Gagal follow")
    
    elif cmd.startswith('/unfollow @'):
        target = cmd.replace('/unfollow @', '').strip()
        if bot.unfollow(target):
            bot.send(sender, f"Unfollow @{target} sukses")
        else:
            bot.send(sender, "Gagal unfollow")
    
    elif cmd.startswith('/like'):
        url = cmd.replace('/like', '').strip()
        if bot.like(url):
            bot.send(sender, "Like sukses")
        else:
            bot.send(sender, "Gagal like")
    
    elif cmd == '/next':
        if uid in bot.chats:
            partner = bot.chats[uid]
            cid = bot.db.c.execute('SELECT id FROM chats WHERE (user1 = ? AND user2 = ?) OR (user1 = ? AND user2 = ?)', 
                                   (uid, partner, partner, uid)).fetchone()
            if cid:
                bot.db.delete_chat(cid[0])
            if partner in bot.chats:
                del bot.chats[partner]
            del bot.chats[uid]
            if uid in bot.waiting:
                bot.waiting.remove(uid)
            bot.send(sender, "Keluar chat.")
    
    elif cmd == '/end':
        if uid in bot.chats:
            partner = bot.chats[uid]
            cid = bot.db.c.execute('SELECT id FROM chats WHERE (user1 = ? AND user2 = ?) OR (user1 = ? AND user2 = ?)',
                                   (uid, partner, partner, uid)).fetchone()
            if cid:
                bot.db.delete_chat(cid[0])
            if partner in bot.chats:
                pname = bot.db.c.execute('SELECT username FROM users WHERE id = ?', (partner,)).fetchone()
                if pname:
                    bot.send(pname[0], "Partner mengakhiri chat.")
                del bot.chats[partner]
            del bot.chats[uid]
            if uid in bot.waiting:
                bot.waiting.remove(uid)
            bot.send(sender, "Chat diakhiri.")
    
    elif cmd == '/report':
        if uid in bot.chats:
            partner = bot.chats[uid]
            bot.reports[partner] = bot.reports.get(partner, 0) + 1
            if bot.reports[partner] >= 3:
                bot.db.block(partner)
                bot.send(sender, "Partner diblokir.")
            else:
                bot.send(sender, f"Laporan terkirim ({bot.reports[partner]}/3)")
        else:
            bot.send(sender, "Tidak ada partner.")
    
    elif cmd == '/info':
        users = bot.db.c.execute('SELECT * FROM users').fetchall()
        info = f"""INFO BOT
Owner: RAJU
Users: {len(users)}
Active: {len(bot.chats)}
Waiting: {len(bot.waiting)}
Status: ONLINE"""
        bot.send(sender, info)
    
    else:
        if uid in bot.chats:
            partner = bot.chats[uid]
            if isinstance(partner, str) and not partner.startswith('@'):
                pname = bot.db.c.execute('SELECT username FROM users WHERE id = ?', (partner,)).fetchone()
                if pname:
                    bot.send(pname[0], f"{sender}: {text}")
            else:
                bot.send(partner, f"{sender}: {text}")
        else:
            bot.send(sender, "Tidak ada partner. /search")

# ==================== MAIN ====================
def main():
    bot = Bot()
    if not bot.login():
        print("Login gagal!")
        return
    
    print(f"Bot running as @{CONFIG['username']}")
    print("="*50)
    print(menu())
    print("="*50)
    
    while True:
        try:
            msgs = bot.get_inbox()
            for msg in msgs:
                if msg['sender'] == CONFIG['username']:
                    continue
                uid = hashlib.md5(msg['sender'].encode()).hexdigest()[:16]
                handle(bot, msg['sender'], uid, msg['text'])
            time.sleep(3)
        except KeyboardInterrupt:
            print("\nStopped")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
