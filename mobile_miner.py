# mobile_miner.py
import time
import threading
from blockchain import Transaction, Block, CPYTROBlockchain

print("Loading Mobile Miner...")

class MobileMiner:
    def __init__(self, wallet_address):
        self.blockchain = CPYTROBlockchain()
        self.wallet_address = wallet_address
        self.mining = False
        self.current_hash_rate = 0
    
    def start_mining(self, background=True):
        if self.mining:
            print("Already mining!")
            return
        
        self.mining = True
        print(f"🚀 Starting CPYTRO miner for: {self.wallet_address[:15]}...")
        print(f"💰 Reward: {self.blockchain.mining_reward} CPYTRO per block")
        print(f"⚙️  Difficulty: {self.blockchain.difficulty}")
        
        if background:
            mining_thread = threading.Thread(target=self._mining_loop, daemon=True)
            mining_thread.start()
            return mining_thread
        else:
            self._mining_loop()
    
    def _mining_loop(self):
        hashes_tried = 0
        start_time = time.time()
        
        while self.mining:
            # Create a test transaction
            test_tx = Transaction(
                self.wallet_address,
                "test_receiver",
                0.1,
                0.001
            )
            
            self.blockchain.pending_transactions.append(test_tx)
            
            # Get latest block
            latest_block = self.blockchain.chain[-1]
            
            # Create new block
            new_block = Block(
                len(self.blockchain.chain),
                self.blockchain.pending_transactions.copy(),
                latest_block.hash,
                self.blockchain.difficulty
            )
            
            # Mine the block
            target = "0" * self.blockchain.difficulty
            if new_block.mine_block(target):
                self.blockchain.chain.append(new_block)
                self.blockchain.pending_transactions = []
                self.blockchain.mined_coins += self.blockchain.mining_reward
                
                print(f"\n✅ New block #{new_block.index} added to chain!")
                print(f"💰 Received {self.blockchain.mining_reward} CPYTRO")
                print(f"📊 Total mined: {self.blockchain.mined_coins:,}/{self.blockchain.total_supply:,}")
            
            # Update hash rate
            hashes_tried += new_block.nonce
            elapsed = time.time() - start_time
            if elapsed > 0:
                self.current_hash_rate = hashes_tried / elapsed
            
            # Brief pause
            time.sleep(1)
    
    def stop_mining(self):
        self.mining = False
        print("\n⏹️ Mining stopped")
    
    def get_stats(self):
        return {
            'mining': self.mining,
            'hash_rate': self.current_hash_rate,
            'wallet': self.wallet_address[:15] + "...",
            'blocks_mined': len(self.blockchain.chain) - 1,  # minus genesis
            'coins_mined': self.blockchain.mined_coins,
            'pending_tx': len(self.blockchain.pending_transactions)
        }
