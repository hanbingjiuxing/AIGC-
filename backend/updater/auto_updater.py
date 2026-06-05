import os
import sys
import json
import hashlib
import time
import shutil
import threading
import subprocess
from typing import Optional, Callable, Dict, Any
from datetime import datetime

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class UpdateError(Exception):
    pass


class NetworkError(UpdateError):
    pass


class DownloadError(UpdateError):
    pass


class ValidationError(UpdateError):
    pass


class InstallError(UpdateError):
    pass


class VersionInfo:
    def __init__(self, version: str, download_url: str, checksum: str,
                 checksum_type: str = 'sha256', size: int = 0,
                 release_notes: str = '', min_required_version: str = None):
        self.version = version
        self.download_url = download_url
        self.checksum = checksum
        self.checksum_type = checksum_type.lower()
        self.size = size
        self.release_notes = release_notes
        self.min_required_version = min_required_version

    def to_dict(self) -> Dict[str, Any]:
        return {
            'version': self.version,
            'download_url': self.download_url,
            'checksum': self.checksum,
            'checksum_type': self.checksum_type,
            'size': self.size,
            'release_notes': self.release_notes,
            'min_required_version': self.min_required_version
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'VersionInfo':
        return cls(
            version=data.get('version', '0.0.0'),
            download_url=data.get('download_url', ''),
            checksum=data.get('checksum', ''),
            checksum_type=data.get('checksum_type', 'sha256'),
            size=data.get('size', 0),
            release_notes=data.get('release_notes', ''),
            min_required_version=data.get('min_required_version')
        )


class AutoUpdater:
    def __init__(self, config: Dict[str, Any] = None):
        self.config = self._load_config(config)
        self.local_version = self._read_local_version()
        self.update_lock = threading.Lock()
        self.is_updating = False
        self._progress_callback: Optional[Callable[[int, int, str], None]] = None
        self._status_callback: Optional[Callable[[str], None]] = None
        self._scheduler_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def _load_config(self, config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        default_config = {
            'check_interval_hours': 6,
            'version_check_url': 'https://api.example.com/update/version',
            'download_dir': os.path.join(os.path.dirname(sys.executable), 'updates'),
            'version_file': 'version.json',
            'max_retries': 3,
            'retry_delay_seconds': 5,
            'chunk_size_bytes': 1024 * 1024,
            'timeout_seconds': 30,
            'auto_install': True,
            'auto_restart': True,
            'verify_ssl': True,
            'github_token': None
        }

        if config:
            default_config.update(config)
        return default_config

    def _read_local_version(self) -> str:
        version_file = self.config['version_file']
        if os.path.exists(version_file):
            try:
                with open(version_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get('version', '0.0.0')
            except (json.JSONDecodeError, IOError):
                pass
        return '0.0.0'

    def set_progress_callback(self, callback: Callable[[int, int, str], None]):
        self._progress_callback = callback

    def set_status_callback(self, callback: Callable[[str], None]):
        self._status_callback = callback

    def _log_status(self, message: str):
        if self._status_callback:
            self._status_callback(message)
        print(f"[AutoUpdater] {message}")

    def _report_progress(self, current: int, total: int, status: str = ''):
        if self._progress_callback:
            self._progress_callback(current, total, status)

    @staticmethod
    def _compare_versions(version1: str, version2: str) -> int:
        parts1 = [int(p) if p.isdigit() else p for p in version1.split('.')]
        parts2 = [int(p) if p.isdigit() else p for p in version2.split('.')]

        max_len = max(len(parts1), len(parts2))
        parts1 += [0] * (max_len - len(parts1))
        parts2 += [0] * (max_len - len(parts2))

        for p1, p2 in zip(parts1, parts2):
            if p1 < p2:
                return -1
            elif p1 > p2:
                return 1
        return 0

    def check_for_update(self) -> Optional[VersionInfo]:
        """检查是否有可用更新"""
        if not HAS_REQUESTS:
            self._log_status("错误: 需要安装 requests 库")
            return None

        url = self.config['version_check_url']
        retries = self.config['max_retries']
        delay = self.config['retry_delay_seconds']
        timeout = self.config['timeout_seconds']

        headers = {}
        github_token = self.config.get('github_token')
        if github_token:
            headers['Authorization'] = f'token {github_token}'

        for attempt in range(retries):
            try:
                self._log_status(f"正在检查更新... (尝试 {attempt + 1}/{retries})")
                response = requests.get(url, headers=headers, timeout=timeout, verify=self.config['verify_ssl'])
                response.raise_for_status()

                data = response.json()
                remote_version = self._parse_version_response(data)
                
                if remote_version is None:
                    self._log_status("未找到有效的更新信息")
                    return None

                self._log_status(f"本地版本: {self.local_version}, 云端版本: {remote_version.version}")

                comparison = self._compare_versions(self.local_version, remote_version.version)

                if comparison < 0:
                    self._log_status(f"发现新版本: {remote_version.version}")
                    return remote_version
                else:
                    self._log_status("当前已是最新版本")
                    return None

            except requests.exceptions.RequestException as e:
                self._log_status(f"网络请求失败: {str(e)}")
                if attempt < retries - 1:
                    time.sleep(delay)
                    continue
                raise NetworkError(f"无法获取版本信息: {str(e)}")

    def _parse_version_response(self, data: Dict[str, Any]) -> Optional[VersionInfo]:
        """解析版本响应，支持标准格式和GitHub API格式"""
        if 'tag_name' in data:
            return self._parse_github_response(data)
        elif 'version' in data and 'download_url' in data:
            return VersionInfo.from_dict(data)
        else:
            return None

    def _parse_github_response(self, data: Dict[str, Any]) -> VersionInfo:
        """解析GitHub Releases API响应"""
        tag_name = data.get('tag_name', 'v0.0.0').lstrip('v')
        download_url = ''
        size = 0
        checksum = ''

        assets = data.get('assets', [])
        for asset in assets:
            if asset.get('name', '').endswith('.zip'):
                download_url = asset.get('browser_download_url', '')
                size = asset.get('size', 0)
                break

        release_notes = data.get('body', '')

        return VersionInfo(
            version=tag_name,
            download_url=download_url,
            checksum=checksum,
            checksum_type='sha256',
            size=size,
            release_notes=release_notes
        )

    def download_update(self, version_info: VersionInfo) -> str:
        """下载更新包，支持断点续传"""
        if not HAS_REQUESTS:
            raise UpdateError("需要安装 requests 库")

        url = version_info.download_url
        download_dir = self.config['download_dir']
        chunk_size = self.config['chunk_size_bytes']
        timeout = self.config['timeout_seconds']
        retries = self.config['max_retries']
        delay = self.config['retry_delay_seconds']

        os.makedirs(download_dir, exist_ok=True)

        filename = os.path.basename(url)
        if not filename:
            filename = f"update_{version_info.version}.zip"
        temp_filename = filename + '.tmp'
        file_path = os.path.join(download_dir, filename)
        temp_file_path = os.path.join(download_dir, temp_filename)

        downloaded_size = 0
        if os.path.exists(temp_file_path):
            downloaded_size = os.path.getsize(temp_file_path)
            self._log_status(f"检测到已下载 {downloaded_size} 字节，尝试断点续传")

        headers = {}
        if downloaded_size > 0:
            headers['Range'] = f'bytes={downloaded_size}-'

        for attempt in range(retries):
            try:
                self._log_status(f"开始下载更新包... (尝试 {attempt + 1}/{retries})")

                response = requests.get(
                    url,
                    headers=headers,
                    stream=True,
                    timeout=timeout,
                    verify=self.config['verify_ssl']
                )
                response.raise_for_status()

                total_size = int(response.headers.get('content-length', 0))
                if total_size == 0 and version_info.size > 0:
                    total_size = version_info.size
                if headers:
                    total_size += downloaded_size

                mode = 'ab' if downloaded_size > 0 else 'wb'

                with open(temp_file_path, mode) as f:
                    start_time = time.time()
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if self._stop_event.is_set():
                            raise DownloadError("下载已被取消")

                        f.write(chunk)
                        downloaded_size += len(chunk)

                        elapsed = time.time() - start_time
                        speed = downloaded_size / elapsed / 1024 / 1024 if elapsed > 0 else 0
                        status = f"下载中... {downloaded_size / 1024 / 1024:.2f}MB / {total_size / 1024 / 1024:.2f}MB ({speed:.2f}MB/s)"

                        if total_size > 0:
                            progress = int(downloaded_size / total_size * 100)
                            self._report_progress(progress, 100, status)
                        else:
                            self._report_progress(0, 100, status)

                        self._log_status(status)

                if os.path.exists(temp_file_path):
                    shutil.move(temp_file_path, file_path)

                self._log_status("更新包下载完成")
                return file_path

            except requests.exceptions.RequestException as e:
                self._log_status(f"下载失败: {str(e)}")
                if attempt < retries - 1:
                    time.sleep(delay)
                    continue
                raise DownloadError(f"下载失败: {str(e)}")

    def validate_update(self, file_path: str, version_info: VersionInfo) -> bool:
        """验证更新包完整性"""
        if not os.path.exists(file_path):
            raise ValidationError("更新包文件不存在")

        self._log_status("开始验证更新包完整性...")

        file_size = os.path.getsize(file_path)
        if version_info.size > 0 and file_size != version_info.size:
            raise ValidationError(f"文件大小不匹配: 期望 {version_info.size} 字节, 实际 {file_size} 字节")

        hash_type = version_info.checksum_type
        if hash_type == 'sha256':
            hasher = hashlib.sha256()
        elif hash_type == 'md5':
            hasher = hashlib.md5()
        else:
            raise ValidationError(f"不支持的校验类型: {hash_type}")

        chunk_size = 1024 * 1024
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(chunk_size), b''):
                hasher.update(chunk)

        calculated_checksum = hasher.hexdigest()
        expected_checksum = version_info.checksum.lower()

        if calculated_checksum != expected_checksum:
            raise ValidationError(
                f"校验失败: 期望 {expected_checksum}, 实际 {calculated_checksum}"
            )

        self._log_status("更新包验证通过")
        return True

    def install_update(self, file_path: str, version_info: VersionInfo) -> bool:
        """安装更新并重启程序"""
        self._log_status("开始安装更新...")

        import zipfile
        if not zipfile.is_zipfile(file_path):
            raise InstallError("更新包不是有效的 ZIP 文件")

        install_dir = os.path.dirname(sys.executable)
        backup_dir = os.path.join(install_dir, 'backup')

        try:
            os.makedirs(backup_dir, exist_ok=True)

            with zipfile.ZipFile(file_path, 'r') as zip_ref:
                members = zip_ref.namelist()
                total_files = len(members)
                extracted_files = 0

                for member in members:
                    if self._stop_event.is_set():
                        raise InstallError("安装已被取消")

                    if member.endswith('/'):
                        continue

                    target_path = os.path.join(install_dir, member)
                    target_dir = os.path.dirname(target_path)
                    os.makedirs(target_dir, exist_ok=True)

                    try:
                        with zip_ref.open(member) as source, open(target_path, 'wb') as target:
                            shutil.copyfileobj(source, target)
                    except PermissionError:
                        pass

                    extracted_files += 1
                    progress = int(extracted_files / total_files * 100)
                    status = f"安装中... {extracted_files}/{total_files} 文件"
                    self._report_progress(progress, 100, status)
                    self._log_status(status)

            version_file = os.path.join(install_dir, self.config['version_file'])
            version_data = {
                'version': version_info.version,
                'installed_at': datetime.now().isoformat(),
                'release_notes': version_info.release_notes
            }
            with open(version_file, 'w', encoding='utf-8') as f:
                json.dump(version_data, f, indent=2)

            self._log_status("更新安装完成")

            if self.config['auto_restart']:
                self.restart_application()

            return True

        except Exception as e:
            raise InstallError(f"安装失败: {str(e)}")

    def restart_application(self):
        """重启应用程序"""
        self._log_status("准备重启应用程序...")

        python = sys.executable
        script = sys.argv[0]
        args = sys.argv[1:]

        try:
            if sys.platform == 'win32':
                subprocess.Popen([python, script] + args, creationflags=subprocess.CREATE_NEW_CONSOLE)
            else:
                subprocess.Popen([python, script] + args)

            sys.exit(0)
        except Exception as e:
            self._log_status(f"重启失败: {str(e)}")

    def run_update(self, version_info: Optional[VersionInfo] = None) -> bool:
        """执行完整更新流程"""
        with self.update_lock:
            if self.is_updating:
                self._log_status("更新正在进行中")
                return False

            self.is_updating = True
            self._stop_event.clear()

            try:
                if version_info is None:
                    version_info = self.check_for_update()

                if version_info is None:
                    return False

                file_path = self.download_update(version_info)

                self.validate_update(file_path, version_info)

                self.install_update(file_path, version_info)

                return True

            except UpdateError as e:
                self._log_status(f"更新失败: {str(e)}")
                return False
            finally:
                self.is_updating = False

    def start_scheduler(self):
        """启动定时检查更新"""
        if self._scheduler_thread and self._scheduler_thread.is_alive():
            self._log_status("定时检查已在运行")
            return

        self._stop_event.clear()
        self._scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
        self._scheduler_thread.start()
        self._log_status("定时检查已启动")

    def stop_scheduler(self):
        """停止定时检查更新"""
        self._stop_event.set()
        if self._scheduler_thread:
            self._scheduler_thread.join(timeout=5)
        self._log_status("定时检查已停止")

    def _scheduler_loop(self):
        """定时检查循环"""
        interval_seconds = self.config['check_interval_hours'] * 3600

        while not self._stop_event.is_set():
            try:
                self.run_update()
            except Exception as e:
                self._log_status(f"定时检查异常: {str(e)}")

            if not self._stop_event.is_set():
                self._log_status(f"下次检查将在 {self.config['check_interval_hours']} 小时后")
                self._stop_event.wait(interval_seconds)

    def shutdown(self):
        """关闭更新器"""
        self.stop_scheduler()


if __name__ == '__main__':
    def progress_callback(current: int, total: int, status: str):
        print(f"\r进度: {current}% - {status}", end='')

    def status_callback(message: str):
        print(f"\n[状态] {message}")

    updater = AutoUpdater({
        'check_interval_hours': 1,
        'version_check_url': 'http://localhost:5000/api/update/check',
        'download_dir': './updates',
        'version_file': 'version.json',
        'auto_install': True,
        'auto_restart': False
    })

    updater.set_progress_callback(progress_callback)
    updater.set_status_callback(status_callback)

    print("开始手动检查更新...")
    try:
        success = updater.run_update()
        if success:
            print("\n更新完成!")
        else:
            print("\n无需更新或更新失败")
    except Exception as e:
        print(f"\n错误: {e}")