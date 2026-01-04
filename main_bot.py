#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Bot Telegram để quản lý các công cụ tự động hóa Golike
Hỗ trợ: Instagram, LinkedIn, và Threads
"""

import logging
import json
import os
import threading
import asyncio
import time
from datetime import datetime
from typing import Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler
)

# Import Golike runners
from golike_runners import GolikeThreadsRunner

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States cho conversation
WAITING_TOKEN = 1
WAITING_COOKIE = 2
WAITING_DELAY_MIN = 3
WAITING_DELAY_MAX = 4
WAITING_JOB_LIMIT = 5

# Instagram setup states
WAITING_ACCOUNT_CHOICE = 10
WAITING_IG_COOKIE = 11
WAITING_IG_DELAY_MIN = 12
WAITING_IG_DELAY_MAX = 13
WAITING_IG_JOBS = 14

# Lưu trữ tiến trình đang chạy
running_tasks: Dict[int, Dict] = {}

class GolikeBot:
    def __init__(self):
        self.config_file = 'bot_config.json'
        # Default user ID (bạn nên set biến này trên Render là ID Telegram của bạn)
        self.admin_id = os.environ.get('ADMIN_ID', '7509896689') 
        self.load_config()
    
    def load_config(self):
        """Tải cấu hình từ file và Environment Variables"""
        # 1. Load từ file
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = {
                'bot_token': os.environ.get('BOT_TOKEN', ''),
                'users': {}
            }
            
        # 2. Check biến môi trường cho Bot Token nếu file không có
        if not self.config.get('bot_token') and os.environ.get('BOT_TOKEN'):
            self.config['bot_token'] = os.environ.get('BOT_TOKEN')

    def save_config(self):
        """Lưu cấu hình ra file"""
        # Trên Render, việc này chỉ lưu tạm thời
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)
    
    def get_user_data(self, user_id: str) -> Dict:
        """Lấy dữ liệu người dùng, ưu tiên Env Vars cho Admin"""
        user_id = str(user_id)
        
        if user_id not in self.config['users']:
            self.config['users'][user_id] = {
                'threads_token': '',
                'threads_delay_min': 8,
                'threads_delay_max': 15,
                'threads_job_limit': 0
            }
        
        # Nếu là Admin (hoặc user trùng khớp), và Token chưa có trong config, thử lấy từ Env
        # Hoặc luôn ưu tiên Env nếu muốn fix cứng
        if user_id == self.admin_id or self.admin_id == '*':
            env_token = os.environ.get('THREADS_TOKEN')
            if env_token and not self.config['users'][user_id].get('threads_token'):
                 self.config['users'][user_id]['threads_token'] = env_token
            
            # Load delay configs from env if available
            if os.environ.get('THREADS_DELAY_MIN'):
                self.config['users'][user_id]['threads_delay_min'] = int(os.environ.get('THREADS_DELAY_MIN'))
            if os.environ.get('THREADS_DELAY_MAX'):
                 self.config['users'][user_id]['threads_delay_max'] = int(os.environ.get('THREADS_DELAY_MAX'))
                 
        self.save_config()
        return self.config['users'][user_id]
    
    def save_user_token(self, user_id: str, platform: str, token: str):
        """Lưu token của người dùng"""
        user_id = str(user_id)
        user_data = self.get_user_data(user_id)
        user_data[f'{platform}_token'] = token
        self.config['users'][user_id] = user_data
        self.save_config()
    
    def save_user_setting(self, user_id: str, setting_key: str, value):
        """Lưu setting của người dùng (cookie, delay, job_limit)"""
        user_id = str(user_id)
        user_data = self.get_user_data(user_id)
        user_data[setting_key] = value
        self.config['users'][user_id] = user_data
        self.save_config()


bot_manager = GolikeBot()

async def send_completion_notification(context: ContextTypes.DEFAULT_TYPE, user_id: int, platform: str, stats: dict):
    """Gửi thông báo khi tool hoàn thành"""
    platform_emoji = {'threads': '🧵'}[platform]
    
    completion_text = f"""
✅ **HOÀN THÀNH**

{platform_emoji} **Tool {platform.title()} đã hoàn thành!**

📊 **Thống kê:**
• Jobs hoàn thành: {stats.get('jobs_completed', 0)}
• Coin kiếm được: {stats.get('coins_earned', 0)} VND
• Thời gian chạy: {stats.get('duration', 'N/A')}

💡 Sử dụng /{platform} để chạy lại.
"""
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=completion_text,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Lỗi khi gửi thông báo hoàn thành: {e}")

async def cleanup_task(user_id: int, platform: str = None):
    """Dọn dẹp task sau khi hoàn thành hoặc dừng"""
    if user_id in running_tasks:
        if platform is None or running_tasks[user_id]['platform'] == platform:
            del running_tasks[user_id]
            logger.info(f"Đã dọn dẹp task cho user {user_id}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /start - Chào mừng người dùng"""
    user = update.effective_user
    welcome_text = f"""
👋 Xin chào {user.first_name}!

🤖 **Bot Golike Automation Tool**

Bot này giúp bạn tự động hóa nhiệm vụ trên Golike cho:
• 🧵 Threads

📋 **Lệnh có sẵn:**
/threads - Chạy tool Threads
/status - Kiểm tra trạng thái
/stop - Dừng tool đang chạy
/settings - Cài đặt token
/help - Hiển thị trợ giúp

⚙️ **Bắt đầu sử dụng:**
Sử dụng /settings để thêm Golike Authorization token cho Threads.
"""
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /help - Hiển thị trợ giúp"""
    help_text = """
📚 **HƯỚNG DẪN SỬ DỤNG**

**1️⃣ Cài đặt Token:**
• Sử dụng lệnh /settings
• Chọn Threads
• Nhập Authorization token từ Golike

**2️⃣ Chạy Tool:**
• /threads - Tự động hóa Threads

**3️⃣ Quản lý:**
• /status - Xem trạng thái
• /stop - Dừng tool hiện tại

**❓ Lấy Authorization Token:**
1. Đăng nhập vào https://app.golike.net
2. Mở Developer Tools (F12)
3. Vào tab Network
4. Làm mới trang
5. Tìm request đến api/users/me
6. Copy giá trị trong header "Authorization"

**⚠️ Lưu ý:**
• Chỉ cần treo máy, bot tự làm việc
• Token cần được làm mới nếu hết hạn
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /settings - Cài đặt token"""
    keyboard = [
        [
            InlineKeyboardButton("🧵 Threads", callback_data='set_threads'),
        ],
        [
            InlineKeyboardButton("📋 Xem Token", callback_data='view_tokens'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        '⚙️ **CÀI ĐẶT TOKEN**\n\nChọn nền tảng bạn muốn cài đặt token:',
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý callback từ inline buttons"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    
    if query.data == 'view_tokens':
        user_data = bot_manager.get_user_data(user_id)
        tokens_text = "🔑 **TOKEN CỦA BẠN:**\n\n"
        
        token = user_data.get('threads_token', '')
        status = '✅ Đã cài đặt' if token else '❌ Chưa cài đặt'
        tokens_text += f"🧵 **Threads:** {status}\n"
        if token:
            tokens_text += f"   `{token[:20]}...{token[-10:]}`\n"
        
        await query.edit_message_text(tokens_text, parse_mode='Markdown')
        return
    
    if query.data.startswith('set_'):
        platform = query.data.replace('set_', '')
        context.user_data['setting_platform'] = platform
        
        platform_name = {'threads': '🧵 Threads'}[platform]
        
        await query.edit_message_text(
            f"🔑 **CÀI ĐẶT TOKEN CHO {platform_name.upper()}**\n\n"
            f"Vui lòng gửi Authorization token của bạn từ Golike.\n\n"
            f"Gửi /cancel để hủy.",
            parse_mode='Markdown'
        )
        return WAITING_TOKEN

async def receive_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Nhận token từ người dùng"""
    token = update.message.text.strip()
    platform = context.user_data.get('setting_platform')
    user_id = str(update.effective_user.id)
    
    if not platform:
        await update.message.reply_text("❌ Có lỗi xảy ra. Vui lòng thử lại với /settings")
        return ConversationHandler.END
    
    # Lưu token
    bot_manager.save_user_token(user_id, platform, token)
    
    platform_name = {'threads': '🧵 Threads'}[platform]
    
    await update.message.reply_text(
        f"✅ **ĐÃ LƯU TOKEN**\n\n"
        f"Token cho {platform_name} đã được lưu thành công!\n\n"
        f"Bạn có thể bắt đầu sử dụng /{platform} để chạy tool.",
        parse_mode='Markdown'
    )
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hủy conversation"""
    await update.message.reply_text("❌ Đã hủy. Sử dụng /settings để thử lại.")
    return ConversationHandler.END

async def config_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /config - Hướng dẫn cấu hình"""
    user_id = str(update.effective_user.id)
    user_data = bot_manager.get_user_data(user_id)
    
    config_text = f"""⚙️ **CẤU HÌNH HIỆN TẠI**

**🧵 Threads:**
• Jobs: `{user_data.get('threads_job_limit', 0) or 'Unlimited'}`
• Delay: `{user_data.get('threads_delay_min', 8)}-{user_data.get('threads_delay_max', 15)}s`



📝 **Cách thay đổi:**
Chỉnh sửa file `bot_config.json` → Tìm user ID `{user_id}` → Thay đổi các giá trị → Restart bot
"""
    
    await update.message.reply_text(config_text, parse_mode='Markdown')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /status - Kiểm tra trạng thái"""
    user_id = update.effective_user.id
    
    if user_id in running_tasks:
        task_info = running_tasks[user_id]
        platform = task_info['platform']
        platform_emoji = {'threads': '🧵'}[platform]
        
        status_text = f"""
🟢 **TOOL ĐANG CHẠY**

{platform_emoji} **Nền tảng:** {platform.title()}
⏱️ **Trạng thái:** Đang hoạt động
🔄 **Thread:** {task_info.get('thread', 'N/A')}

Sử dụng /stop để dừng tool.
"""
    else:
        status_text = """
⚪ **KHÔNG CÓ TOOL NÀO ĐANG CHẠY**

Sử dụng lệnh sau để bắt đầu:
• /threads
"""
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

async def stop_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /stop - Dừng tool đang chạy"""
    user_id = update.effective_user.id
    
    if user_id in running_tasks:
        task_info = running_tasks[user_id]
        platform = task_info['platform']
        platform_emoji = {'threads': '🧵'}[platform]
        
        # Dừng runner nếu có
        if 'runner' in task_info and task_info['runner']:
            task_info['runner'].stop()
            logger.info(f"Stopped runner for user {user_id}, platform {platform}")
        
        # Đánh dấu để dừng
        task_info['stop_flag'] = True
        
        await update.message.reply_text(
            f"⏹️ **ĐANG DỪNG TOOL**\n\n"
            f"{platform_emoji} Tool **{platform.title()}** đang được dừng...\n\n"
            f"✅ Tool sẽ dừng ngay sau job hiện tại.\n"
            f"📊 Bạn sẽ nhận được báo cáo kết quả cuối cùng.",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "ℹ️ **KHÔNG CÓ TOOL ĐANG CHẠY**\n\n"
            "Hiện tại không có tool nào đang hoạt động.\n"
            "Sử dụng /threads để bắt đầu.",
            parse_mode='Markdown'
        )



# === THREADS ONLY ===

async def run_threads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /threads - Chạy tool Threads"""
    user_id = update.effective_user.id
    user_id_str = str(user_id)
    
    if user_id in running_tasks:
        current_platform = running_tasks[user_id]['platform']
        await update.message.reply_text(
            f"⚠️ Tool {current_platform.title()} đang chạy!\n\n"
            f"Sử dụng /stop để dừng trước khi chạy tool khác."
        )
        return
    
    user_data = bot_manager.get_user_data(user_id_str)
    token = user_data.get('threads_token', '')
    
    if not token:
        await update.message.reply_text(
            "❌ **CHƯ A CÓ TOKEN**\n\n"
            "Bạn chưa cài đặt Authorization token cho Threads.\n"
            "Sử dụng /settings để cài đặt token.",
            parse_mode='Markdown'
        )
        return
    
    # Lấy settings
    delay_min = user_data.get('threads_delay_min', 8)
    delay_max = user_data.get('threads_delay_max', 15)
    job_limit = user_data.get('threads_job_limit', 0)  # 0 = unlimited
    
    running_tasks[user_id] = {
        'platform': 'threads',
        'stop_flag': False,
        'thread': None,
        'start_time': time.time()
    }
    
    await update.message.reply_text(
        f"🚀 **BẮT ĐẦU TOOL THREADS**\n\n"
        f"🧵 Tool Threads đang khởi động...\n\n"
        f"⚙️ **Cấu hình:**\n"
        f"• Jobs: `{job_limit if job_limit > 0 else 'Không giới hạn'}`\n"
        f"• Delay: `{delay_min}-{delay_max}s`\n\n"
        f"⚡ Sử dụng `/config` để thay đổi!",
        parse_mode='Markdown'
    )
    
    async def run_threads_task():
        start_time = time.time()
        
        # CRITICAL FIX: Capture event loop before spawning thread
        main_loop = asyncio.get_event_loop()
        
        # Callback để gửi updates từ worker thread
        def send_update(msg: str):
            try:
                future = asyncio.run_coroutine_threadsafe(
                    context.bot.send_message(chat_id=user_id, text=msg, parse_mode='Markdown'),
                    main_loop
                )
                future.result(timeout=10)
            except Exception as e:
                logger.error(f"Error sending update: {e}")
        
        # Lấy auto_switch setting  
        auto_switch = user_data.get('auto_switch_threads_account', True)
        
        runner = GolikeThreadsRunner(token, send_update, delay_min, delay_max, auto_switch)
        running_tasks[user_id]['runner'] = runner
        
        stats = await main_loop.run_in_executor(None, runner.run, job_limit if job_limit > 0 else None)  # Use job_limit
        
        duration = int(time.time() - start_time)
        stats['duration'] = f"{duration // 60}p {duration % 60}s"
        
        await send_completion_notification(context, user_id, 'threads', stats)
        await cleanup_task(user_id, 'threads')
    
    asyncio.create_task(run_threads_task())

def main():
    """Khởi động bot"""
    # Fix Windows console encoding
    import sys
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    
    # Kiểm tra token
    if not bot_manager.config.get('bot_token'):
        print("Loi: Chua cau hinh bot token!")
        print("Vui long tao file bot_config.json voi noi dung:")
        print(json.dumps({
            "bot_token": "YOUR_BOT_TOKEN_HERE",
            "users": {}
        }, indent=2))
        return
    
    # Tạo application
    application = Application.builder().token(bot_manager.config['bot_token']).build()
    
    # Conversation handler cho settings
    settings_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_callback, pattern='^set_')],
        states={
            WAITING_TOKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_token)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    # Đăng ký handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("settings", settings))
    application.add_handler(CommandHandler("config", config_command))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("stop", stop_task))
    application.add_handler(CommandHandler("threads", run_threads))  # ONLY ACTIVE
    application.add_handler(settings_conv)
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Start keep_alive server (Render 24/7)
    from keep_alive import keep_alive
    keep_alive()
    
    # Khởi động bot
    print("Bot dang chay...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
