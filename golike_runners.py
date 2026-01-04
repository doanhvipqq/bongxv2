"""
Wrapper functions để chạy Golike tools từ Telegram bot
"""
import requests
import time
import random
from typing import Callable, Optional

class GolikeThreadsRunner:
    """Chạy Golike Threads automation"""
    
    def __init__(self, token: str, callback: Optional[Callable] = None, delay_min: int = 8, delay_max: int = 15, auto_switch_account: bool = True):
        self.token = token
        self.callback = callback
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.auto_switch_account = auto_switch_account
        self.stop_flag = False
        self.ses = requests.Session()
        self.stats = {'jobs_completed': 0, 'likes': 0, 'follows': 0, 'coins_earned': 0, 'errors': 0}
        
        # Multi-account support
        self.all_accounts = []  # Danh sách tất cả Threads accounts
        self.current_account_index = 0  # Index của account đang dùng
        self.accounts_no_jobs = set()  # Track accounts đã hết jobs
        
        # User agents
        self.user_agents = [
            "android|Mozilla/5.0 (Linux; Android 13; Pixel 6a Build/TQ3A.230805.001; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/116.0.0.0 Mobile Safari/537.36",
            "android|Mozilla/5.0 (Linux; U; Android 7.1; GT-I9100 Build/KTU84P) AppleWebKit/603.12 (KHTML, like Gecko) Chrome/50.0.3755.367 Mobile Safari/600.8"
        ]

        
    def send_update(self, message: str):
        """Gửi update về bot nếu có callback"""
        if self.callback:
            self.callback(message)
    
    def run(self, max_jobs: int = None):
        """Chạy Threads automation - max_jobs=None nghĩa là chạy vô hạn"""
        try:
            User_Agent = random.choice(self.user_agents)
            
            # Headers
            headers = {
                'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8',
                'Referer': 'https://app.golike.net/',
                'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="125", "Chromium";v="121"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': "Windows",
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'T': 'VFZSamQwOUVSVEpQVkZFd1RrRTlQUT09',
                'User-Agent': User_Agent,
                "Authorization": self.token,
                'Content-Type': 'application/json;charset=utf-8'
            }
            
            # Kiểm tra login
            self.send_update("⏳ **Đang kiểm tra tài khoản...**")
            url1 = 'https://gateway.golike.net/api/users/me'
            check_login = self.ses.get(url1, headers=headers).json()
            
            if check_login.get('status') != 200:
                self.send_update("❌ **LỖI ĐĂNG NHẬP**\n\nToken không hợp lệ hoặc đã hết hạn!")
                return self.stats
            
            username = check_login['data']['username']
            coin = check_login['data']['coin']
            self.send_update(f"✅ **ĐĂNG NHẬP THÀNH CÔNG**\n\n👤 User: `{username}`\n💰 Số dư: `{coin} VND`")
            
            # Lấy danh sách threads accounts
            self.send_update("⏳ Đang lấy danh sách Threads accounts...")
            check_account = requests.get('https://gateway.golike.net/api/threads-account', headers=headers).json()
            
            if not check_account.get('data'):
                self.send_update("❌ **LỖI**\n\nKhông tìm thấy Threads account nào!\nVui lòng thêm Threads account vào Golike.")
                return self.stats
            
            # Lưu TẤT CẢ accounts
            self.all_accounts = check_account['data']
            
            # Hiển thị danh sách accounts
            if len(self.all_accounts) > 1:
                accounts_list = "📱 **THREADS ACCOUNTS:**\n\n"
                for idx, acc in enumerate(self.all_accounts, 1):
                    accounts_list += f"{idx}. `{acc['name']}` (ID: {acc['id']})\n"
                accounts_list += f"\n{'🔄 Auto-switch: ON' if self.auto_switch_account else '⚠️ Auto-switch: OFF'}"
                self.send_update(accounts_list)
            
            # Bắt đầu với account đầu tiên
            account_id = self.all_accounts[self.current_account_index]['id']
            account_name = self.all_accounts[self.current_account_index]['name']
            self.send_update(f"📱 **Đang dùng account:** `{account_name}` ({self.current_account_index + 1}/{len(self.all_accounts)})")
            
            # Bắt đầu làm jobs
            if max_jobs:
                self.send_update(f"🚀 **BẮT ĐẦU**\n\nLàm tối đa {max_jobs} jobs\nDùng /stop để dừng")
            else:
                self.send_update(f"🚀 **BẮT ĐẦU CHẠY LIÊN TỤC**\n\n♾️ Không giới hạn jobs\n⏹️ Dùng /stop để dừng")
            
            job_count = 0
            consecutive_errors = 0  # Đếm lỗi liên tiếp
            
            while not self.stop_flag:
                # Kiểm tra giới hạn jobs nếu có
                if max_jobs and job_count >= max_jobs:
                    break
                    
                try:
                    # Lấy job
                    job_url = f'https://gateway.golike.net/api/advertising/publishers/threads/jobs?account_id={account_id}'
                    job_response = self.ses.get(job_url, headers=headers).json()
                    
                    if job_response.get('status') != 200:
                        msg = job_response.get('message', 'Không có job')
                        
                        # Thử chuyển sang account khác nếu bật auto-switch
                        if self.auto_switch_account and len(self.all_accounts) > 1:
                            # Đánh dấu account hiện tại hết jobs
                            self.accounts_no_jobs.add(self.current_account_index)
                            
                            # Thử tìm account khác
                            if len(self.accounts_no_jobs) < len(self.all_accounts):
                                # Chuyển sang account tiếp theo
                                self.current_account_index = (self.current_account_index + 1) % len(self.all_accounts)
                                
                                # Skip các account đã hết jobs
                                while self.current_account_index in self.accounts_no_jobs:
                                    self.current_account_index = (self.current_account_index + 1) % len(self.all_accounts)
                                
                                account_id = self.all_accounts[self.current_account_index]['id']
                                account_name = self.all_accounts[self.current_account_index]['name']
                                
                                self.send_update(
                                    f"🔄 **CHUYỂN ACCOUNT**\n\n"
                                    f"Account cũ hết job: `{msg}`\n"
                                    f"📱 Chuyển sang: `{account_name}` ({self.current_account_index + 1}/{len(self.all_accounts)})\n"
                                    f"⏳ Thử lấy jobs..."
                                )
                                time.sleep(3)  # Đợi 3 giây trước khi lấy job từ account mới
                                continue
                            else:
                                # Tất cả accounts đều hết jobs
                                self.send_update(
                                    f"⚠️ **TẤT CẢ ACCOUNTS HẾT JOBS**\n\n"
                                    f"Đã thử {len(self.all_accounts)} accounts\n"
                                    f"⏳ Đợi 30 giây rồi reset..."
                                )
                                time.sleep(30)
                                # Reset lại để thử vòng mới
                                self.accounts_no_jobs.clear()
                                self.current_account_index = 0
                                account_id = self.all_accounts[0]['id']
                                account_name = self.all_accounts[0]['name']
                                self.send_update(f"🔄 Reset - thử lại với `{account_name}`")
                                continue
                        else:
                            # Logic cũ: không auto-switch hoặc chỉ có 1 account
                            consecutive_errors += 1
                            self.send_update(f"⚠️ `{msg}`\n\n⏳ Đợi 10 giây rồi thử lại... (Lỗi {consecutive_errors}/5)")
                            time.sleep(10)
                            continue
                    
                    # Reset consecutive errors khi lấy job thành công
                    consecutive_errors = 0
                    
                    ads_id = job_response['data']['id']
                    object_id = job_response['data']['object_id']
                    job_type = job_response['data']['type']
                    
                    # Thông báo bắt đầu job
                    job_emoji = "❤️" if job_type == "like" else "➕"
                    self.send_update(f"⏳ **JOB #{job_count + 1}**\n\n{job_emoji} Loại: `{job_type.upper()}`\n🆔 ID: `{ads_id}`\n⏱️ Đang xử lý...")
                    
                    # Delay ngẫu nhiên
                    delay = random.randint(self.delay_min, self.delay_max)
                    time.sleep(delay)
                    
                    # Kiểm tra stop_flag sau delay
                    if self.stop_flag:
                        break
                    
                    # Complete job
                    complete_url = 'https://gateway.golike.net/api/advertising/publishers/threads/complete-jobs'
                    json_data = {
                        'account_id': account_id,
                        'ads_id': ads_id,
                    }
                    
                    response = requests.post(complete_url, headers=headers, json=json_data).json()
                    
                    if response.get('success'):
                        prices = response['data']['prices']
                        self.stats['jobs_completed'] += 1
                        self.stats['coins_earned'] += prices
                        
                        if job_type == 'follow':
                            self.stats['follows'] += 1
                        elif job_type == 'like':
                            self.stats['likes'] += 1
                        
                        job_count += 1
                        
                        # Reset accounts_no_jobs khi có job thành công
                        if self.current_account_index in self.accounts_no_jobs:
                            self.accounts_no_jobs.discard(self.current_account_index)
                        
                        # Thông báo hoàn thành job
                        account_info = f" | 📱 {self.all_accounts[self.current_account_index]['name']}" if len(self.all_accounts) > 1 else ""
                        self.send_update(
                            f"✅ **HOÀN THÀNH JOB #{job_count}**\n\n"
                            f"{job_emoji} `{job_type.upper()}`\n"
                            f"💵 Nhận: `+{prices} VND`\n"
                            f"💰 Tổng: `{self.stats['coins_earned']} VND`\n"
                            f"📊 Tổng jobs: `{job_count}`{account_info}"
                        )
                        
                        consecutive_errors = 0  # Reset lỗi liên tiếp
                        
                    else:
                        # Job thất bại
                        self.stats['errors'] += 1
                        error_msg = response.get('message', 'Không rõ')
                        self.send_update(
                            f"⚠️ **JOB THẤT BẠI**\n\n"
                            f"🆔 ID: `{ads_id}`\n"
                            f"❌ Lý do: `{error_msg}`\n"
                            f"🔄 Đang skip job..."
                        )
                        
                        # Skip job
                        skip_url = 'https://gateway.golike.net/api/advertising/publishers/threads/skip-jobs'
                        skip_params = {
                            'ads_id': ads_id,
                            'account_id': account_id,
                            'object_id': object_id,
                            'async': 'true',
                            'data': 'null',
                            'type': job_type,
                        }
                        self.ses.post(skip_url, params=skip_params)
                        
                except KeyError as e:
                    self.stats['errors'] += 1
                    consecutive_errors += 1
                    self.send_update(
                        f"❌ **LỖI DỮ LIỆU**\n\n"
                        f"Thiếu field: `{str(e)}`\n"
                        f"⏳ Thử lại sau 5 giây..."
                    )
                    time.sleep(5)
                    continue
                    
                except requests.exceptions.RequestException as e:
                    self.stats['errors'] += 1
                    consecutive_errors += 1
                    self.send_update(
                        f"❌ **LỖI KẾT NỐI**\n\n"
                        f"Chi tiết: `{str(e)[:100]}`\n"
                        f"⏳ Thử lại sau 10 giây..."
                    )
                    time.sleep(10)
                    continue
                    
                except Exception as e:
                    self.stats['errors'] += 1
                    consecutive_errors += 1
                    self.send_update(
                        f"❌ **LỖI KHÔNG XÁC ĐỊNH**\n\n"
                        f"Chi tiết: `{str(e)[:100]}`\n"
                        f"⏳ Thử lại sau 5 giây..."
                    )
                    time.sleep(5)
                    continue
            
            # Thông báo kết thúc
            if self.stop_flag:
                self.send_update(
                    f"⏹️ **ĐÃ DỪNG**\n\n"
                    f"Tool đã dừng theo yêu cầu của bạn."
                )
            else:
                self.send_update(
                    f"🎉 **HOÀN THÀNH TẤT CẢ**\n\n"
                    f"Đã làm xong {job_count} jobs!"
                )
            
            return self.stats
            
        except Exception as e:
            self.send_update(
                f"❌ **LỖI NGHIÊM TRỌNG**\n\n"
                f"Tool bị crash: `{str(e)[:150]}`\n\n"
                f"Vui lòng báo lỗi này cho admin!"
            )
            return self.stats
    
    def stop(self):
        """Dừng tool"""
        self.stop_flag = True


class GolikeInstagramRunner:
    """Chạy Golike Instagram automation"""
    
    def __init__(self, token: str, callback: Optional[Callable] = None, cookie: str = '', delay_min: int = 10, delay_max: int = 18, auto_switch_account: bool = True):
        self.token = token
        self.callback = callback
        self.cookie = cookie
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.auto_switch_account = auto_switch_account
        self.stop_flag = False
        self.ses = requests.Session()
        self.stats = {'jobs_completed': 0, 'likes': 0, 'follows': 0, 'comments': 0, 'coins_earned': 0, 'errors': 0}
        
        # Multi-account support
        self.all_accounts = []
        self.current_account_index = 0
        self.accounts_no_jobs = set()
        
        self.user_agents = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Linux; Android 13; Pixel 6a) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Mobile Safari/537.36"
        ]
    
    def send_update(self, message: str):
        if self.callback:
            self.callback(message)
    
    def run(self, max_jobs: int = None):
        """Chạy Instagram automation - max_jobs=None nghĩa là chạy vô hạn"""
        try:
            User_Agent = random.choice(self.user_agents)
            
            # Headers
            headers = {
                'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8',
                'Referer': 'https://app.golike.net/',
                'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="125", "Chromium";v="121"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': "Windows",
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'T': 'VFZSamQwOUVSVEpQVkVFd1RrRTlQUT09',
                'User-Agent': User_Agent,
                "Authorization": self.token,
                'Content-Type': 'application/json;charset=utf-8'
            }
            
            # Kiểm tra login
            self.send_update("⏳ **Đang kiểm tra tài khoản...**")
            url1 = 'https://gateway.golike.net/api/users/me'
            check_login = self.ses.get(url1, headers=headers).json()
            
            if check_login.get('status') != 200:
                self.send_update("❌ **LỖI ĐĂNG NHẬP**\n\nToken không hợp lệ!")
                return self.stats
            
            username = check_login['data']['username']
            coin = check_login['data']['coin']
            self.send_update(f"✅ **ĐĂNG NHẬP THÀNH CÔNG**\n\n👤 User: `{username}`\n💰 Số dư: `{coin} VND`")
            
            # Lấy Instagram accounts
            self.send_update("⏳ Đang lấy danh sách Instagram accounts...")
            check_account = requests.get('https://gateway.golike.net/api/instagram-account', headers=headers).json()
            
            if not check_account.get('data'):
                self.send_update("❌ **LỖI**\n\nKhông tìm thấy Instagram account!\nThêm Instagram account vào Golike.")
                return self.stats
            
            # Lưu TẤT CẢ accounts
            self.all_accounts = check_account['data']
            
            # Hiển thị danh sách accounts
            if len(self.all_accounts) > 1:
                accounts_list = "📱 **INSTAGRAM ACCOUNTS:**\n\n"
                for idx, acc in enumerate(self.all_accounts, 1):
                    accounts_list += f"{idx}. @{acc['instagram_username']} (ID: {acc['id']})\n"
                accounts_list += f"\n{'🔄 Auto-switch: ON' if self.auto_switch_account else '⚠️ Auto-switch: OFF'}"
                self.send_update(accounts_list)
            
            # Bắt đầu với account đầu tiên  
            account_id = self.all_accounts[self.current_account_index]['id']
            account_name = self.all_accounts[self.current_account_index]['instagram_username']
            self.send_update(f"📱 **Đang dùng:** `@{account_name}` ({self.current_account_index + 1}/{len(self.all_accounts)})\n🍪 Cookie: {'✅ Có' if self.cookie else '⚠️ Không (chỉ claim)'}")
            
            # Bắt đầu
            if max_jobs:
                self.send_update(f"🚀 **BẮT ĐẦU**\n\nTối đa {max_jobs} jobs")
            else:
                self.send_update(f"🚀 **CHẠY LIÊN TỤC**\n\n♾️ Dùng /stop để dừng")
            
            job_count = 0
            consecutive_errors = 0
            
            while not self.stop_flag:
                if max_jobs and job_count >= max_jobs:
                    break
                
                try:
                    # Lấy job
                    job_url = f'https://gateway.golike.net/api/advertising/publishers/instagram/jobs'
                    params = {'instagram_account_id': account_id, 'data': 'null'}
                    job_response = self.ses.get(job_url, headers=headers, params=params).json()
                    
                    if job_response.get('status') != 200:
                        msg = job_response.get('message', 'Không có job')
                        
                        # Thử chuyển account nếu bật auto-switch
                        if self.auto_switch_account and len(self.all_accounts) > 1:
                            self.accounts_no_jobs.add(self.current_account_index)
                            
                            if len(self.accounts_no_jobs) < len(self.all_accounts):
                                self.current_account_index = (self.current_account_index + 1) % len(self.all_accounts)
                                while self.current_account_index in self.accounts_no_jobs:
                                    self.current_account_index = (self.current_account_index + 1) % len(self.all_accounts)
                                
                                account_id = self.all_accounts[self.current_account_index]['id']
                                account_name = self.all_accounts[self.current_account_index]['instagram_username']
                                
                                self.send_update(
                                    f"🔄 **CHUYỂN ACCOUNT**\n\n"
                                    f"@{self.all_accounts[(self.current_account_index - 1) % len(self.all_accounts)]['instagram_username']} hết jobs\n"
                                    f"📱 Sang: @{account_name} ({self.current_account_index + 1}/{len(self.all_accounts)})"
                                )
                                time.sleep(3)
                                continue
                            else:
                                self.send_update(f"⚠️ **TẤT CẢ {len(self.all_accounts)} ACCOUNTS HẾT JOBS**\n⏳ Đợi 30s...")
                                time.sleep(30)
                                self.accounts_no_jobs.clear()
                                self.current_account_index = 0
                                account_id = self.all_accounts[0]['id']
                                account_name = self.all_accounts[0]['instagram_username']
                                self.send_update(f"🔄 Reset - @{account_name}")
                                continue
                        else:
                            consecutive_errors += 1
                            self.send_update(f"⚠️ `{msg}`\n\n⏳ Đợi 10s... (Lỗi {consecutive_errors}/5)")
                            time.sleep(10)
                            continue
                    
                    consecutive_errors = 0
                    ads_id = job_response['data']['id']
                    object_id = job_response['data']['object_id']
                    job_type = job_response['data']['type']
                    
                    # Thông báo job
                    job_emoji = {"like": "❤️", "follow": "➕", "comment": "💬"}.get(job_type, "📝")
                    self.send_update(f"⏳ **JOB #{job_count + 1}**\n\n{job_emoji} `{job_type.upper()}`\n🆔 `{ads_id}`")
                    
                    # Use custom delay
                    delay = random.randint(self.delay_min, self.delay_max)
                    
                    # Perform actual Instagram action if cookie is provided
                    if self.cookie:
                        try:
                            # Extract csrftoken from cookie
                            csrftoken = self.cookie.split('csrftoken=')[1].split(';')[0] if 'csrftoken=' in self.cookie else ''
                            
                            # Instagram headers with cookie
                            ig_headers = {
                                'accept': '*/*',
                                'accept-language': 'vi,en-US;q=0.9,en;q=0.8',
                                'content-type': 'application/x-www-form-urlencoded',
                                'cookie': self.cookie,
                                'origin': 'https://www.instagram.com',
                                'referer': 'https://www.instagram.com/',
                                'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
                                'x-csrftoken': csrftoken,
                                'x-ig-app-id': '936619743392459',
                                'x-instagram-ajax': '1014868636',
                                'x-requested-with': 'XMLHttpRequest',
                            }
                            
                            if job_type == 'follow':
                                # Follow user on Instagram
                                follow_url = f'https://www.instagram.com/api/v1/friendships/create/{object_id}/'
                                follow_data = {
                                    'container_module': 'profile',
                                    'nav_chain': 'PolarisFeedRoot:feedPage:8:topnav-link',
                                    'user_id': object_id
                                }
                                ig_response = requests.post(follow_url, headers=ig_headers, data=follow_data)
                                self.send_update(f"📱 Đã follow trên Instagram: {'✅' if 'ok' in ig_response.text else '⚠️'}")
                            
                            elif job_type == 'like':
                                # Like post on Instagram  
                                like_id = job_response['data'].get('description', object_id)
                                like_url = f'https://www.instagram.com/api/v1/web/likes/{like_id}/like/'
                                ig_response = requests.post(like_url, headers=ig_headers)
                                self.send_update(f"📱 Đã like trên Instagram: {'✅' if 'ok' in ig_response.text else '⚠️'}")
                        
                        except Exception as e:
                            self.send_update(f"⚠️ Lỗi Instagram action: `{str(e)[:50]}`")
                    
                    time.sleep(delay)
                    
                    if self.stop_flag:
                        break
                    
                    # Complete job - CRITICAL FIX: use instagram_users_advertising_id
                    complete_url = 'https://gateway.golike.net/api/advertising/publishers/instagram/complete-jobs'
                    json_data = {
                        'instagram_account_id': account_id,
                        'instagram_users_advertising_id': ads_id,  # CORRECT parameter name
                        'async': True,
                        'data': 'null'
                    }
                    response = requests.post(complete_url, headers=headers, json=json_data).json()
                    
                    if response.get('success'):
                        prices = response['data']['prices']
                        self.stats['jobs_completed'] += 1
                        self.stats['coins_earned'] += prices
                        
                        if job_type == 'follow':
                            self.stats['follows'] += 1
                        elif job_type == 'like':
                            self.stats['likes'] += 1
                        elif job_type == 'comment':
                            self.stats['comments'] += 1
                        
                        job_count += 1
                        
                        if self.current_account_index in self.accounts_no_jobs:
                            self.accounts_no_jobs.discard(self.current_account_index)
                        
                        account_info = f" | @{self.all_accounts[self.current_account_index]['instagram_username']}" if len(self.all_accounts) > 1 else ""
                        self.send_update(
                            f"✅ **JOB #{job_count} HOÀN THÀNH**\n\n"
                            f"{job_emoji} `{job_type.upper()}`\n"
                            f"💵 +`{prices} VND`\n"
                            f"💰 Tổng: `{self.stats['coins_earned']} VND`{account_info}"
                        )
                    else:
                        self.stats['errors'] += 1
                        self.send_update(f"⚠️ **JOB THẤT BẠI**\n\n🔄 Skip...")
                        
                except Exception as e:
                    self.stats['errors'] += 1
                    consecutive_errors += 1
                    self.send_update(f"❌ **LỖI**\n\n`{str(e)[:100]}`")
                    time.sleep(5)
            
            if self.stop_flag:
                self.send_update("⏹️ **ĐÃ DỪNG**")
            else:
                self.send_update(f"🎉 **HOÀN THÀNH**\n\n{job_count} jobs!")
            
            return self.stats
            
        except Exception as e:
            self.send_update(f"❌ **LỖI NGHIÊM TRỌNG**\n\n`{str(e)[:150]}`")
            return self.stats
    
    def stop(self):
        self.stop_flag = True


class GolikeLinkedInRunner:
    """Chạy Golike LinkedIn automation"""
    
    def __init__(self, token: str, callback: Optional[Callable] = None, delay_min: int = 10, delay_max: int = 18, auto_switch_account: bool = True):
        self.token = token
        self.callback = callback
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.auto_switch_account = auto_switch_account
        self.stop_flag = False
        self.ses = requests.Session()
        self.stats = {'jobs_completed': 0, 'likes': 0, 'follows': 0, 'coins_earned': 0, 'errors': 0}
        
        # Multi-account support
        self.all_accounts = []
        self.current_account_index = 0
        self.accounts_no_jobs = set()
        
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ]
    
    def send_update(self, message: str):
        if self.callback:
            self.callback(message)
    
    def run(self, max_jobs: int = None):
        """Chạy LinkedIn automation - max_jobs=None nghĩa là chạy vô hạn"""
        try:
            User_Agent = random.choice(self.user_agents)
            
            headers = {
                'Accept-Language': 'vi,en-US;q=0.9,en;q=0.8',
                'Referer': 'https://app.golike.net/',
                'Sec-Ch-Ua': '"Not A(Brand";v="99", "Google Chrome";v="125", "Chromium";v="121"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': "Windows",
                'Sec-Fetch-Dest': 'empty',
                'Sec-Fetch-Mode': 'cors',
                'Sec-Fetch-Site': 'same-site',
                'T': 'VFZSamQwOUVSVEpQVkZFd1RrRTlQUT09',
                'User-Agent': User_Agent,
                "Authorization": self.token,
                'Content-Type': 'application/json;charset=utf-8'
            }
            
            self.send_update("⏳ **Đang kiểm tra tài khoản...**")
            url1 = 'https://gateway.golike.net/api/users/me'
            check_login = self.ses.get(url1, headers=headers).json()
            
            if check_login.get('status') != 200:
                self.send_update("❌ **LỖI ĐĂNG NHẬP**\n\nToken không hợp lệ!")
                return self.stats
            
            username = check_login['data']['username']
            coin = check_login['data']['coin']
            self.send_update(f"✅ **ĐĂNG NHẬP THÀNH CÔNG**\n\n👤 `{username}`\n💰 `{coin} VND`")
            
            self.send_update("⏳ Lấy LinkedIn accounts...")
            check_account = requests.get('https://gateway.golike.net/api/linkedin-account', headers=headers).json()
            
            if not check_account.get('data'):
                self.send_update("❌ **LỖI**\n\nKhông có LinkedIn account!\nThêm account vào Golike.")
                return self.stats
            
            # Lưu TẤT CẢ accounts
            self.all_accounts = check_account['data']
            
            # Hiển thị danh sách
            if len(self.all_accounts) > 1:
                accounts_list = "📱 **LINKEDIN ACCOUNTS:**\n\n"
                for idx, acc in enumerate(self.all_accounts, 1):
                    accounts_list += f"{idx}. {acc.get('link', acc['id'])} (ID: {acc['id']})\n"
                accounts_list += f"\n{'🔄 Auto-switch: ON' if self.auto_switch_account else '⚠️ Auto-switch: OFF'}"
                self.send_update(accounts_list)
            
            account_id = self.all_accounts[self.current_account_index]['id']
            account_name = self.all_accounts[self.current_account_index].get('link', f"ID-{account_id}")
            self.send_update(f"📱 **Đang dùng:** `{account_name}` ({self.current_account_index + 1}/{len(self.all_accounts)})")
            
            if max_jobs:
                self.send_update(f"🚀 **BẮT ĐẦU**\n\nTối đa {max_jobs} jobs")
            else:
                self.send_update(f"🚀 **CHẠY LIÊN TỤC**\n\n♾️ /stop để dừng")
            
            job_count = 0
            consecutive_errors = 0
            
            while not self.stop_flag:
                if max_jobs and job_count >= max_jobs:
                    break
                
                try:
                    job_url = f'https://gateway.golike.net/api/advertising/publishers/linkedin/jobs'
                    params = {'linkedin_account_id': account_id, 'data': 'null'}
                    job_response = self.ses.get(job_url, headers=headers, params=params).json()
                    
                    if job_response.get('status') != 200:
                        msg = job_response.get('message', 'Không có job')
                        
                        if self.auto_switch_account and len(self.all_accounts) > 1:
                            self.accounts_no_jobs.add(self.current_account_index)
                            
                            if len(self.accounts_no_jobs) < len(self.all_accounts):
                                self.current_account_index = (self.current_account_index + 1) % len(self.all_accounts)
                                while self.current_account_index in self.accounts_no_jobs:
                                    self.current_account_index = (self.current_account_index + 1) % len(self.all_accounts)
                                
                                account_id = self.all_accounts[self.current_account_index]['id']
                                account_name = self.all_accounts[self.current_account_index].get('link', f"ID-{account_id}")
                                
                                self.send_update(f"🔄 **CHUYỂN ACCOUNT**\n\n📱 Sang: {account_name} ({self.current_account_index + 1}/{len(self.all_accounts)})")
                                time.sleep(3)
                                continue
                            else:
                                self.send_update(f"⚠️ **TẤT CẢ {len(self.all_accounts)} ACCOUNTS HẾT JOBS**\n⏳ 30s...")
                                time.sleep(30)
                                self.accounts_no_jobs.clear()
                                self.current_account_index = 0
                                account_id = self.all_accounts[0]['id']
                                continue
                        else:
                            consecutive_errors += 1
                            self.send_update(f"⚠️ `{msg}`\n\n⏳ Đợi 10s...")
                            time.sleep(10)
                            continue
                    
                    consecutive_errors = 0
                    ads_id = job_response['data']['id']
                    job_type = job_response['data']['type']
                    
                    job_emoji = {"like": "❤️", "follow": "➕"}.get(job_type, "📝")
                    self.send_update(f"⏳ **JOB #{job_count + 1}**\n\n{job_emoji} `{job_type.upper()}`")
                    
                    time.sleep(random.randint(self.delay_min, self.delay_max))
                    
                    if self.stop_flag:
                        break
                    
                    complete_url = 'https://gateway.golike.net/api/advertising/publishers/linkedin/complete-jobs'
                    json_data = {'linkedin_account_id': account_id, 'ads_id': ads_id}
                    response = requests.post(complete_url, headers=headers, json=json_data).json()
                    
                    if response.get('success'):
                        prices = response['data']['prices']
                        self.stats['jobs_completed'] += 1
                        self.stats['coins_earned'] += prices
                        
                        if job_type == 'follow':
                            self.stats['follows'] += 1
                        elif job_type == 'like':
                            self.stats['likes'] += 1
                        
                        job_count += 1
                        
                        if self.current_account_index in self.accounts_no_jobs:
                            self.accounts_no_jobs.discard(self.current_account_index)
                        
                        account_info = f" | {self.all_accounts[self.current_account_index].get('link', 'LinkedIn')}" if len(self.all_accounts) > 1 else ""
                        self.send_update(
                            f"✅ **JOB #{job_count} HOÀN THÀNH**\n\n"
                            f"{job_emoji} `{job_type.upper()}`\n"
                            f"💵 +`{prices} VND`\n"
                            f"💰 `{self.stats['coins_earned']} VND`{account_info}"
                        )
                    else:
                        self.stats['errors'] += 1
                        self.send_update(f"⚠️ **THẤT BẠI**\n\nSkip...")
                        
                except Exception as e:
                    self.stats['errors'] += 1
                    consecutive_errors += 1
                    self.send_update(f"❌ `{str(e)[:100]}`")
                    time.sleep(5)
            
            if self.stop_flag:
                self.send_update("⏹️ **ĐÃ DỪNG**")
            else:
                self.send_update(f"🎉 **XONG**\n\n{job_count} jobs!")
            
            return self.stats
            
        except Exception as e:
            self.send_update(f"❌ **LỖI**\n\n`{str(e)[:150]}`")
            return self.stats
    
    def stop(self):
        self.stop_flag = True

