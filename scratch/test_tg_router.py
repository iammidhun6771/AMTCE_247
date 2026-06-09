import os, sys
sys.path.insert(0, '.')

os.environ['TELEGRAM_GROUP_ID'] = '@general_group'
os.environ['TELEGRAM_GROUP_ID_FASHION'] = '@fashion_group'
os.environ['TELEGRAM_GROUP_ID_FASHION_01'] = '@fashion_group_2'
os.environ['TELEGRAM_GROUP_ID_NSFW'] = '@nsfw_group'
os.environ['TELEGRAM_GROUP_ID_NSFW_01'] = '@nsfw_group_2'

from Uploader_Modules.telegram_router import get_telegram_group_id, get_router_status

print('fashion ->', get_telegram_group_id('fashion'))
print('fashion ->', get_telegram_group_id('fashion'))
print('fashion ->', get_telegram_group_id('fashion'))
print('nsfw    ->', get_telegram_group_id('nsfw'))
print('nsfw    ->', get_telegram_group_id('nsfw'))
print('general ->', get_telegram_group_id('general'))
print()

status = get_router_status()
for cat, info in status.items():
    print(cat, info['groups'], 'next_idx=', info['next_index'])
