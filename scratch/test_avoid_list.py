import sys
import os

# Adjust path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Actress_Modules.actress_ledger import get_ledger

def test_avoid_list():
    ledger = get_ledger()
    print(f"Ledger loaded successfully.")
    print(f"Shortcodes: {len(ledger._shortcodes)}")
    print(f"Hashes: {len(ledger._hashes)}")
    
    # Test with a known shortcode if any exists
    if ledger._shortcodes:
        sc = list(ledger._shortcodes)[0]
        print(f"Testing seen shortcode '{sc}': expected True, got {ledger.is_in_avoid_list(sc)}")
    
    # Test with unseen shortcode
    print(f"Testing unseen shortcode 'UNSEEN123': expected False, got {ledger.is_in_avoid_list('UNSEEN123')}")
    
    # Test with seen hash
    if ledger._hashes:
        h = list(ledger._hashes.keys())[0]
        print(f"Testing seen hash '{h}': expected true in ledger._hashes: {h in ledger._hashes}")

if __name__ == "__main__":
    test_avoid_list()
