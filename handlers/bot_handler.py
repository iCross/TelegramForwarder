from telethon import events
from handlers.button.callback.callback_handlers import handle_callback
from handlers.command_handlers import *
from handlers.link_handlers import handle_message_link
from telethon.tl.types import ChannelParticipantsAdmins
from dotenv import load_dotenv
from utils.common import *
from utils.media import *
from datetime import datetime, timedelta
from version import WELCOME_TEXT

logger = logging.getLogger(__name__)

# 确保 temp 目录存在
os.makedirs(TEMP_DIR, exist_ok=True)

load_dotenv()

# 添加缓存字典
_admin_cache = {}
_CACHE_DURATION = timedelta(minutes=30)  # 缓存30分钟

async def get_channel_admins(client, chat_id):
    """获取频道管理员列表，带缓存机制"""
    current_time = datetime.now()
    
    # 检查缓存是否存在且未过期
    if chat_id in _admin_cache:
        cache_data = _admin_cache[chat_id]
        if current_time - cache_data['timestamp'] < _CACHE_DURATION:
            return cache_data['admin_ids']
    
    # 缓存不存在或已过期，重新获取管理员列表
    try:
        admins = await client.get_participants(chat_id, filter=ChannelParticipantsAdmins)
        admin_ids = [admin.id for admin in admins]
        
        # 更新缓存
        _admin_cache[chat_id] = {
            'admin_ids': admin_ids,
            'timestamp': current_time
        }
        return admin_ids
    except Exception as e:
        logger.error(f'获取频道管理员列表失败: {str(e)}')
        return None

async def handle_command(client, event):
    """处理机器人命令"""
    message = event.message
    
    if message.is_channel and not message.is_group:
        # 获取频道管理员列表（使用缓存）
        channel_admins = await get_channel_admins(client, event.chat_id)
        if channel_admins is None:
            return
            
        # 获取所有机器人管理员列表
        bot_admins = get_admin_list()
        
        # 检查机器人管理员是否在频道管理员列表中
        admin_in_channel = any(admin_id in channel_admins for admin_id in bot_admins)
        if not admin_in_channel:
            logger.info(f'机器人管理员不在频道管理员列表中，已忽略')
            return
    else:
        # 检查发送者ID
        user_id = event.sender_id  # 使用 sender_id 作为主要ID来源
        logger.info(f'发送者ID：{user_id}')
        
        bot_admins = get_admin_list()
        # 检查是否是机器人管理员
        if user_id not in bot_admins:
            logger.info(f'非管理员的消息，已忽略')
            return
    
    # 处理命令逻辑
    message = event.message
    if not message.text:
        return
    
    chat = await event.get_chat()
    user_id = await get_user_id()
    chat_id = abs(chat.id)
    user_id = int(user_id)
    

    # 链接转发功能
    if not message.text.startswith('/') and chat_id == user_id:
        # 检查是否是 Telegram 消息链接且是用户自己的消息
        logger.info(f'进入链接转发功能：{message.text}')
        if 't.me/' in message.text:
            await handle_message_link(client, event)
        return
    if not message.text.startswith('/'):
        return
    
    logger.info(f'收到管理员命令: {event.message.text}')
    # 分割命令，处理可能带有机器人用户名的情况
    parts = message.text.split()
    command = parts[0].split('@')[0][1:]  # 移除开头的 '/' 并处理可能的 @username

    # 命令处理器字典
    command_handlers = {
        'bind': lambda: handle_bind_command(event, client, parts),
        'b': lambda: handle_bind_command(event, client, parts),
        'settings': lambda: handle_settings_command(event, command, parts),
        's': lambda: handle_settings_command(event, command, parts),
        'switch': lambda: handle_switch_command(event),
        'sw': lambda: handle_switch_command(event),
        'add': lambda: handle_add_command(event, command, parts),
        'a': lambda: handle_add_command(event, command, parts),
        'add_regex': lambda: handle_add_command(event, command, parts),
        'ar': lambda: handle_add_command(event, 'add_regex', parts),
        'replace': lambda: handle_replace_command(event, parts),
        'r': lambda: handle_replace_command(event, parts),
        'list_keyword': lambda: handle_list_keyword_command(event),
        'lk': lambda: handle_list_keyword_command(event),
        'list_replace': lambda: handle_list_replace_command(event),
        'lrp': lambda: handle_list_replace_command(event),
        'remove_keyword': lambda: handle_remove_command(event, command, parts),
        'rk': lambda: handle_remove_command(event, 'remove_keyword', parts),
        'remove_keyword_by_id': lambda: handle_remove_command(event, command, parts),
        'rkbi': lambda: handle_remove_command(event, 'remove_keyword_by_id', parts),
        'remove_replace': lambda: handle_remove_command(event, command, parts),
        'rr': lambda: handle_remove_command(event, 'remove_replace', parts),
        'remove_all_keyword': lambda: handle_remove_all_keyword_command(event, command, parts),
        'rak': lambda: handle_remove_all_keyword_command(event, 'remove_all_keyword', parts),
        'clear_all': lambda: handle_clear_all_command(event),
        'ca': lambda: handle_clear_all_command(event),
        'start': lambda: handle_start_command(event),
        'help': lambda: handle_help_command(event,'help'),
        'h': lambda: handle_help_command(event,'help'),
        'export_keyword': lambda: handle_export_keyword_command(event, command),
        'ek': lambda: handle_export_keyword_command(event, command),
        'export_replace': lambda: handle_export_replace_command(event, client),
        'er': lambda: handle_export_replace_command(event, client),
        'add_all': lambda: handle_add_all_command(event, command, parts),
        'aa': lambda: handle_add_all_command(event, 'add_all', parts),
        'add_regex_all': lambda: handle_add_all_command(event, command, parts),
        'ara': lambda: handle_add_all_command(event, 'add_regex_all', parts),
        'replace_all': lambda: handle_replace_all_command(event, parts),
        'ra': lambda: handle_replace_all_command(event, parts),
        'import_keyword': lambda: handle_import_command(event, command),
        'ik': lambda: handle_import_command(event, 'import_keyword'),
        'import_regex_keyword': lambda: handle_import_command(event, command),
        'irk': lambda: handle_import_command(event, 'import_regex_keyword'),
        'import_replace': lambda: handle_import_command(event, command),
        'ir': lambda: handle_import_command(event, 'import_replace'),
        'ufb_bind': lambda: handle_ufb_bind_command(event, command),
        'ub': lambda: handle_ufb_bind_command(event, 'ufb_bind'),
        'ufb_unbind': lambda: handle_ufb_unbind_command(event, command),
        'uu': lambda: handle_ufb_unbind_command(event, 'ufb_unbind'),
        'ufb_item_change': lambda: handle_ufb_item_change_command(event, command),
        'uic': lambda: handle_ufb_item_change_command(event, 'ufb_item_change'),
        'clear_all_keywords': lambda: handle_clear_all_keywords_command(event, command),
        'cak': lambda: handle_clear_all_keywords_command(event, 'clear_all_keywords'),
        'clear_all_keywords_regex': lambda: handle_clear_all_keywords_regex_command(event, command),
        'cakr': lambda: handle_clear_all_keywords_regex_command(event, 'clear_all_keywords_regex'),
        'clear_all_replace': lambda: handle_clear_all_replace_command(event, command),
        'car': lambda: handle_clear_all_replace_command(event, 'clear_all_replace'),
        'copy_keywords': lambda: handle_copy_keywords_command(event, command),
        'ck': lambda: handle_copy_keywords_command(event, 'copy_keywords'),
        'copy_keywords_regex': lambda: handle_copy_keywords_regex_command(event, command),
        'ckr': lambda: handle_copy_keywords_regex_command(event, 'copy_keywords_regex'),
        'copy_replace': lambda: handle_copy_replace_command(event, command),
        'crp': lambda: handle_copy_replace_command(event, 'copy_replace'),
        'copy_rule': lambda: handle_copy_rule_command(event, command),
        'cr': lambda: handle_copy_rule_command(event, 'copy_rule'),
        'changelog': lambda: handle_changelog_command(event),
        'cl': lambda: handle_changelog_command(event),
        'list_rule': lambda: handle_list_rule_command(event, command, parts),
        'lr': lambda: handle_list_rule_command(event, command, parts),
        'delete_rule': lambda: handle_delete_rule_command(event, command, parts),
        'dr': lambda: handle_delete_rule_command(event, command, parts),
        'delete_rss_user': lambda: handle_delete_rss_user_command(event, command, parts),
        'dru': lambda: handle_delete_rss_user_command(event, command, parts),
    }

    # 执行对应的命令处理器
    handler = command_handlers.get(command)
    if handler:
        await handler()



# 注册回调处理器
@events.register(events.CallbackQuery)
async def callback_handler(event):
    """回调处理器入口"""
    # 检查是否是管理员的回调
    admin_list = get_admin_list()
    if event.sender_id not in admin_list:
        return
    await handle_callback(event)


async def send_welcome_message(client):
    """发送欢迎消息"""
    main = await get_main_module()
    user_id = await get_user_id()

    # 发送新消息
    await client.send_message(
        user_id,
        WELCOME_TEXT,
        parse_mode='html',
        link_preview=True
    )
    logger.info("已发送欢迎消息")



