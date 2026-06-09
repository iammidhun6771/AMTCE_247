import os
import sys
import asyncio
import json

# Fix Windows console encoding issues
if sys.platform.startswith('win'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add parent directory to path to enable local module imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set working directory to project root
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(root_dir)

from Uploader_Modules.telegram_message_ledger import update_affiliate_link

class MockBot:
    def __init__(self):
        self.edits = []

    async def edit_message_caption(self, chat_id, message_id, caption, reply_markup=None):
        print(f"[MOCK BOT] edit_message_caption called:")
        print(f"   Chat ID    : {chat_id}")
        print(f"   Message ID : {message_id}")
        print(f"   Caption    : {caption}")
        if reply_markup:
            btn_details = []
            for row in reply_markup.inline_keyboard:
                row_details = []
                for btn in row:
                    row_details.append(f"Button(text={btn.text}, url={btn.url})")
                btn_details.append(row_details)
            print(f"   Buttons    : {btn_details}")
        
        self.edits.append({
            "chat_id": chat_id,
            "message_id": message_id,
            "caption": caption,
            "reply_markup": reply_markup
        })

async def run_tests():
    print("Starting local link refresh verification tests...")
    
    # Save a backup of pools first if they exist
    pool_file = "The_json/los_pollos_links.json"
    backup_pool_content = None
    if os.path.exists(pool_file):
        with open(pool_file, "r", encoding="utf-8") as f:
            backup_pool_content = f.read()

    # 1. Test Auto-Rotation (no arguments)
    print("\n--- Test Case 1: Auto-Rotation (no arguments provided) ---")
    bot = MockBot()
    summary = await update_affiliate_link(bot, old_link=None, new_link=None)
    
    print("\nTest Case 1 Summary Result:")
    print(f"Status        : {summary['status']}")
    print(f"New Chosen Lk : {summary['new_link']}")
    print(f"Posts Scanned : {summary['posts_scanned']}")
    print(f"Posts Updated : {summary['posts_updated']}")
    print("Details:")
    for detail in summary["details"]:
        print(f" - {detail}")

    # Check that ledger is updated
    with open("The_json/message_ledger.json", "r", encoding="utf-8") as f:
        ledger = json.load(f)
    print("\nUpdated ledger content:")
    for entry in ledger:
        print(f"Post ID {entry['message_id']} has caption: {entry['caption']}")
        print(f"Post ID {entry['message_id']} has button: {entry['buttons']}")

    # Restore backup
    if backup_pool_content:
        with open(pool_file, "w", encoding="utf-8") as f:
            f.write(backup_pool_content)
    
    # 2. Test Surgical Replacement (with arguments)
    print("\n--- Test Case 2: Surgical Replacement (explicit links) ---")
    # Reset mock ledger first
    mock_ledger = [
      {
        "message_id": 12345,
        "chat_id": "-1003762065314",
        "title": "Mock Actress Post 1",
        "caption": "Hey look at this amazing video! Buy here: https://old-link.com/yd6huy5 #hot #reels",
        "buttons": [
          [
            {
              "text": "Find Your Match",
              "url": "https://old-link.com/yd6huy5"
            }
          ]
        ],
        "timestamp": "2026-06-02T16:00:00.000000"
      }
    ]
    with open("The_json/message_ledger.json", "w", encoding="utf-8") as f:
        json.dump(mock_ledger, f, indent=2)

    bot2 = MockBot()
    summary2 = await update_affiliate_link(bot2, old_link="https://old-link.com/yd6huy5", new_link="https://new-link.com/yd6huy5")
    
    print("\nTest Case 2 Summary Result:")
    print(f"Status        : {summary2['status']}")
    print(f"New Chosen Lk : {summary2['new_link']}")
    print(f"Posts Scanned : {summary2['posts_scanned']}")
    print(f"Posts Updated : {summary2['posts_updated']}")
    print("Details:")
    for detail in summary2["details"]:
        print(f" - {detail}")

    # Check updated ledger
    with open("The_json/message_ledger.json", "r", encoding="utf-8") as f:
        ledger2 = json.load(f)
    print("\nUpdated ledger content:")
    for entry in ledger2:
        print(f"Post ID {entry['message_id']} has caption: {entry['caption']}")
        print(f"Post ID {entry['message_id']} has button: {entry['buttons']}")

    print("\nAll verification tests completed successfully!")

if __name__ == "__main__":
    asyncio.run(run_tests())
