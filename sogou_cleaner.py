#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sogou_cleaner.py — 搜狗输入法 去广告/去推广/去遥测/去AI 清理工具
=================================================================
单文件 Python 脚本, 无需编译器/无第三方依赖 (标准库实现)。

推荐用法 — 双击运行, 然后在菜单里选:
    双击 "搜狗清理.bat"   -> 自动请求管理员权限 -> 弹出操作菜单
    菜单选项: 1=一键清理  2=自定义选择  3=预演  4=还原  0=退出
    全程只需要按数字, 不需要输入任何命令。

命令行用法 (供脚本化/批量调用, 可选):
    交互菜单:      python sogou_cleaner.py
    执行全部:      python sogou_cleaner.py --all
    指定项目:      python sogou_cleaner.py --remove ads update ai hosts
    预演(不修改):  python sogou_cleaner.py --dry-run
    还原:          python sogou_cleaner.py --restore
    列出项目:      python sogou_cleaner.py --list
    非管理员运行时, 脚本会自动弹出 UAC 提权窗口。

可选参数:
    --install-dir DIR     手动指定搜狗安装目录
    --backup-root DIR     备份目录 (默认: <系统盘>:\\SogouDebloatBackup)
    --delete-ai-browser   删除AI浏览器时不备份 (省约116MB)
    --block-dict-domains  hosts 同时拦截词库更新域名 (会导致无法更新词库)
    --yes                 跳过确认提示

可选项目:
    ads         广告/推广弹窗进程 (SGTool/SogouCloud/旺仔/引导/反馈等)
    update      升级程序 + 升级服务 (词库更新默认保留)
    crash       崩溃上报程序
    ai          AI助手浏览器 (CEF, 约116MB) + 网页渲染器
    telemetry   遥测/上报 DLL (shiply/beacon/qimei/Sogoulog)
    components  营销组件目录 + 组件显示开关
    login       登录/账户痕迹
    mall        商城/无用设置页入口 + 商城Web应用
    hosts       广告/遥测/账户域名拦截
    track       追踪/状态注册表键
    logs        日志/缓存清理
    startup     自启动面清理 (Run键/计划任务)

需要管理员权限。所有改动前会备份, 可用 --restore 还原。
"""

import argparse
import base64
import ctypes
import ctypes.wintypes as wt
import io
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import time
import zipfile
from datetime import datetime
from pathlib import Path

# ============================================================================
# 内嵌空壳程序: 1024 字节原生 PE (x64/x86), 入口 xor eax,eax; ret, 无导入表
# 启动即退出, 无窗口/无网络/无行为, 用于替换被移除的推广程序
# ============================================================================
# 说明: 上面是占位; 实际数据在构建时由 build 生成(见 TVoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQRQAAZIYBAAAAAAAAAAAAAAAAAPAAIgALAgAAAAIAAAACAAAAAAAAABAAAAAQAAAAAABAAQAAAAAQAAAAAgAABgAAAAAAAAAGAAAAAAAAAAAgAAAAAgAAAAAAAAIAAAAAABAAAAAAAAAQAAAAAAAAAAAQAAAAAAAAEAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAudGV4dAAAAAABAAAAEAAAAAIAAAACAAAAAAAAAAAAAAAAAAAgAABgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAzwMMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==/TVoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQRQAATAEBAAAAAAAAAAAAAAAAAOAAAgELAQAAAAIAAAACAAAAAAAAABAAAAAQAAAAEAAAAABAAAAQAAAAAgAABgAAAAAAAAAGAAAAAAAAAAAgAAAAAgAAAAAAAAIAAAAAABAAABAAAAAAEAAAEAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAC50ZXh0AAAAAAEAAAAQAAAAAgAAAAIAAAAAAAAAAAAAAAAAACAAAGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAzwMMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA== 注入点)
STUB_X64_B64 = "TVoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQRQAAZIYBAAAAAAAAAAAAAAAAAPAAIgALAgAAAAIAAAACAAAAAAAAABAAAAAQAAAAAABAAQAAAAAQAAAAAgAABgAAAAAAAAAGAAAAAAAAAAAgAAAAAgAAAAAAAAIAAAAAABAAAAAAAAAQAAAAAAAAAAAQAAAAAAAAEAAAAAAAAAAAAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAudGV4dAAAAAABAAAAEAAAAAIAAAACAAAAAAAAAAAAAAAAAAAgAABgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAzwMMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="
STUB_X86_B64 = "TVoAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABQRQAATAEBAAAAAAAAAAAAAAAAAOAAAgELAQAAAAIAAAACAAAAAAAAABAAAAAQAAAAEAAAAABAAAAQAAAAAgAABgAAAAAAAAAGAAAAAAAAAAAgAAAAAgAAAAAAAAIAAAAAABAAABAAAAAAEAAAEAAAAAAAABAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAC50ZXh0AAAAAAEAAAAQAAAAAgAAAAIAAAAAAAAAAAAAAAAAACAAAGAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAzwMMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=="

# ============================================================================
# 配置区
# ============================================================================
ADS_EXES = [
    "SGTool.exe", "SogouCloud.exe", "SGSmartAssistant.exe", "SGIGuideHelper.exe",
    "sgfeedbackhelper.exe", "SGWangzai.exe", "SGBizLauncher.exe", "SGDownload.exe",
    "SGWizard.exe",
]
UPDATE_EXES = ["PinyinUp.exe"]
CRASH_EXES = ["crashrpt.exe"]
TELEMETRY_DLLS = [
    "shiply.dll", "beacon_sdk.dll", "beacon_sdk64.dll",
    "qimei.dll", "qimei64.dll", "Sogoulog.dll", "Sogoulog64.dll",
]
MARKETING_DIRS = [
    "biz_center", "game_center", "AppBox", "isgpet",
    "SogouFlash", "biz_pdf", "IChat", "systembeautify",
]
HOSTS_DOMAINS = [
    "account.sogou.com", "ie.sogou.com", "wan.sogou.com", "api.zhiyin.sogou.com",
    "master-proxy.shouji.sogou.com", "srv.android.shouji.sogou.com", "torrent.ie.sogou.com",
    "pro.cdn.ime.sogou.com", "ime.gtimg.com", "h5api.sginput.qq.com",
    "push-service-pc.sginput.qq.com", "sec.sginput.qq.com", "sj.qq.com",
    "snowflake.qq.com", "rdelivery.qq.com", "6ts.qq.com", "ts.qq.com",
    "oth.eve.mdt.qq.com", "trace.inlong.qq.com", "qqdata.ab.qq.com",
    "tqqdata.ab.qq.com", "beacon.qq.com", "report.beacon.qq.com",
    "galileotelemetry.tencent.com",
]
HOSTS_DICT_DOMAINS = ["pinyin.sogou.com", "get.sogou.com", "download.ime.sogou.com"]
TRACK_REGS = [
    r"HKCU\Software\SogouInput.ppup",
    r"HKCU\Software\SogouInput.tc",
    r"HKCU\Software\SogouInput\KernelReport",
    r"HKCU\Software\SogouInput\LongConn",
    r"HKCU\Software\kdiskmgr_sogou",
    r"HKCU\Software\kwallpaper_sogou",
    r"HKCU\Software\kzip_sogou",
]
LOGIN_REGS = [
    r"HKCU\Software\SogouInput.user",
    r"HKCU\Software\SogouInput.store.user",
]
MALL_NAV_HIDE = [
    "cmpx_nav_person", "cmpx_nav_skincenter", "cmpx_nav_crossdevice",
    "cmpx_nav_custom", "cmpx_nav_recommend",
]
MALL_PAGES = [
    "personpage.xml", "customServicePage.xml", "smartServicePage.xml",
    "crossDevicePage.xml", "set/setrecommend.xml", "set/setaccountpage.xml",
    "skincenterpage.xml",
]
ITEMS = {
    "ads":        "广告/推广弹窗进程",
    "update":     "升级程序 + 升级服务",
    "crash":      "崩溃上报程序",
    "ai":         "AI助手浏览器(约116MB) + 渲染器",
    "telemetry":  "遥测/上报 DLL",
    "components": "营销组件目录 + 显示开关",
    "login":      "登录/账户痕迹",
    "mall":       "商城/无用设置页入口 + 商城Web应用",
    "hosts":      "域名拦截 (保留词库更新)",
    "track":      "追踪/状态注册表键",
    "logs":       "日志/缓存清理",
    "startup":    "自启动面清理",
}

# ============================================================================
# 终端输出
# ============================================================================
class C:
    G = "\033[32m"; Y = "\033[33m"; R = "\033[31m"
    C_ = "\033[36m"; M = "\033[35m"; D = "\033[90m"; X = "\033[0m"

def _no_color():
    return not sys.stdout.isatty() or os.environ.get("NO_COLOR")

def cprint(msg, color=""):
    if _no_color() or not color:
        print(msg)
    else:
        print(color + msg + C.X)

def ok(m):   cprint("    [完成] " + m, C.G)
def skip(m): cprint("    [跳过] " + m, C.D)
def plan(m): cprint("    [计划] " + m, C.Y)
def warn(m): cprint("    [注意] " + m, C.M)
def hdr(m):  print(); cprint("== " + m, C.C_)

# ============================================================================
# 管理员权限
# ============================================================================
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

def require_admin():
    """非管理员时自动弹 UAC 提权重启, 免去手敲命令"""
    if is_admin():
        return
    script = os.path.abspath(__file__)
    cprint("需要管理员权限, 正在请求提权 (请在弹窗中点击[是])...", C.Y)
    extra = " ".join('"%s"' % a for a in sys.argv[1:])
    params = '"%s"%s' % (script, (" " + extra) if extra else "")
    rc = 0
    try:
        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, params, os.path.dirname(script), 1)
    except Exception as e:
        warn("提权调用失败: %s" % e)
    if rc > 32:
        cprint("已在新的管理员窗口继续运行, 本窗口关闭。", C.G)
        sys.exit(0)
    cprint("提权被取消或失败。", C.R)
    cprint("  也可手动: 右键 %s -> 以管理员身份运行"
           % os.path.basename(script), C.Y)
    sys.exit(1)

# ============================================================================
# 备份 / 清单
# ============================================================================
class Session:
    def __init__(self, backup_root, dry_run=False):
        self.dry_run = dry_run
        self.records = []
        if dry_run:
            self.dir = None
            self.manifest = None
            return
        root = backup_root or os.path.join(os.environ.get("SystemDrive", "C:") + "\\", "SogouDebloatBackup")
        self.dir = os.path.join(root, datetime.now().strftime("%Y%m%d-%H%M%S"))
        os.makedirs(os.path.join(self.dir, "files"), exist_ok=True)
        os.makedirs(os.path.join(self.dir, "dirs"), exist_ok=True)
        os.makedirs(os.path.join(self.dir, "reg"), exist_ok=True)
        self.manifest = os.path.join(root, "manifest.jsonl")

    def record(self, action, target, backup=None):
        rec = {"t": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
               "action": action, "target": target, "backup": backup}
        self.records.append(rec)
        if self.manifest:
            try:
                os.makedirs(os.path.dirname(self.manifest), exist_ok=True)
                with open(self.manifest, "a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            except Exception as e:
                warn("写清单失败: %s" % e)

    def backup_path(self, path, kind="files"):
        name = os.path.basename(path)
        dest = os.path.join(self.dir, kind, name)
        i = 1
        while os.path.exists(dest):
            dest = os.path.join(self.dir, kind, "%s.%d" % (name, i))
            i += 1
        return dest

    def backup_move(self, path):
        """移动(而非复制)到备份区 - 用于删除类操作"""
        kind = "dirs" if os.path.isdir(path) else "files"
        dest = self.backup_path(path, kind)
        shutil.move(path, dest)
        return dest

# ============================================================================
# ACL / 空壳 工具 (ctypes 直接调用 icacls, 避免命令行闪烁)
# ============================================================================
def run_quiet(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True, timeout=30)
    except Exception:
        return None

def acl_deny(path, spec):
    run_quiet('icacls "%s" /deny *S-1-1-0:%s' % (path, spec))

def acl_remove_deny(path):
    run_quiet('icacls "%s" /remove:d *S-1-1-0' % path)

def stub_bytes():
    b64 = STUB_X64_B64
    if not (os.environ.get("PROCESSOR_ARCHITECTURE", "").endswith("64")
            or os.environ.get("PROCESSOR_ARCHITEW6432")):
        b64 = STUB_X86_B64
    return base64.b64decode(b64)

def stub_file_path():
    suffix = "x64" if (os.environ.get("PROCESSOR_ARCHITECTURE", "").endswith("64")
                       or os.environ.get("PROCESSOR_ARCHITEW6432")) else "x86"
    p = os.path.join(os.environ.get("TEMP", "."), "sgd_stub_%s.exe" % suffix)
    if not os.path.exists(p):
        with open(p, "wb") as f:
            f.write(stub_bytes())
    return p

def kill_exe(exe_name):
    base = os.path.splitext(exe_name)[0]
    run_quiet('taskkill /F /IM %s >nul 2>&1' % exe_name)
    # 兜底: 按进程名
    run_quiet('taskkill /F /IM %s >nul 2>&1' % (base + ".exe"))

def is_stub(path):
    try:
        return os.path.getsize(path) <= 2048
    except OSError:
        return False

def is_locked(path):
    """DENY ACE 生效时连读取都会被拒, 以此判定对象已锁定"""
    try:
        if os.path.isdir(path):
            next(iter(os.scandir(path)), None)
        else:
            with open(path, "rb") as f:
                f.read(1)
        return False
    except PermissionError:
        return True
    except OSError:
        return False

# ============================================================================
# 核心操作
# ============================================================================
def op_stub_file(sess, path):
    """把 exe 替换为 1KB 空壳 + 锁写保护"""
    if not os.path.isfile(path):
        skip("不存在: " + os.path.basename(path)); return
    if is_stub(path):
        skip("已是空壳: " + os.path.basename(path)); return
    if sess.dry_run:
        plan("将空壳化+锁定: " + path); return
    kill_exe(os.path.basename(path))
    acl_remove_deny(path)
    try:
        dest = sess.backup_move(path)
    except Exception as e:
        warn("备份失败(%s), 跳过: %s" % (e, os.path.basename(path))); return
    shutil.copy2(stub_file_path(), path)
    acl_deny(path, "(D,W)")
    sess.record("stub", path, dest)
    ok("已空壳化+锁定: " + os.path.basename(path))

def op_move_out(sess, path):
    """移出文件(备份)"""
    if not os.path.isfile(path):
        skip("不存在: " + os.path.basename(path)); return
    if sess.dry_run:
        plan("将移出(备份): " + path); return
    acl_remove_deny(path)
    dest = sess.backup_move(path)
    sess.record("move", path, dest)
    ok("已移出: " + os.path.basename(path))

def dir_write_locked(path):
    """目录是否已写入锁定: 锁定的目录仍可列目录, 但无法在其中新建文件"""
    probe = os.path.join(path, ".sgd_lockprobe")
    try:
        open(probe, "w").close()
    except PermissionError:
        return True
    except OSError:
        return False
    try:
        os.remove(probe)
    except OSError:
        pass
    return False

def op_clear_lock(sess, path):
    """清空目录内容 + 锁写保护(防重建)"""
    if not os.path.isdir(path):
        skip("不存在: " + os.path.basename(path)); return
    if not any(os.scandir(path)) and dir_write_locked(path):
        skip("已清空+锁定: " + os.path.basename(path)); return
    if sess.dry_run:
        plan("将清空+锁定: " + path); return
    acl_remove_deny(path)
    has_content = any(os.scandir(path))
    dest = None
    if has_content:
        dest = sess.backup_move(path)
        os.makedirs(path, exist_ok=True)
    else:
        os.makedirs(path, exist_ok=True)
    acl_deny(path, "(DE,WD,AD,DC)")
    sess.record("clear", path, dest)
    ok("已清空+锁定: " + os.path.basename(path))

def op_clear_only(sess, path):
    """只清空(可重建的缓存类)"""
    if not os.path.isdir(path):
        skip("不存在: " + os.path.basename(path)); return
    if sess.dry_run:
        plan("将清空: " + path); return
    err = 0
    for entry in os.scandir(path):
        try:
            if entry.is_dir(follow_symlinks=False):
                shutil.rmtree(entry.path, ignore_errors=True)
            else:
                os.remove(entry.path)
        except Exception:
            err += 1
    sess.record("clearonly", path, None)
    ok("已清空: " + os.path.basename(path) + ((" (%d 项被占用跳过)" % err) if err else ""))

def op_truncate_lock(sess, path):
    """清空文件内容 + 锁写"""
    if not os.path.isfile(path):
        skip("不存在: " + os.path.basename(path)); return
    if os.path.getsize(path) == 0 and is_locked(path):
        skip("已清空+锁定: " + os.path.basename(path)); return
    if sess.dry_run:
        plan("将清空+锁定: " + path); return
    acl_remove_deny(path)
    dest = sess.backup_move(path)
    open(path, "wb").close()
    acl_deny(path, "(D,W)")
    sess.record("stub", path, dest)
    ok("已清空+锁定: " + os.path.basename(path))

def op_reg_delete(sess, key):
    """导出注册表后删除"""
    import winreg
    hive_map = {"HKCU": winreg.HKEY_CURRENT_USER, "HKLM": winreg.HKEY_LOCAL_MACHINE}
    parts = key.split("\\", 1)
    if len(parts) != 2 or parts[0] not in hive_map:
        skip("不支持的键: " + key); return
    try:
        winreg.OpenKey(hive_map[parts[0]], parts[1])
    except OSError:
        skip("注册表键不存在: " + key); return
    if sess.dry_run:
        plan("将导出并删除: " + key); return
    safe = key.replace(":", "_").replace("\\", "_")
    bak = os.path.join(sess.dir, "reg", safe + ".reg")
    run_quiet('reg export "%s" "%s" /y >nul 2>&1' % (key, bak))
    # 递归删除
    def del_tree(root_hive, sub):
        try:
            with winreg.OpenKey(root_hive, sub, 0, winreg.KEY_ALL_ACCESS) as k:
                while True:
                    try:
                        child = winreg.EnumKey(k, 0)
                    except OSError:
                        break
                    del_tree(root_hive, sub + "\\" + child)
        except OSError:
            pass
        try:
            winreg.DeleteKey(root_hive, sub)
        except OSError:
            pass
    del_tree(hive_map[parts[0]], parts[1])
    sess.record("regdel", key, bak)
    ok("已删除(已导出备份): " + key)

# ============================================================================
# 安装目录探测
# ============================================================================
def find_sogou(install_dir=None):
    cands = []
    if install_dir:
        cands.append(install_dir)
    drive = os.environ.get("SystemDrive", "C:") + "\\"
    for p in [os.path.join(drive, "搜狗输入法", "SogouInput"),
              os.path.join(drive, "Program Files", "SogouInput"),
              os.path.join(drive, "Program Files (x86)", "SogouInput")]:
        cands.append(p)
    # 注册表卸载信息
    try:
        import winreg
        for root, sub in [(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                          (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")]:
            try:
                k = winreg.OpenKey(root, sub)
                for i in range(winreg.QueryInfoKey(k)[0]):
                    try:
                        sk = winreg.EnumKey(k, i)
                        with winreg.OpenKey(k, sk) as skk:
                            try:
                                name = winreg.QueryValueEx(skk, "DisplayName")[0]
                                loc = winreg.QueryValueEx(skk, "InstallLocation")[0]
                                if name and re.search(r"搜狗|Sogou", str(name)) and loc:
                                    cands.append(str(loc))
                            except OSError:
                                pass
                    except OSError:
                        pass
            except OSError:
                pass
    except Exception:
        pass
    seen = set()
    for c in cands:
        c = c.rstrip("\\")
        if not c or c in seen:
            continue
        seen.add(c)
        if not os.path.isdir(c):
            continue
        vdirs = [d for d in os.listdir(c) if re.match(r"^\d+\.\d+", d)
                 and os.path.isdir(os.path.join(c, d))]
        if vdirs:
            vdirs.sort(reverse=True)
            return {"root": c, "ver": os.path.join(c, vdirs[0])}
    return None

def py_dir():
    return os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "LocalLow", "SogouPY")

# ============================================================================
# 各项目实现
# ============================================================================
def do_ads(sess, R):
    for n in ADS_EXES:
        op_stub_file(sess, os.path.join(R["ver"], n))

def do_update(sess, R):
    for n in UPDATE_EXES:
        op_stub_file(sess, os.path.join(R["ver"], n))
    r = run_quiet('sc query SogouSvc')
    if not (r and b"SogouSvc" in (r.stdout or b"")):
        skip("服务 SogouSvc 不存在")
        cprint("    提示: 词库更新域名在 hosts 白名单中, 不受升级清理影响", C.D)
        return
    old = "auto"
    r2 = run_quiet('sc qc SogouSvc')
    if r2 and r2.stdout:
        m = re.search(rb"START_TYPE\s*:\s*\d+\s+(\w+)", r2.stdout)
        if m:
            old = m.group(1).decode().lower()
    if old == "disabled":
        skip("服务 SogouSvc 已禁用")
    elif sess.dry_run:
        plan("将禁用服务 SogouSvc")
    else:
        run_quiet('sc stop SogouSvc >nul 2>&1')
        run_quiet('sc config SogouSvc start= disabled >nul 2>&1')
        sess.record("svc", "SogouSvc", old)
        ok("已禁用服务 SogouSvc (原启动类型: %s)" % old)
    cprint("    提示: 词库更新域名在 hosts 白名单中, 不受升级清理影响", C.D)

def do_crash(sess, R):
    for n in CRASH_EXES:
        op_stub_file(sess, os.path.join(R["ver"], n))
        op_stub_file(sess, os.path.join(R["root"], "Components", n))

def do_ai(sess, R, delete_browser=False):
    browser = os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"),
                           "SGAIAssistant", "Browser")
    if os.path.isfile(os.path.join(browser, "libcef.dll")):
        if sess.dry_run:
            plan("将移除 AI 浏览器组件: %s (约116MB)" % browser)
        elif delete_browser:
            acl_remove_deny(browser)
            shutil.rmtree(browser, ignore_errors=True)
            os.makedirs(browser, exist_ok=True)
            acl_deny(browser, "(DE,WD,AD,DC)")
            sess.record("clear", browser, None)
            ok("已删除 AI 浏览器组件 (未备份)")
        else:
            op_clear_lock(sess, browser)
    else:
        skip("AI 浏览器组件不存在")
    op_move_out(sess, os.path.join(R["ver"], "SGWebRender.exe"))

def do_telemetry(sess, R):
    for n in TELEMETRY_DLLS:
        op_move_out(sess, os.path.join(R["ver"], n))

def do_components(sess, R):
    for d in MARKETING_DIRS:
        op_clear_lock(sess, os.path.join(R["root"], "Components", d))
    # 组件显示开关
    cfg = os.path.join(py_dir(), "Components", "ComponentConfig.ini")
    if not os.path.isfile(cfg):
        skip("ComponentConfig.ini 不存在"); return
    if sess.dry_run:
        # 锁定时连读取都被拒, 直接视为已完成
        if is_locked(cfg):
            skip("组件开关已锁定(视为已关闭)")
        else:
            plan("将关闭组件开关: " + cfg)
        return
    try:
        acl_remove_deny(cfg)  # 必须先解锁: 上锁后连读取都会被拒
        with open(cfg, "rb") as f:
            raw = f.read()
        txt = raw.decode("utf-16-le", errors="ignore")
        if re.search(r"IChatCom\s*=\s*0", txt) and re.search(r"ISGPetCom\s*=\s*0", txt):
            acl_deny(cfg, "(D,W)")
            skip("组件开关已是关闭状态"); return
        dest = sess.backup_move(cfg)
        new = "[Active]\r\nIChatCom=0\r\nISGPetCom=0\r\nPicFaceCom=1\r\nSystemBeautifyCom=0\r\n"
        with open(cfg, "wb") as f:
            f.write(b"\xff\xfe" + new.encode("utf-16-le"))
        acl_deny(cfg, "(D,W)")
        sess.record("stub", cfg, dest)
        ok("已关闭 IChat/旺仔/系统美化 组件开关并锁定")
    except Exception as e:
        warn("组件开关处理失败: %s" % e)

def do_login(sess, R):
    op_clear_lock(sess, os.path.join(R["ver"], "ThirdPassportIcon"))
    op_clear_lock(sess, os.path.join(py_dir(), "ThirdPassportIcon"))
    op_truncate_lock(sess, os.path.join(py_dir(), "FastPassport.ini"))
    op_truncate_lock(sess, os.path.join(py_dir(), "ThirdPassport.ini"))
    for k in LOGIN_REGS:
        op_reg_delete(sess, k)

def do_hosts(sess, block_dict=False):
    hosts = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                         "System32", "drivers", "etc", "hosts")
    domains = list(HOSTS_DOMAINS)
    if block_dict:
        domains += HOSTS_DICT_DOMAINS
    try:
        with open(hosts, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        warn("无法读取 hosts: %s" % e); return
    if "sogou-debloat-start" in content:
        skip("hosts 拦截已存在")
    else:
        if sess.dry_run:
            plan("将写入 %d 个域名拦截到 hosts" % len(domains))
        else:
            bak = os.path.join(sess.dir, "hosts.bak")
            shutil.copy2(hosts, bak)
            block = "\r\n# sogou-debloat-start\r\n"
            block += "".join("0.0.0.0 %s\r\n" % d for d in domains)
            block += "# sogou-debloat-end\r\n"
            with open(hosts, "a", encoding="ascii") as f:
                f.write(block)
            sess.record("hosts", hosts, bak)
            ok("已写入 hosts 拦截 (%d 个域名)" % len(domains))
    if not sess.dry_run:
        run_quiet("ipconfig /flushdns >nul 2>&1")

def do_track(sess, R):
    for k in TRACK_REGS:
        op_reg_delete(sess, k)

def do_logs(sess, R):
    p = py_dir()
    for d in ["LOG", "logs", "Temp", "SGCefCache"]:
        op_clear_only(sess, os.path.join(p, d))
    op_clear_lock(sess, os.path.join(p, "Popup"))
    op_clear_lock(sess, os.path.join(p, "Components", "SmartInfo"))
    op_truncate_lock(sess, os.path.join(p, "Components", "SuggList.ini"))
    pd = os.path.join(os.environ.get("ProgramData", r"C:\ProgramData"), "SogouInput")
    for d in ["SGSysToast", "SGBizConfig", "ShiplyUpdate"]:
        op_clear_only(sess, os.path.join(pd, d))
    # 日志目录里的具体文件(若目录被锁清不掉)
    logdir = os.path.join(p, "LOG")
    if os.path.isdir(logdir):
        op_clear_only(sess, logdir)

def do_startup(sess, R):
    import winreg
    run_keys = [
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", "HKCU"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run", "HKLM"),
    ]
    found = False
    for hive, sub, tag in run_keys:
        try:
            with winreg.OpenKey(hive, sub, 0, winreg.KEY_ALL_ACCESS) as k:
                n_sub = winreg.QueryInfoKey(k)[1]
                targets = []
                for i in range(n_sub):
                    try:
                        name, val, _ = winreg.EnumValue(k, i)
                        if val and re.search(r"Sogou|sogou|SGAI|SGMyInput", str(val)):
                            targets.append((name, str(val)))
                    except OSError:
                        pass
                for name, val in targets:
                    found = True
                    if sess.dry_run:
                        plan("将移除自启动: %s\\%s = %s" % (tag, name, val)); continue
                    bak = os.path.join(sess.dir, "reg", "run_%s_%s.reg" % (tag, name))
                    run_quiet('reg export "%s\\%s" "%s" /y >nul 2>&1' % (tag, sub, bak))
                    winreg.DeleteValue(k, name)
                    sess.record("regdel", "%s\\%s\\%s" % (tag, sub, name), bak)
                    ok("已移除自启动: " + name)
        except OSError:
            pass
    if not found:
        skip("Run 键中无搜狗自启动项")
    # 计划任务
    r = run_quiet('schtasks /query /fo csv')
    tasks = []
    if r and r.stdout:
        txt = r.stdout.decode("gbk", errors="ignore")
        for line in txt.splitlines():
            if re.search(r"sogou|SGAI", line, re.I):
                name = line.split(",")[0].strip('"')
                if name and name not in tasks:
                    tasks.append(name)
    if tasks:
        for name in tasks:
            if sess.dry_run:
                plan("将删除计划任务: " + name); continue
            run_quiet('schtasks /delete /tn "%s" /f >nul 2>&1' % name)
            sess.record("task", name, None)
            ok("已删除计划任务: " + name)
    else:
        skip("无搜狗相关计划任务")

# ---------------------------------------------------------------- mall (实验)
def _patch_nav(text):
    """只给目标 Option 自身加 visible=false (不动父级, 避免错位)"""
    for name in MALL_NAV_HIDE:
        pat = r'(<Option(?![^>]*visible=)[^>]*name="%s")' % re.escape(name)
        text = re.sub(pat, r'\1 visible="false"', text, count=1)
    # 智能服务: 包装层带 name
    text = re.sub(r'(<VBoxOption(?![^>]*visible=)[^>]*name="cmpx_nav_smart_layout")',
                  r'\1 visible="false"', text, count=1)
    return text

def _patch_page(text):
    """页面隐藏: 有 VerticalLayout 的加 visible=false; Window 型(如 skincenterpage)则移除内部 include 使其为空"""
    if re.search(r'<VerticalLayout', text):
        return re.sub(r'(?s)<VerticalLayout(?![^>]*visible=)', '<VerticalLayout visible="false"',
                      text, count=1)
    # Window 型: 移除 include source=... (商城页靠 include 加载皮肤中心)
    out = re.sub(r'(?s)<include\s+source="[^"]*"\s*/?>', '<!-- removed -->', text)
    return out

def _iter_zip_candidates(data):
    """遍历所有 EOCD, 反推包起点; yield (start, end)"""
    eocd = b"PK\x05\x06"
    pos = 0
    while True:
        i = data.find(eocd, pos)
        if i < 0:
            return
        if i + 22 <= len(data):
            cd_size = struct.unpack_from("<I", data, i + 12)[0]
            cd_off = struct.unpack_from("<I", data, i + 16)[0]
            cmt = struct.unpack_from("<H", data, i + 20)[0]
            if cmt <= 512:
                start = i - cd_size - cd_off
                if 0 <= start < i:
                    yield (start, i)
        pos = i + 1

def do_mall(sess, R):
    exe = os.path.join(R["ver"], "SGMyInput.exe")
    if not os.path.isfile(exe):
        skip("SGMyInput.exe 不存在"); return
    if sess.dry_run:
        plan("将尝试隐藏商城/无用设置页入口 (资源级, 实验性)"); return

    bak = sess.backup_path(exe)
    shutil.copy2(exe, bak)

    with open(exe, "rb") as f:
        data = bytearray(f.read())

    patched = 0
    for start, end in list(_iter_zip_candidates(bytes(data))):
        if bytes(data[start:start + 4]) != b"PK\x03\x04":
            continue
        cmt = struct.unpack_from("<H", data, end + 20)[0]
        zip_len = end + 22 + cmt - start
        if zip_len <= 0 or start + zip_len > len(data):
            continue
        try:
            zf = zipfile.ZipFile(io.BytesIO(bytes(data[start:start + zip_len])))
        except Exception:
            continue
        names = zf.namelist()
        if "cmxp_nav_menu.xml" not in names:
            zf.close(); continue
        nav = zf.read("cmxp_nav_menu.xml").decode("utf-8", errors="ignore")
        if 'visible="false"' in nav:
            skip("商城入口已是隐藏状态"); zf.close(); continue

        print("    发现布局资源包 @0x%X (%d 字节), 打包修改中..." % (start, zip_len))
        entries = []
        for info in zf.infolist():
            if info.is_dir():
                entries.append((info.filename, None))
                continue
            raw = zf.read(info.filename)
            if info.filename == "cmxp_nav_menu.xml":
                raw = _patch_nav(raw.decode("utf-8", errors="ignore")).encode("utf-8")
            elif info.filename in MALL_PAGES:
                raw = _patch_page(raw.decode("utf-8", errors="ignore")).encode("utf-8")
            entries.append((info.filename, raw))
        zf.close()

        # 迭代重建到原始大小
        new_zip = None
        pad = 0
        for _ in range(8):
            buf = io.BytesIO()
            with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zo:
                for name, raw in entries:
                    if raw is None:
                        zo.writestr(zipfile.ZipInfo(name), b"")
                    else:
                        zo.writestr(name, raw)
                if pad > 0:
                    zi = zipfile.ZipInfo("zz_padding.bin")
                    zi.compress_type = zipfile.ZIP_STORED
                    zo.writestr(zi, b"\x00" * pad)
            got = len(buf.getvalue())
            if got == zip_len:
                new_zip = buf.getvalue(); break
            if got > zip_len:
                over = got - zip_len
                if pad < over:
                    break
                pad -= over
            else:
                pad += zip_len - got
        if new_zip is None:
            warn("资源包无法精确重建 (需 %d 字节), 跳过此包" % zip_len); continue
        data[start:start + zip_len] = new_zip
        patched += 1

    # 顺带清空商城 Web 应用包 (104包: index.html + 主JS)
    for start2, end2 in list(_iter_zip_candidates(bytes(data))):
        if bytes(data[start2:start2 + 4]) != b"PK\x03\x04":
            continue
        cmt2 = struct.unpack_from("<H", data, end2 + 20)[0]
        zl2 = end2 + 22 + cmt2 - start2
        if zl2 <= 0 or start2 + zl2 > len(data):
            continue
        try:
            zf2 = zipfile.ZipFile(io.BytesIO(bytes(data[start2:start2 + zl2])))
        except Exception:
            continue
        names2 = zf2.namelist()
        if "index.html" not in names2:
            zf2.close(); continue
        idx_html = zf2.read("index.html")
        if len(idx_html) < 200:
            skip("商城 Web 应用已是清空状态"); zf2.close(); continue
        print("    发现商城Web应用 @0x%X, 清空入口中..." % start2)
        entries2 = []
        for info in zf2.infolist():
            if info.is_dir():
                entries2.append((info.filename, None)); continue
            raw = zf2.read(info.filename)
            if info.filename == "index.html":
                raw = b"<html><head></head><body></body></html>\n"
            elif info.filename.endswith(".js") and b"react" not in raw[:200].lower() and len(raw) > 100000:
                raw = b"/* removed */\n"
            entries2.append((info.filename, raw))
        zf2.close()
        new2 = None
        pad2 = 0
        for _ in range(8):
            buf2 = io.BytesIO()
            with zipfile.ZipFile(buf2, "w", zipfile.ZIP_DEFLATED) as zo2:
                for name2, raw2 in entries2:
                    if raw2 is None:
                        zo2.writestr(zipfile.ZipInfo(name2), b"")
                    else:
                        zo2.writestr(name2, raw2)
                if pad2 > 0:
                    zi2 = zipfile.ZipInfo("zz_padding.bin")
                    zi2.compress_type = zipfile.ZIP_STORED
                    zo2.writestr(zi2, b"\x00" * pad2)
            got2 = len(buf2.getvalue())
            if got2 == zl2:
                new2 = buf2.getvalue(); break
            if got2 > zl2:
                over2 = got2 - zl2
                if pad2 < over2: break
                pad2 -= over2
            else:
                pad2 += zl2 - got2
        if new2:
            data[start2:start2 + zl2] = new2
            patched += 1
            print("    商城Web应用已清空")

    if patched == 0:
        skip("未发现可修补的资源包 (版本可能不同)")
        return
    with open(exe, "wb") as f:
        f.write(bytes(data))
    # PE 完整性验证: 用 LoadLibraryEx LOAD_LIBRARY_AS_IMAGE_RESOURCE
    try:
        LOAD_IMAGE = 0x20
        h = ctypes.windll.kernel32.LoadLibraryExW(ctypes.c_wchar_p(exe), None, LOAD_IMAGE)
        if not h:
            shutil.copy2(bak, exe)
            warn("补丁后 PE 验证失败, 已自动回滚!")
            return
    except Exception:
        pass
    sess.record("mall", exe, bak)
    ok("已隐藏商城/无用设置页入口 (%d 个资源包), PE 验证通过" % patched)

# ============================================================================
# 还原
# ============================================================================
def do_restore(backup_root=None):
    import winreg
    root = backup_root or os.path.join(os.environ.get("SystemDrive", "C:") + "\\", "SogouDebloatBackup")
    mf = os.path.join(root, "manifest.jsonl")
    if not os.path.isfile(mf):
        warn("未找到备份清单: " + mf); return
    cprint("从备份还原: " + mf, C.C_)
    with open(mf, "r", encoding="utf-8") as f:
        lines = [l for l in f if l.strip()]
    for line in reversed(lines):
        try:
            r = json.loads(line)
        except Exception:
            continue
        act, tgt, bak = r.get("action"), r.get("target"), r.get("backup")
        if act in ("stub", "move", "clear"):
            if bak and os.path.exists(bak):
                acl_remove_deny(tgt)
                if os.path.exists(tgt):
                    if os.path.isdir(tgt):
                        shutil.rmtree(tgt, ignore_errors=True)
                    else:
                        try: os.remove(tgt)
                        except OSError: pass
                shutil.move(bak, tgt)
                ok("已还原: " + os.path.basename(tgt))
            else:
                acl_remove_deny(tgt)
                ok("已解除锁定: " + os.path.basename(tgt))
        elif act == "hosts":
            hosts = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"),
                                 "System32", "drivers", "etc", "hosts")
            try:
                with open(hosts, "r", encoding="utf-8", errors="ignore") as f:
                    txt = f.read()
                txt = re.sub(r"(?ms)\r?\n?# sogou-debloat-start.*?# sogou-debloat-end\r?\n?",
                             "\r\n", txt)
                with open(hosts, "w", encoding="ascii", errors="ignore") as f:
                    f.write(txt)
                run_quiet("ipconfig /flushdns >nul 2>&1")
                ok("已移除 hosts 拦截段")
            except Exception as e:
                warn("hosts 还原失败: %s" % e)
        elif act == "regdel":
            if bak and os.path.exists(bak):
                run_quiet('reg import "%s" >nul 2>&1' % bak)
                ok("已还原注册表: " + tgt)
        elif act == "svc":
            st = (bak or "auto").lower()
            run_quiet('sc config %s start= %s >nul 2>&1' % (tgt, st))
            ok("已还原服务启动类型: %s -> %s" % (tgt, st))
        elif act == "task":
            skip("计划任务需手动恢复: " + str(tgt))
    cprint("还原完成。建议重启相关应用/输入法。", C.G)

# ============================================================================
# 菜单 / 参数
# ============================================================================
def interactive_select():
    keys = list(ITEMS.keys())
    print()
    cprint("可选项目:", C.C_)
    for i, k in enumerate(keys, 1):
        print("  [%2d] %-11s %s" % (i, k, ITEMS[k]))
    print()
    print("  all = 全部   none = 取消")
    ans = input("请输入编号 (逗号分隔, 支持 1,3,5-8): ").strip().lower()
    if ans in ("", "none", "n"):
        return []
    if ans == "all":
        return list(keys)
    sel = []
    for part in ans.split(","):
        part = part.strip()
        m = re.match(r"^(\d+)\s*-\s*(\d+)$", part)
        if m:
            for j in range(int(m.group(1)), int(m.group(2)) + 1):
                if 1 <= j <= len(keys):
                    sel.append(keys[j - 1])
        elif part.isdigit():
            j = int(part)
            if 1 <= j <= len(keys):
                sel.append(keys[j - 1])
        elif part in ITEMS:
            sel.append(part)
    seen = []
    for k in sel:
        if k not in seen:
            seen.append(k)
    return seen

def interactive_menu(backup_root=""):
    """顶层菜单: 直接运行脚本时使用, 无需记任何命令行参数。
    返回 (动作, 预演标志):
      动作 = None 表示退出, "restore" 表示还原, 否则为项目列表。"""
    while True:
        print()
        cprint("请选择要执行的操作:", C.C_)
        print("  [1] 一键清理      执行全部 %d 个项目 (推荐)" % len(ITEMS))
        print("  [2] 自定义选择    自己挑要清理哪些项目")
        print("  [3] 预演          只列出会做什么, 不修改任何东西")
        print("  [4] 还原          从备份恢复之前的所有改动")
        print("  [0] 退出")
        print()
        ans = input("请输入编号: ").strip().lower()
        if ans in ("", "0", "q", "quit", "exit"):
            return None, False
        if ans == "1":
            return list(ITEMS), False
        if ans == "2":
            sel = interactive_select()
            if sel:
                return sel, False
            cprint("未选择任何项目, 返回主菜单。", C.Y)
            continue
        if ans == "3":
            return list(ITEMS), True
        if ans == "4":
            mf = os.path.join(backup_root or os.path.join(
                os.environ.get("SystemDrive", "C:") + "\\", "SogouDebloatBackup"),
                "manifest.jsonl")
            if not os.path.isfile(mf):
                warn("没有找到备份清单, 无法还原: %s" % mf)
                continue
            print()
            cprint("将从备份还原: " + mf, C.Y)
            go = input("确认还原? 此操作会把清理过的文件恢复原状 (y/N): ").strip().lower()
            if go == "y":
                return "restore", False
            continue
        warn("无效输入, 请重新选择")

def main():
    ap = argparse.ArgumentParser(
        description="搜狗输入法 去广告/去推广/去遥测 清理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n  python sogou_cleaner.py\n  python sogou_cleaner.py --all\n"
               "  python sogou_cleaner.py --remove ads ai hosts\n"
               "  python sogou_cleaner.py --restore")
    ap.add_argument("--remove", nargs="*", default=[], metavar="ITEM",
                    help="要执行的清理项目 (空格分隔)")
    ap.add_argument("--all", action="store_true", help="执行全部项目")
    ap.add_argument("--dry-run", action="store_true", help="只报告不修改")
    ap.add_argument("--restore", action="store_true", help="从备份还原")
    ap.add_argument("--list", action="store_true", help="列出可选项目")
    ap.add_argument("--install-dir", default="", help="手动指定安装目录")
    ap.add_argument("--backup-root", default="", help="备份目录")
    ap.add_argument("--delete-ai-browser", action="store_true", help="删除AI浏览器时不备份")
    ap.add_argument("--block-dict-domains", action="store_true", help="同时拦截词库域名")
    ap.add_argument("--yes", action="store_true", help="跳过确认")
    args = ap.parse_args()

    if args.list:
        for k, v in ITEMS.items():
            print("  %-12s %s" % (k, v))
        return

    print()
    cprint("=" * 62, C.C_)
    cprint("  搜狗输入法 去广告/去推广/去遥测 清理工具 v1.0 (Python)", C.C_)
    cprint("=" * 62, C.C_)

    require_admin()

    if args.restore:
        do_restore(args.backup_root)
        return

    R = find_sogou(args.install_dir)
    if not R:
        warn("未找到搜狗输入法安装目录。可用 --install-dir 手动指定。")
        sys.exit(1)
    print("安装目录: " + R["root"])
    print("当前版本: " + os.path.basename(R["ver"]))
    # 选项: 命令行参数优先; 无参数则进入交互菜单
    if args.all:
        sel = list(ITEMS)
    elif args.remove:
        sel = []
        flat = []
        for token in args.remove:
            flat.extend(re.split(r"[,\s]+", token))
        for t in flat:
            t = t.strip().lower()
            if not t:
                continue
            if t in ITEMS and t not in sel:
                sel.append(t)
            elif t.isdigit():
                keys = list(ITEMS)
                j = int(t)
                if 1 <= j <= len(keys) and keys[j - 1] not in sel:
                    sel.append(keys[j - 1])
            else:
                warn("未知项目: " + t)
    elif args.dry_run:
        sel = list(ITEMS)          # 单独 --dry-run 即预演全部
    else:
        action, dry = interactive_menu(args.backup_root)
        if action is None:
            print("已退出"); return
        if action == "restore":
            do_restore(args.backup_root)
            return
        sel = action
        if dry:
            args.dry_run = True
            cprint("\n将预演以下项目 (不做任何修改): " + ", ".join(sel), C.Y)
        else:
            cprint("\n将执行: " + ", ".join(sel), C.Y)
            if not args.yes:
                go = input("确认执行? (y/N): ").strip().lower()
                if go != "y":
                    print("已取消"); return

    if not sel:
        print("未选择任何项目"); return

    if args.dry_run:
        cprint("[预演模式] 只报告不修改", C.Y)

    # 会话
    sess = Session(args.backup_root, dry_run=args.dry_run)
    if not args.dry_run:
        cprint("备份目录: " + sess.dir, C.G)

    dispatch = {
        "ads":        lambda: do_ads(sess, R),
        "update":     lambda: do_update(sess, R),
        "crash":      lambda: do_crash(sess, R),
        "ai":         lambda: do_ai(sess, R, args.delete_ai_browser),
        "telemetry":  lambda: do_telemetry(sess, R),
        "components": lambda: do_components(sess, R),
        "login":      lambda: do_login(sess, R),
        "mall":       lambda: do_mall(sess, R),
        "hosts":      lambda: do_hosts(sess, args.block_dict_domains),
        "track":      lambda: do_track(sess, R),
        "logs":       lambda: do_logs(sess, R),
        "startup":    lambda: do_startup(sess, R),
    }
    for k in sel:
        hdr("%s — %s" % (k, ITEMS[k]))
        try:
            dispatch[k]()
        except Exception as e:
            warn("项目 %s 执行出错: %s" % (k, e))

    print()
    cprint("=" * 62, C.C_)
    if args.dry_run:
        cprint("预演完成 (未做任何修改)", C.Y)
    else:
        cprint("执行完成", C.G)
        cprint("备份与清单: " + os.path.dirname(sess.dir), C.G)
        cprint("还原: python %s --restore" % os.path.basename(__file__), C.G)
        cprint("建议重启相关应用/输入法使改动生效", C.D)

if __name__ == "__main__":
    main()
