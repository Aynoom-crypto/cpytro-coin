#!/usr/bin/env python3
"""
CpyTro (CPT) Cryptocurrency - Mobile Mining Coin
Main Blockchain Implementation
"""

import hashlib
import json
import time
import threading
from datetime import datetime
from typing import List, Dict, Optional, Tuple
import socket
import pickle
import base64
from dataclasses import dataclass, field
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
import requests
import sqlite3
import os
from enum import Enum
import logging

# ================ คอนฟิกูเรชัน ================

# พารามิเตอร์เครือข่าย
VERSION = "1.0.0"
NETWORK_PORT = 8333
RPC_PORT = 8334
MAX_SUPPLY = 210_000_000
INITIAL_BLOCK_REWARD = 50
HALVING_INTERVAL = 1_050_000  # บล็อก
DIFFICULTY_ADJUSTMENT_INTERVAL = 2016  # บล็อก
TARGET_BLOCK_TIME = 120  # วินาที
MAX_BLOCK_SIZE = 1_000_000  # 1 MB

# Database
DATABASE_FILE = "cpytro_blockchain.db"

# ตั้งค่า logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('cpytro.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CpyTro")

# ================ โครงสร้างข้อมูล ================

class TransactionType(Enum):
    COINBASE = "coinbase"
    REGULAR = "regular"
    STAKE = "stake"

@dataclass
class TransactionInput:
    txid: str  # Transaction ID of the output being spent
    vout: int  # Index of the output in the transaction
    signature: str
    pubkey: str

@dataclass
class TransactionOutput:
    value: float
    script_pubkey: str  # Locking script/address

@dataclass
class Transaction:
    txid: str = ""
    version: int = 1
    inputs: List[TransactionInput] = field(default_factory=list)
    outputs: List[TransactionOutput] = field(default_factory=list)
    locktime: int = 0
    type: TransactionType = TransactionType.REGULAR
    
    def calculate_hash(self) -> str:
        """Calculate transaction ID"""
        tx_data = {
            'version': self.version,
            'inputs': [(inp.txid, inp.vout) for inp in self.inputs],
            'outputs': [(out.value, out.script_pubkey) for out in self.outputs],
            'locktime': self.locktime,
            'type': self.type.value
        }
        tx_json = json.dumps(tx_data, sort_keys=True)
        return hashlib.sha256(tx_json.encode()).hexdigest()

@dataclass
class BlockHeader:
    version: int
    previous_hash: str
    merkle_root: str
    timestamp: int
    bits: int  # Difficulty target
    nonce: int
    
    def calculate_hash(self) -> str:
        header_data = f"{self.version}{self.previous_hash}{self.merkle_root}" \
                     f"{self.timestamp}{self.bits}{self.nonce}"
        return hashlib.sha256(header_data.encode()).hexdigest()

@dataclass
class Block:
    header: BlockHeader
    transactions: List[Transaction]
    height: int = 0
    
    def calculate_merkle_root(self) -> str:
        """Calculate Merkle root from transactions"""
        if not self.transactions:
            return "0" * 64
            
        tx_hashes = [tx.calculate_hash() for tx in self.transactions]
        
        while len(tx_hashes) > 1:
            new_hashes = []
            for i in range(0, len(tx_hashes), 2):
                if i + 1 < len(tx_hashes):
                    combined = tx_hashes[i] + tx_hashes[i + 1]
                else:
                    combined = tx_hashes[i] + tx_hashes[i]
                new_hash = hashlib.sha256(combined.encode()).hexdigest()
                new_hashes.append(new_hash)
            tx_hashes = new_hashes
        
        return tx_hashes[0] if tx_hashes else "0" * 64

# ================ ฐานข้อมูลบล็อคเชน ================

class BlockchainDB:
    def __init__(self, db_file=DATABASE_FILE):
        self.db_file = db_file
        self.init_database()
    
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # ตารางบล็อก
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blocks (
                height INTEGER PRIMARY KEY,
                hash TEXT UNIQUE,
                previous_hash TEXT,
                version INTEGER,
                merkle_root TEXT,
                timestamp INTEGER,
                bits INTEGER,
                nonce INTEGER,
                difficulty REAL,
                transaction_count INTEGER
            )
        ''')
        
        # ตารางธุรกรรม
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                txid TEXT PRIMARY KEY,
                block_height INTEGER,
                version INTEGER,
                locktime INTEGER,
                type TEXT,
                FOREIGN KEY (block_height) REFERENCES blocks(height)
            )
        ''')
        
        # ตาราง Transaction Inputs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tx_inputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                txid TEXT,
                input_index INTEGER,
                spent_txid TEXT,
                spent_vout INTEGER,
                signature TEXT,
                pubkey TEXT,
                FOREIGN KEY (txid) REFERENCES transactions(txid)
            )
        ''')
        
        # ตาราง Transaction Outputs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tx_outputs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                txid TEXT,
                output_index INTEGER,
                value REAL,
                script_pubkey TEXT,
                spent INTEGER DEFAULT 0,
                FOREIGN KEY (txid) REFERENCES transactions(txid)
            )
        ''')
        
        # ตาราง UTXO (Unspent Transaction Outputs)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS utxo (
                txid TEXT,
                vout INTEGER,
                value REAL,
                script_pubkey TEXT,
                PRIMARY KEY (txid, vout)
            )
        ''')
        
        # ตารางสำหรับตรวจสอบความยาก
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS difficulty (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                current_difficulty REAL,
                last_adjustment_height INTEGER
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_block(self, block: Block):
        """Save block to database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # บันทึกบล็อก
        cursor.execute('''
            INSERT INTO blocks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            block.height,
            block.header.calculate_hash(),
            block.header.previous_hash,
            block.header.version,
            block.header.merkle_root,
            block.header.timestamp,
            block.header.bits,
            block.header.nonce,
            self.bits_to_difficulty(block.header.bits),
            len(block.transactions)
        ))
        
        # บันทึกธุรกรรม
        for tx in block.transactions:
            cursor.execute('''
                INSERT INTO transactions VALUES (?, ?, ?, ?, ?)
            ''', (
                tx.txid,
                block.height,
                tx.version,
                tx.locktime,
                tx.type.value
            ))
            
            # บันทึก Inputs
            for i, txin in enumerate(tx.inputs):
                cursor.execute('''
                    INSERT INTO tx_inputs (txid, input_index, spent_txid, spent_vout, signature, pubkey)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    tx.txid,
                    i,
                    txin.txid,
                    txin.vout,
                    txin.signature,
                    txin.pubkey
                ))
                
                # ทำเครื่องหมายว่า UTXO ถูกใช้แล้ว
                if tx.type != TransactionType.COINBASE:
                    cursor.execute('''
                        UPDATE tx_outputs SET spent = 1 WHERE txid = ? AND output_index = ?
                    ''', (txin.txid, txin.vout))
                    
                    cursor.execute('''
                        DELETE FROM utxo WHERE txid = ? AND vout = ?
                    ''', (txin.txid, txin.vout))
            
            # บันทึก Outputs
            for i, txout in enumerate(tx.outputs):
                cursor.execute('''
                    INSERT INTO tx_outputs (txid, output_index, value, script_pubkey)
                    VALUES (?, ?, ?, ?)
                ''', (
                    tx.txid,
                    i,
                    txout.value,
                    txout.script_pubkey
                ))
                
                # เพิ่มใน UTXO ถ้ายังไม่ถูกใช้ (และไม่ใช่ coinbase ที่ยังไม่ครบ 100 บล็อก)
                if tx.type != TransactionType.COINBASE or block.height <= 100:
                    cursor.execute('''
                        INSERT OR REPLACE INTO utxo VALUES (?, ?, ?, ?)
                    ''', (
                        tx.txid,
                        i,
                        txout.value,
                        txout.script_pubkey
                    ))
        
        conn.commit()
        conn.close()
    
    def get_last_block(self) -> Optional[Block]:
        """Get the last block in the blockchain"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('SELECT MAX(height) FROM blocks')
        result = cursor.fetchone()
        
        if not result or result[0] is None:
            conn.close()
            return None
        
        height = result[0]
        
        cursor.execute('''
            SELECT hash, previous_hash, version, merkle_root, timestamp, bits, nonce
            FROM blocks WHERE height = ?
        ''', (height,))
        
        block_data = cursor.fetchone()
        conn.close()
        
        if not block_data:
            return None
        
        header = BlockHeader(
            version=block_data[2],
            previous_hash=block_data[1],
            merkle_root=block_data[3],
            timestamp=block_data[4],
            bits=block_data[5],
            nonce=block_data[6]
        )
        
        # ในทางปฏิบัติควรโหลดธุรกรรมด้วย แต่เพื่อความง่ายข้ามไป
        return Block(header=header, transactions=[], height=height)
    
    def get_block_count(self) -> int:
        """Get current block height"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM blocks')
        result = cursor.fetchone()
        
        conn.close()
        return result[0] if result else 0
    
    def bits_to_difficulty(self, bits: int) -> float:
        """Convert bits to difficulty"""
        # Simplified calculation
        return 0x0000ffff00000000000000000000000000000000000000000000000000000000 / bits
    
    def get_difficulty(self) -> float:
        """Get current difficulty"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('SELECT current_difficulty FROM difficulty WHERE id = 1')
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            return result[0]
        else:
            # ค่าเริ่มต้น
            return 1.0

# ================ เครือข่าย P2P ================

class P2PNetwork:
    def __init__(self, host='0.0.0.0', port=NETWORK_PORT):
        self.host = host
        self.port = port
        self.peers = set()
        self.server_socket = None
        self.running = False
        self.blockchain_db = BlockchainDB()
        
    def start(self):
        """Start P2P server"""
        self.running = True
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            logger.info(f"P2P server started on {self.host}:{self.port}")
            
            while self.running:
                client_socket, address = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket, address)).start()
                
        except Exception as e:
            logger.error(f"P2P server error: {e}")
    
    def handle_client(self, client_socket, address):
        """Handle incoming peer connection"""
        try:
            # แลกเปลี่ยนข้อมูล peer
            peer_info = self.receive_data(client_socket)
            if peer_info:
                self.peers.add((address[0], peer_info.get('port', self.port)))
                
                # ส่งรายการ peers กลับ
                self.send_data(client_socket, {
                    'type': 'peers',
                    'peers': list(self.peers)[:10]  # ส่งแค่ 10 peers
                })
                
                # ถ้าต้องการบล็อกล่าสุด
                if peer_info.get('type') == 'sync':
                    self.sync_blocks(client_socket)
                    
        except Exception as e:
            logger.error(f"Error handling client {address}: {e}")
        finally:
            client_socket.close()
    
    def connect_to_peer(self, host, port):
        """Connect to a peer"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))
            
            # ส่งข้อมูลของเรา
            self.send_data(sock, {
                'type': 'sync',
                'port': self.port,
                'height': self.blockchain_db.get_block_count()
            })
            
            # รับข้อมูล peers
            response = self.receive_data(sock)
            if response and response.get('type') == 'peers':
                for peer in response.get('peers', []):
                    self.peers.add(tuple(peer))
            
            sock.close()
            logger.info(f"Connected to peer {host}:{port}")
            
        except Exception as e:
            logger.error(f"Failed to connect to {host}:{port}: {e}")
    
    def broadcast_block(self, block: Block):
        """Broadcast new block to peers"""
        block_data = {
            'type': 'new_block',
            'block': self.serialize_block(block)
        }
        
        for peer in list(self.peers):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(peer)
                self.send_data(sock, block_data)
                sock.close()
            except:
                # ลบ peer ที่เชื่อมต่อไม่ได้
                self.peers.remove(peer)
    
    def send_data(self, sock, data):
        """Send data through socket"""
        serialized = pickle.dumps(data)
        sock.sendall(len(serialized).to_bytes(4, 'big') + serialized)
    
    def receive_data(self, sock):
        """Receive data from socket"""
        try:
            length_bytes = sock.recv(4)
            if not length_bytes:
                return None
                
            length = int.from_bytes(length_bytes, 'big')
            data = b''
            
            while len(data) < length:
                chunk = sock.recv(min(4096, length - len(data)))
                if not chunk:
                    return None
                data += chunk
            
            return pickle.loads(data)
        except:
            return None
    
    def serialize_block(self, block: Block) -> dict:
        """Serialize block for network transmission"""
        return {
            'header': {
                'version': block.header.version,
                'previous_hash': block.header.previous_hash,
                'merkle_root': block.header.merkle_root,
                'timestamp': block.header.timestamp,
                'bits': block.header.bits,
                'nonce': block.header.nonce
            },
            'transactions': [
                {
                    'txid': tx.txid,
                    'version': tx.version,
                    'inputs': [
                        {
                            'txid': inp.txid,
                            'vout': inp.vout,
                            'signature': inp.signature,
                            'pubkey': inp.pubkey
                        } for inp in tx.inputs
                    ],
                    'outputs': [
                        {
                            'value': out.value,
                            'script_pubkey': out.script_pubkey
                        } for out in tx.outputs
                    ],
                    'locktime': tx.locktime,
                    'type': tx.type.value
                } for tx in block.transactions
            ],
            'height': block.height
        }

# ================ ระบบขุดสำหรับมือถือ ================

class MobileMiner:
    def __init__(self, address: str):
        self.address = address
        self.mining = False
        self.current_block = None
        self.current_nonce = 0
        self.hash_rate = 0
        self.last_hash_time = time.time()
        self.hash_count = 0
        
    def start_mining(self, blockchain_db: BlockchainDB):
        """Start mining on mobile device"""
        self.mining = True
        logger.info(f"Starting mobile miner for address: {self.address}")
        
        while self.mining:
            # สร้างบล็อกใหม่
            last_block = blockchain_db.get_last_block()
            if not last_block:
                # Genesis block
                self.create_genesis_block()
            else:
                self.create_new_block(last_block, blockchain_db)
            
            # ขุดบล็อก
            self.mine_block()
            
            # พักสั้นๆ เพื่อประหยัดแบตเตอรี่
            time.sleep(0.1)
    
    def create_new_block(self, last_block: Block, blockchain_db: BlockchainDB):
        """Create new block for mining"""
        # สร้าง coinbase transaction
        coinbase_tx = self.create_coinbase_transaction(blockchain_db.get_block_count() + 1)
        
        # สร้าง block header
        header = BlockHeader(
            version=1,
            previous_hash=last_block.header.calculate_hash(),
            merkle_root="",  # จะคำนวณหลังจากมีธุรกรรม
            timestamp=int(time.time()),
            bits=self.calculate_bits(blockchain_db),
            nonce=0
        )
        
        self.current_block = Block(
            header=header,
            transactions=[coinbase_tx],
            height=last_block.height + 1
        )
        
        # คำนวณ merkle root
        self.current_block.header.merkle_root = self.current_block.calculate_merkle_root()
        
        logger.info(f"Created new block #{self.current_block.height}")
    
    def create_coinbase_transaction(self, height: int) -> Transaction:
        """Create coinbase transaction"""
        # คำนวณรางวัลบล็อก
        reward = self.get_block_reward(height)
        
        # สร้าง transaction output
        tx_output = TransactionOutput(
            value=reward,
            script_pubkey=self.address
        )
        
        # สร้าง transaction
        tx = Transaction(
            version=1,
            inputs=[],  # Coinbase ไม่มี input
            outputs=[tx_output],
            type=TransactionType.COINBASE
        )
        
        tx.txid = tx.calculate_hash()
        return tx
    
    def get_block_reward(self, height: int) -> float:
        """Calculate block reward based on halving"""
        halvings = height // HALVING_INTERVAL
        
        if halvings >= 64:
            return 0
        
        reward = INITIAL_BLOCK_REWARD
        for _ in range(halvings):
            reward /= 2
        
        return reward
    
    def calculate_bits(self, blockchain_db: BlockchainDB) -> int:
        """Calculate difficulty bits"""
        # วิธีคำนวณความยากแบบง่าย
        current_height = blockchain_db.get_block_count()
        
        if current_height % DIFFICULTY_ADJUSTMENT_INTERVAL == 0 and current_height > 0:
            # ปรับความยาก
            return self.adjust_difficulty(blockchain_db)
        else:
            # ใช้ความยากปัจจุบัน
            difficulty = blockchain_db.get_difficulty()
            return int(0x0000ffff00000000000000000000000000000000000000000000000000000000 / difficulty)
    
    def adjust_difficulty(self, blockchain_db: BlockchainDB) -> int:
        """Adjust difficulty based on actual block time"""
        # Simplified difficulty adjustment
        current_difficulty = blockchain_db.get_difficulty()
        
        # ตัวอย่าง: ถ้าบล็อกเร็วเกินไป ให้เพิ่มความยาก
        # ในทางปฏิบัติต้องดูเวลาเฉลี่ยของบล็อกที่ผ่านมา
        new_difficulty = current_difficulty * 1.1  # เพิ่ม 10%
        
        logger.info(f"Adjusted difficulty: {current_difficulty} -> {new_difficulty}")
        return int(0x0000ffff00000000000000000000000000000000000000000000000000000000 / new_difficulty)
    
    def mine_block(self):
        """Mine the current block (mobile optimized)"""
        if not self.current_block:
            return
        
        target = self.current_block.header.bits
        
        # Mobile-friendly mining loop
        start_time = time.time()
        
        while self.mining:
            # อัพเดต nonce
            self.current_block.header.nonce += 1
            
            # คำนวณ hash
            block_hash = self.current_block.header.calculate_hash()
            
            # อัพเดต hash rate
            self.update_hash_rate()
            
            # ตรวจสอบว่า hash ต่ำกว่า target หรือไม่
            if int(block_hash, 16) < target:
                logger.info(f"Block mined! Hash: {block_hash}, Nonce: {self.current_block.header.nonce}")
                
                # บันทึกบล็อก
                self.save_mined_block()
                
                # รีเซ็ตสำหรับบล็อกถัดไป
                self.current_block = None
                self.current_nonce = 0
                break
            
            # พักเพื่อประหยัดพลังงาน (สำคัญสำหรับมือถือ)
            if self.current_block.header.nonce % 1000 == 0:
                time.sleep(0.001)
                
            # เปลี่ยนบล็อกถ้ายาวเกินไป
            if time.time() - start_time > 300:  # 5 นาที
                logger.info("Mining timeout, creating new block")
                break
    
    def update_hash_rate(self):
        """Update and display hash rate"""
        self.hash_count += 1
        
        current_time = time.time()
        time_diff = current_time - self.last_hash_time
        
        if time_diff >= 1.0:  # อัพเดตทุกวินาที
            self.hash_rate = self.hash_count / time_diff
            self.hash_count = 0
            self.last_hash_time = current_time
            
            # แสดง hash rate (สำหรับ UI)
            if self.hash_rate > 1000000:
                logger.debug(f"Hash rate: {self.hash_rate/1000000:.2f} MH/s")
            elif self.hash_rate > 1000:
                logger.debug(f"Hash rate: {self.hash_rate/1000:.2f} KH/s")
            else:
                logger.debug(f"Hash rate: {self.hash_rate:.2f} H/s")
    
    def save_mined_block(self):
        """Save mined block to database"""
        # ในทางปฏิบัติควรเชื่อมต่อกับ blockchain database
        logger.info(f"Block #{self.current_block.height} mined successfully!")
        
        # Broadcast ไปยังเครือข่าย
        # network.broadcast_block(self.current_block)
    
    def create_genesis_block(self):
        """Create genesis block"""
        logger.info("Creating genesis block...")
        
        # Genesis transaction
        genesis_tx = Transaction(
            version=1,
            inputs=[],
            outputs=[
                TransactionOutput(
                    value=INITIAL_BLOCK_REWARD,
                    script_pubkey="Genesis"
                )
            ],
            type=TransactionType.COINBASE
        )
        genesis_tx.txid = genesis_tx.calculate_hash()
        
        # Genesis block header
        header = BlockHeader(
            version=1,
            previous_hash="0" * 64,
            merkle_root=genesis_tx.txid,
            timestamp=int(time.time()),
            bits=0x1d00ffff,  # Difficulty target เริ่มต้น
            nonce=0
        )
        
        self.current_block = Block(
            header=header,
            transactions=[genesis_tx],
            height=0
        )
        
        # Mine genesis block
        self.current_block.header.nonce = 0
        while int(self.current_block.header.calculate_hash(), 16) > self.current_block.header.bits:
            self.current_block.header.nonce += 1
        
        logger.info(f"Genesis block created: {self.current_block.header.calculate_hash()}")

# ================ ระบบกระเป๋าสตางค์ ================

class Wallet:
    def __init__(self, name="My CpyTro Wallet"):
        self.name = name
        self.private_key = None
        self.public_key = None
        self.address = None
        self.balance = 0.0
        self.transactions = []
        
        self.generate_keys()
    
    def generate_keys(self):
        """Generate RSA key pair for wallet"""
        # ตัวอย่างง่ายๆ สำหรับการสาธิต
        # ในทางปฏิบัติควรใช้ elliptic curve cryptography
        self.private_key = hashlib.sha256(os.urandom(32)).hexdigest()
        self.public_key = hashlib.sha256(self.private_key.encode()).hexdigest()
        self.address = self.public_key[:40]  # ที่อยู่สั้นๆ
        
        logger.info(f"New wallet created: {self.address}")
    
    def get_balance(self, blockchain_db: BlockchainDB) -> float:
        """Get wallet balance from UTXO"""
        conn = sqlite3.connect(blockchain_db.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT SUM(value) FROM utxo WHERE script_pubkey = ?
        ''', (self.address,))
        
        result = cursor.fetchone()
        conn.close()
        
        self.balance = result[0] if result[0] else 0.0
        return self.balance
    
    def create_transaction(self, to_address: str, amount: float, blockchain_db: BlockchainDB) -> Optional[Transaction]:
        """Create and sign a transaction"""
        # ตรวจสอบยอดเงิน
        if amount > self.balance:
            logger.error("Insufficient balance")
            return None
        
        # ค้นหา UTXO
        utxos = self.find_utxos(amount, blockchain_db)
        if not utxos:
            logger.error("No suitable UTXOs found")
            return None
        
        # สร้าง transaction inputs
        inputs = []
        total_input = 0.0
        
        for utxo in utxos:
            txin = TransactionInput(
                txid=utxo['txid'],
                vout=utxo['vout'],
                signature="",  # จะเซ็นต์หลังจากสร้าง transaction
                pubkey=self.public_key
            )
            inputs.append(txin)
            total_input += utxo['value']
        
        # สร้าง transaction outputs
        outputs = [
            TransactionOutput(
                value=amount,
                script_pubkey=to_address
            )
        ]
        
        # ส่งเงินทอน (ถ้ามี)
        change = total_input - amount
        if change > 0:
            outputs.append(
                TransactionOutput(
                    value=change,
                    script_pubkey=self.address
                )
            )
        
        # สร้าง transaction
        tx = Transaction(
            version=1,
            inputs=inputs,
            outputs=outputs,
            type=TransactionType.REGULAR
        )
        
        # เซ็นต์ transaction
        tx.txid = self.sign_transaction(tx)
        
        return tx
    
    def find_utxos(self, amount: float, blockchain_db: BlockchainDB) -> List[Dict]:
        """Find UTXOs for spending"""
        conn = sqlite3.connect(blockchain_db.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT txid, vout, value FROM utxo 
            WHERE script_pubkey = ? 
            ORDER BY value DESC
        ''', (self.address,))
        
        utxos = []
        total = 0.0
        
        for row in cursor.fetchall():
            utxo = {
                'txid': row[0],
                'vout': row[1],
                'value': row[2]
            }
            utxos.append(utxo)
            total += row[2]
            
            if total >= amount:
                break
        
        conn.close()
        
        if total >= amount:
            return utxos
        else:
            return []
    
    def sign_transaction(self, tx: Transaction) -> str:
        """Sign transaction"""
        # ในตัวอย่างนี้ใช้ hash ง่ายๆ
        # ในทางปฏิบัติควรใช้การเซ็นต์ดิจิทัลจริง
        tx_data = f"{tx.version}{[(inp.txid, inp.vout) for inp in tx.inputs]}" \
                  f"{[(out.value, out.script_pubkey) for out in tx.outputs]}{tx.locktime}"
        
        # "เซ็นต์" ด้วย private key
        signature = hashlib.sha256((tx_data + self.private_key).encode()).hexdigest()
        
        # อัพเดต signature ใน inputs
        for txin in tx.inputs:
            txin.signature = signature
        
        # คำนวณ txid
        return tx.calculate_hash()

# ================ API เซิร์ฟเวอร์ ================

class APIServer:
    def __init__(self, blockchain_db: BlockchainDB, port=8334):
        self.blockchain_db = blockchain_db
        self.port = port
        self.app = self.create_app()
    
    def create_app(self):
        """Create Flask API server"""
        try:
            from flask import Flask, jsonify, request
            app = Flask(__name__)
            
            @app.route('/api/blockchain/info', methods=['GET'])
            def get_blockchain_info():
                height = self.blockchain_db.get_block_count()
                last_block = self.blockchain_db.get_last_block()
                
                return jsonify({
                    'version': VERSION,
                    'height': height,
                    'last_block_hash': last_block.header.calculate_hash() if last_block else None,
                    'difficulty': self.blockchain_db.get_difficulty(),
                    'network': 'CpyTro Mainnet'
                })
            
            @app.route('/api/block/<int:height>', methods=['GET'])
            def get_block(height):
                conn = sqlite3.connect(self.blockchain_db.db_file)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT * FROM blocks WHERE height = ?
                ''', (height,))
                
                block_data = cursor.fetchone()
                conn.close()
                
                if block_data:
                    return jsonify({
                        'height': block_data[0],
                        'hash': block_data[1],
                        'timestamp': block_data[5],
                        'transaction_count': block_data[9]
                    })
                else:
                    return jsonify({'error': 'Block not found'}), 404
            
            @app.route('/api/wallet/<address>/balance', methods=['GET'])
            def get_wallet_balance(address):
                conn = sqlite3.connect(self.blockchain_db.db_file)
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT SUM(value) FROM utxo WHERE script_pubkey = ?
                ''', (address,))
                
                result = cursor.fetchone()
                conn.close()
                
                balance = result[0] if result[0] else 0.0
                
                return jsonify({
                    'address': address,
                    'balance': balance,
                    'unit': 'CPT'
                })
            
            @app.route('/api/transaction/broadcast', methods=['POST'])
            def broadcast_transaction():
                # ตัวอย่างการรับ transaction
                tx_data = request.json
                
                # ในทางปฏิบัติควรตรวจสอบและบันทึก transaction
                logger.info(f"Received transaction: {tx_data}")
                
                return jsonify({
                    'status': 'received',
                    'message': 'Transaction will be processed'
                })
            
            return app
            
        except ImportError:
            logger.warning("Flask not installed. API server disabled.")
            return None
    
    def start(self):
        """Start API server"""
        if self.app:
            threading.Thread(target=lambda: self.app.run(
                host='0.0.0.0', 
                port=self.port, 
                debug=False
            )).start()
            logger.info(f"API server started on port {self.port}")

# ================ อินเทอร์เฟซมือถือ ================

class MobileUI:
    """Simple mobile interface (console-based for demo)"""
    
    def __init__(self, miner: MobileMiner, wallet: Wallet, blockchain_db: BlockchainDB):
        self.miner = miner
        self.wallet = wallet
        self.blockchain_db = blockchain_db
        self.running = True
    
    def display_menu(self):
        """Display main menu"""
        print("\n" + "="*50)
        print("          CpyTro Mobile Miner")
        print("="*50)
        print(f"Address: {self.wallet.address}")
        print(f"Balance: {self.wallet.get_balance(self.blockchain_db):.8f} CPT")
        print(f"Block Height: {self.blockchain_db.get_block_count()}")
        print(f"Mining: {'Active' if self.miner.mining else 'Inactive'}")
        print(f"Hash Rate: {self.miner.hash_rate:.2f} H/s")
        print("="*50)
        print("1. Start Mining")
        print("2. Stop Mining")
        print("3. Send CPT")
        print("4. Check Balance")
        print("5. View Transactions")
        print("6. Network Info")
        print("7. Exit")
        print("="*50)
    
    def handle_choice(self, choice: str):
        """Handle user choice"""
        if choice == '1':
            self.start_mining()
        elif choice == '2':
            self.stop_mining()
        elif choice == '3':
            self.send_transaction()
        elif choice == '4':
            self.check_balance()
        elif choice == '5':
            self.view_transactions()
        elif choice == '6':
            self.network_info()
        elif choice == '7':
            self.exit_app()
        else:
            print("Invalid choice. Please try again.")
    
    def start_mining(self):
        """Start mining"""
        if not self.miner.mining:
            threading.Thread(target=self.miner.start_mining, args=(self.blockchain_db,)).start()
            print("Mining started...")
        else:
            print("Mining is already active.")
    
    def stop_mining(self):
        """Stop mining"""
        self.miner.mining = False
        print("Mining stopped.")
    
    def send_transaction(self):
        """Send CPT to another address"""
        try:
            to_address = input("Enter recipient address: ")
            amount = float(input("Enter amount: "))
            
            if amount <= 0:
                print("Amount must be positive.")
                return
            
            tx = self.wallet.create_transaction(to_address, amount, self.blockchain_db)
            
            if tx:
                print(f"Transaction created: {tx.txid}")
                print(f"Sent {amount} CPT to {to_address}")
            else:
                print("Failed to create transaction.")
                
        except ValueError:
            print("Invalid amount.")
    
    def check_balance(self):
        """Check wallet balance"""
        balance = self.wallet.get_balance(self.blockchain_db)
        print(f"Current balance: {balance:.8f} CPT")
    
    def view_transactions(self):
        """View transaction history"""
        # ตัวอย่างง่ายๆ
        print("\nRecent Transactions:")
        print("(Transaction history feature in development)")
    
    def network_info(self):
        """Display network information"""
        height = self.blockchain_db.get_block_count()
        difficulty = self.blockchain_db.get_difficulty()
        
        print(f"\nNetwork Information:")
        print(f"Block Height: {height}")
        print(f"Difficulty: {difficulty:.2f}")
        print(f"Max Supply: {MAX_SUPPLY:,} CPT")
        print(f"Block Reward: {self.miner.get_block_reward(height + 1):.8f} CPT")
    
    def exit_app(self):
        """Exit application"""
        self.miner.mining = False
        self.running = False
        print("Exiting CpyTro Mobile Miner...")
    
    def run(self):
        """Run mobile UI"""
        print("Initializing CpyTro Mobile Miner...")
        time.sleep(1)
        
        while self.running:
            self.display_menu()
            choice = input("Select option (1-7): ")
            self.handle_choice(choice)
            
            # รอเล็กน้อยเพื่อให้ UI อัพเดต
            time.sleep(0.5)

# ================ ฟังก์ชันหลัก ================

def main():
    """Main function"""
    print("\n" + "="*60)
    print("           CpyTro (CPT) Mobile Cryptocurrency")
    print("="*60)
    print(f"Version: {VERSION}")
    print(f"Max Supply: {MAX_SUPPLY:,} CPT")
    print(f"Mobile Mining Enabled: YES")
    print("="*60)
    
    # เริ่มต้นฐานข้อมูล
    db = BlockchainDB()
    
    # สร้างกระเป๋า
    wallet = Wallet()
    
    # สร้าง miner
    miner = MobileMiner(wallet.address)
    
    # เริ่มเครือข่าย P2P (ใน thread แยก)
    network = P2PNetwork()
    network_thread = threading.Thread(target=network.start)
    network_thread.daemon = True
    network_thread.start()
    
    # เริ่ม API server
    api = APIServer(db)
    api.start()
    
    # เชื่อมต่อกับ peers เริ่มต้น
    time.sleep(2)  # รอให้ network server เริ่ม
    network.connect_to_peer('127.0.0.1', NETWORK_PORT)
    
    # เริ่ม mobile UI
    ui = MobileUI(miner, wallet, db)
    
    # ถ้ามี genesis block หรือไม่
    if db.get_block_count() == 0:
        print("\nCreating genesis block...")
        miner.create_genesis_block()
        db.save_block(miner.current_block)
        print("Genesis block created successfully!")
    
    # แสดงข้อมูลเริ่มต้น
    print(f"\nYour wallet address: {wallet.address}")
    print(f"Initial balance: {wallet.get_balance(db):.8f} CPT")
    print(f"Current block height: {db.get_block_count()}")
    
    # รัน UI
    ui.run()

if __name__ == "__main__":
    main()
