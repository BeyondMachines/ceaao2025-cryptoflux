#!/usr/bin/env python3
"""
Database Population Tool for Crypto Trading Application
Populates the database with sample cryptocurrency transactions for testing
"""
import sys
import random
import time
from datetime import datetime, timedelta
from decimal import Decimal
from app import create_app
from models import Transaction

# Sample cryptocurrencies with realistic data
CRYPTOCURRENCIES = [
    {"name": "Bitcoin", "symbol": "BTC-USD", "price_range": (20000, 70000)},
    {"name": "Ethereum", "symbol": "ETH-USD", "price_range": (1200, 5000)},
    {"name": "Solana", "symbol": "SOL-USD", "price_range": (20, 300)},
    {"name": "Cardano", "symbol": "ADA-USD", "price_range": (0.3, 3.0)},
    {"name": "Polygon", "symbol": "MATIC-USD", "price_range": (0.5, 2.8)},
    {"name": "Chainlink", "symbol": "LINK-USD", "price_range": (5, 50)},
    {"name": "Polkadot", "symbol": "DOT-USD", "price_range": (4, 55)},
    {"name": "Avalanche", "symbol": "AVAX-USD", "price_range": (10, 150)},
    {"name": "Litecoin", "symbol": "LTC-USD", "price_range": (50, 400)},
    {"name": "Uniswap", "symbol": "UNI-USD", "price_range": (3, 30)},
]

TRANSACTION_SIDES = ["buy", "sell"]


def check_existing_data_new(db):
    """
    Check if database already contains transaction data
    Returns True if data exists, False if empty
    """
    transaction_count = db.session.query(Transaction).count()
    print('new check for transactions')
    print(transaction_count)
    if transaction_count > 0:
        print(f"Current database status:")
        print(f"  Transactions: {transaction_count}")
        return True
    else:
        return False
    

def check_existing_data():
    """
    Check if database already contains transaction data
    Returns True if data exists, False if empty
    """
    transaction_count = db.session.query(Transaction).count()
    
    print(f"Current database status:")
    print(f"  Transactions: {transaction_count}")
    
    return transaction_count > 0


def generate_realistic_quantity(price, side):
    """
    Generate realistic trading quantities based on price and side
    Higher value coins tend to have smaller quantities
    """
    # Base quantity ranges by price level
    if price > 10000:  # Bitcoin range
        base_range = (0.001, 2.5)
    elif price > 1000:  # Ethereum range  
        base_range = (0.01, 15.0)
    elif price > 100:   # Mid-range coins
        base_range = (0.1, 100.0)
    elif price > 10:    # Lower price coins
        base_range = (1.0, 500.0)
    else:               # Very low price coins
        base_range = (10.0, 10000.0)
    
    # Adjust for buy vs sell (sells might be slightly smaller)
    if side == "sell":
        multiplier = random.uniform(0.7, 1.0)
    else:
        multiplier = random.uniform(0.8, 1.2)
    
    min_qty, max_qty = base_range
    quantity = random.uniform(min_qty * multiplier, max_qty * multiplier)
    
    return round(quantity, 8)


def generate_unix_timestamp(days_back=30):
    """
    Generate a realistic unix timestamp within the last N days
    """
    now = datetime.now()
    start_date = now - timedelta(days=days_back)
    
    # Random time between start_date and now
    random_date = start_date + timedelta(
        seconds=random.randint(0, int((now - start_date).total_seconds()))
    )
    
    return int(random_date.timestamp())


def create_transactions(count=100):
    """
    Create sample cryptocurrency transactions
    Returns list of created transactions
    """
    print(f"Creating {count} sample transactions...")
    
    transactions = []
    
    for i in range(count):
        # Select random cryptocurrency
        crypto = random.choice(CRYPTOCURRENCIES)
        
        # Generate realistic price within range (with some volatility)
        price_min, price_max = crypto["price_range"]
        base_price = random.uniform(price_min, price_max)
        
        # Add some price volatility (+/- 10%)
        volatility = random.uniform(-0.1, 0.1)
        price = base_price * (1 + volatility)
        price = round(price, 8)
        
        # Choose transaction side
        side = random.choice(TRANSACTION_SIDES)
        
        # Generate realistic quantity
        quantity = generate_realistic_quantity(price, side)
        
        # Generate timestamp (spread over last 30 days)
        unix_time = generate_unix_timestamp(30)
        
        # Create transaction
        transaction = Transaction(
            name=crypto["name"],
            price=Decimal(str(price)),
            quantity=Decimal(str(quantity)),
            side=side,
            symbol=crypto["symbol"],
            unix_time=unix_time
        )
        
        transactions.append(transaction)
        
        if (i + 1) % 20 == 0:
            print(f"  Generated {i + 1}/{count} transactions...")
    
    return transactions


def populate_database():
    """
    Main function to populate the database with sample data
    """
    print("=" * 60)
    print("Crypto Trading Application - Database Population Tool")
    print("=" * 60)
    
    # Check if data already exists
    if check_existing_data():
        print("\nWarning: Database already contains data!")
        return None
    else:
        print("\nDatabase is empty. Populating with sample data...")
    
    try:
        # Create transactions
        transaction_count = random.randint(80, 150)
        print(f"\n1. Creating {transaction_count} sample transactions...")
        
        transactions = create_transactions(transaction_count)
        
        # Add transactions to database in batches
        print("2. Adding transactions to database...")
        batch_size = 50
        total_added = 0
        
        for i in range(0, len(transactions), batch_size):
            batch = transactions[i:i + batch_size]
            db.session.add_all(batch)
            db.session.commit()
            total_added += len(batch)
            print(f"   Committed batch {i//batch_size + 1}: {total_added}/{len(transactions)} transactions")
        
        print(f"\n Database population completed successfully!")
        print(f" Summary:")
        print(f"   Total transactions created: {len(transactions)}")
        
        # Show distribution by cryptocurrency
        crypto_counts = {}
        side_counts = {"buy": 0, "sell": 0}
        
        for tx in transactions:
            crypto_counts[tx.name] = crypto_counts.get(tx.name, 0) + 1
            side_counts[tx.side] += 1
        
        print(f"\n Transaction Distribution:")
        for crypto, count in sorted(crypto_counts.items()):
            print(f"   {crypto}: {count} transactions")
        
        print(f"\n Buy/Sell Distribution:")
        print(f"   Buy orders: {side_counts['buy']}")
        print(f"   Sell orders: {side_counts['sell']}")
        
        # Calculate total volume
        total_volume = sum(float(tx.price * tx.quantity) for tx in transactions)
        print(f"\n💵 Total trading volume: ${total_volume:,.2f}")
        
        return {
            'transactions_created': len(transactions),
            'total_volume': total_volume
        }
        
    except Exception as e:
        print(f"\n Error during database population: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        db.session.rollback()
        return None


def main():
    """
    Main entry point for the population script
    """
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # Import the models after app context is created
        from models import Transaction
        
        # Get the SQLAlchemy instance
        from flask import current_app
        db = current_app.extensions['sqlalchemy']
        
        # Make models and db available globally for other functions
        globals()['db'] = db
        globals()['Transaction'] = Transaction
        
        # Check if data already exists
        print('now checking for data')
        if check_existing_data_new(db):
            print("\nWarning: Database already contains data!")
            return
        else:
            print('the check for data failed, populating')
            result = populate_database()
        
        if result:
            print("\n" + "=" * 60)
            print(" Ready to test!")
            print("   Run: python app.py")
            print("   Then visit: http://localhost:5000")
            print("=" * 60)


if __name__ == '__main__':
    main()