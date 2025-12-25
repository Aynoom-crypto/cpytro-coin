# main.py
import os
import sys
import time

print("\n" + "="*60)
print("        🪙 CPYTRO COIN - Mobile Mining System")
print("="*60)
time.sleep(1)

# Import modules
try:
    from blockchain import CPYTROBlockchain
    from mobile_wallet import MobileWallet
    from mobile_miner import MobileMiner
    print("✓ Modules loaded successfully")
except ImportError as e:
    print(f"❌ Error loading modules: {e}")
    print("Make sure all files are in the same directory:")
    print("  - blockchain.py")
    print("  - mobile_wallet.py")
    print("  - mobile_miner.py")
    sys.exit(1)

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_banner():
    clear_screen()
    print("\n" + "="*60)
    print("        🚀 WELCOME TO CPYTRO COIN")
    print("="*60)
    print("Features:")
    print("✓ Mine on Mobile Phone")
    print("✓ Total Supply: 210,000,000 CPYTRO")
    print("✓ SHA512 Algorithm")
    print("✓ Easy to Use")
    print("="*60)

def main_menu():
    wallet = MobileWallet()
    miner = None
    
    while True:
        show_banner()
        
        # Show wallet info if exists
        if wallet.wallets:
            print(f"\n👛 Active Wallet: {wallet.wallets[0]['nickname']}")
            print(f"   Balance: {wallet.wallets[0]['balance']:.2f} CPYTRO")
        else:
            print("\n👛 No wallet created yet")
        
        print("\n" + "="*60)
        print("MAIN MENU:")
        print("[1] 📝 Create New Wallet")
        print("[2] 📋 List All Wallets")
        print("[3] ⛏️  Start Mining")
        print("[4] 📊 View Mining Stats")
        print("[5] 🔗 View Blockchain Info")
        print("[6] 🚪 Exit")
        print("="*60)
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == "1":
            create_wallet_menu(wallet)
        elif choice == "2":
            list_wallets_menu(wallet)
        elif choice == "3":
            start_mining_menu(wallet, miner)
        elif choice == "4":
            view_stats_menu(miner)
        elif choice == "5":
            view_blockchain_menu()
        elif choice == "6":
            print("\nThank you for using CPYTRO Coin! 👋")
            if miner and miner.mining:
                miner.stop_mining()
            sys.exit(0)
        else:
            print("\n❌ Invalid choice! Please select 1-6")
            time.sleep(1)

def create_wallet_menu(wallet):
    clear_screen()
    print("\n" + "="*60)
    print("        📝 CREATE NEW WALLET")
    print("="*60)
    
    nickname = input("\nEnter wallet nickname (or press Enter for default): ").strip()
    
    address = wallet.create_new_wallet(nickname)
    
    print(f"\n✅ Wallet created successfully!")
    print(f"Your address has been saved to: {wallet.wallet_file}")
    
    input("\nPress Enter to continue...")

def list_wallets_menu(wallet):
    clear_screen()
    wallet.list_wallets()
    input("\nPress Enter to continue...")

def start_mining_menu(wallet, miner):
    clear_screen()
    print("\n" + "="*60)
    print("        ⛏️  START MINING")
    print("="*60)
    
    if not wallet.wallets:
        print("\n❌ You need to create a wallet first!")
        input("\nPress Enter to continue...")
        return
    
    # Show available wallets
    print("\nAvailable wallets:")
    for i, w in enumerate(wallet.wallets, 1):
        print(f"{i}. {w['nickname']} - {w['address'][:20]}...")
    
    try:
        choice = int(input("\nSelect wallet to mine for (number): ")) - 1
        if 0 <= choice < len(wallet.wallets):
            selected_wallet = wallet.wallets[choice]
            
            print(f"\n🎯 Selected: {selected_wallet['nickname']}")
            print(f"📍 Address: {selected_wallet['address'][:20]}...")
            
            # Create miner
            miner = MobileMiner(selected_wallet['address'])
            
            print("\n⏳ Starting mining process...")
            print("Note: Press Ctrl+C to stop mining")
            
            # Start mining in background
            import threading
            thread = miner.start_mining(background=True)
            
            print("\n✅ Mining started successfully!")
            print("Mining in background...")
            print("Use option 4 to view stats")
            
            input("\nPress Enter to return to menu...")
            
            return miner
            
        else:
            print("\n❌ Invalid selection!")
    except ValueError:
        print("\n❌ Please enter a valid number!")
    
    input("\nPress Enter to continue...")
    return miner

def view_stats_menu(miner):
    clear_screen()
    print("\n" + "="*60)
    print("        📊 MINING STATISTICS")
    print("="*60)
    
    if not miner:
        print("\n❌ No active miner found!")
        print("Start mining first using option 3")
    else:
        stats = miner.get_stats()
        
        print(f"\n⛏️  Mining Status: {'ACTIVE ✅' if stats['mining'] else 'INACTIVE ❌'}")
        print(f"📛 Wallet: {stats['wallet']}")
        print(f"⚡ Hash Rate: {stats['hash_rate']:.2f} H/s")
        print(f"📦 Blocks Mined: {stats['blocks_mined']}")
        print(f"💰 Coins Earned: {stats['coins_mined']:.2f} CPYTRO")
        print(f"📋 Pending Transactions: {stats['pending_tx']}")
        
        # Show blockchain info
        blockchain = CPYTROBlockchain()
        print(f"\n🔗 Total Blocks: {len(blockchain.chain)}")
        print(f"🎯 Difficulty: {blockchain.difficulty}")
        print(f"💎 Total Supply Mined: {blockchain.mined_coins:,}/{blockchain.total_supply:,}")
    
    input("\nPress Enter to continue...")

def view_blockchain_menu():
    clear_screen()
    print("\n" + "="*60)
    print("        🔗 BLOCKCHAIN INFORMATION")
    print("="*60)
    
    blockchain = CPYTROBlockchain()
    
    print(f"\n📊 Blockchain Stats:")
    print(f"   Total Blocks: {len(blockchain.chain)}")
    print(f"   Current Difficulty: {blockchain.difficulty}")
    print(f"   Mining Reward: {blockchain.mining_reward} CPYTRO")
    print(f"   Total Supply: {blockchain.total_supply:,} CPYTRO")
    print(f"   Mined So Far: {blockchain.mined_coins:,} CPYTRO")
    
    if blockchain.chain:
        print(f"\n📦 Recent Blocks:")
        for i, block in enumerate(blockchain.chain[-3:]):
            print(f"\n   Block #{block.index}:")
            print(f"      Hash: {block.hash[:20]}...")
            print(f"      Transactions: {len(block.transactions)}")
            print(f"      Nonce: {block.nonce:,}")
            print(f"      Time: {time.ctime(block.timestamp)}")
    
    input("\nPress Enter to continue...")

def first_time_setup():
    """First time setup guide"""
    clear_screen()
    print("\n" + "="*60)
    print("        🎉 FIRST TIME SETUP")
    print("="*60)
    
    print("\nWelcome to CPYTRO Coin! Follow these steps:")
    print("\n1. 📝 Create a wallet (Option 1)")
    print("2. ⛏️  Start mining (Option 3)")
    print("3. 💰 Check your balance (Option 4)")
    print("4. 🔗 View blockchain (Option 5)")
    
    print("\n" + "="*60)
    print("Quick Tips:")
    print("- Mining takes 30-60 seconds per block")
    print("- You earn 50 CPYTRO per block")
    print("- Save your wallet address!")
    print("="*60)
    
    input("\nPress Enter to start...")

if __name__ == "__main__":
    try:
        # Check if first time
        wallet = MobileWallet()
        if not wallet.wallets:
            first_time_setup()
        
        main_menu()
        
    except KeyboardInterrupt:
        print("\n\n👋 Exiting CPYTRO Coin...")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        input("Press Enter to exit...")
