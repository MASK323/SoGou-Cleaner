# 搜狗输入法 去广告/去推广/去遥测 清理工具

单文件 Python 脚本，标准库实现，**无需编译器、无第三方依赖**。
所有改动前先备份，可一键还原。

---

## 快速开始（推荐）

**双击 `搜狗清理.bat`** → 弹出 UAC 授权窗口，点「是」 → 出现操作菜单 → 按数字选择。

全程只需要按数字，**不需要输入任何命令**。

```
请选择要执行的操作:
  [1] 一键清理      执行全部 12 个项目 (推荐)
  [2] 自定义选择    自己挑要清理哪些项目
  [3] 预演          只列出会做什么, 不修改任何东西
  [4] 还原          从备份恢复之前的所有改动
  [0] 退出
```

建议**第一次先选 [3] 预演**，确认会改哪些东西再执行清理。

启动器会自动检测管理员权限（不足则弹 UAC 自提权）、自动定位 `py` / `python`，
并在结束时暂停窗口。

---

## 命令行用法（可选，供脚本化调用）

```bash
python sogou_cleaner.py                 # 交互菜单
python sogou_cleaner.py --all           # 执行全部
python sogou_cleaner.py --remove ads ai hosts
python sogou_cleaner.py --dry-run       # 预演全部，不修改
python sogou_cleaner.py --restore       # 还原
python sogou_cleaner.py --list          # 列出项目
```

其他参数：`--install-dir DIR`、`--backup-root DIR`、`--yes`、
`--block-dict-domains`（同时拦截词库域名，会导致无法更新词库）。

非管理员运行时脚本会**自动弹 UAC 提权**并带上原有参数。

---

## 清理项目

| 项目 | 内容 |
|---|---|
| `ads` | 广告/推广弹窗程序：SGTool、SogouCloud、SGSmartAssistant、SGIGuideHelper、sgfeedbackhelper、SGWangzai、SGBizLauncher、SGDownload、SGWizard |
| `update` | 升级程序 PinyinUp.exe + 禁用 SogouSvc 服务（**词库更新域名不受影响**） |
| `crash` | 崩溃上报程序 crashrpt.exe |
| `ai` | AI 助手浏览器（CEF，约 116MB）+ 网页渲染器 |
| `telemetry` | 遥测上报 DLL：shiply / beacon_sdk / qimei / Sogoulog |
| `components` | 营销组件目录 + 组件显示开关 |
| `login` | 登录/账户痕迹 |
| `mall` | 商城/无用设置页入口 + 商城 Web 应用（资源级，实验性） |
| `hosts` | 域名拦截（24 个广告/遥测/账户域名） |
| `track` | 追踪/状态注册表键 |
| `logs` | 日志/缓存清理 |
| `startup` | 自启动项与计划任务 |

**处理方式**：推广程序替换为 1024 字节空壳（启动即退出）并加 ACL 拒写锁，
防止被自动重建；配置与痕迹同理清空后锁定。

---

## 备份与还原

- 备份目录：`C:\SogouDebloatBackup\<时间戳>\`（files / dirs / reg 三类）
- 清单：`C:\SogouDebloatBackup\manifest.jsonl`，逐条记录每个改动及其备份路径
- 还原：菜单选 **[4]**，或 `python sogou_cleaner.py --restore`
  （按清单倒序还原，hosts 段移除，注册表从 .reg 导入）

---

## 验证清理结果

```bash
python verify_cleanup.py
```

逐项检查：推广程序是否已空壳化并锁定、**核心输入法文件是否完好**、
hosts 拦截段、进程与服务状态、配置锁定状态。

---

## 已知限制

1. **HKCU 注册表删除是临时的**。运行中的输入法会在几分钟内重建
   `HKCU\Software\SogouInput.user` 和 `.store.user`（前者只剩首次加载时间戳，
   后者是空的统计计数字键）。因为遥测域名已被 hosts 拦截，这些计数发不出去，
   但本地仍会重新累积。文件级改动和 hosts 拦截是永久的。
2. **`mall` 为实验性**：通过重写 `SGMyInput.exe` 内嵌资源包隐藏商城入口。
   脚本会先备份原文件，并在重写后校验长度一致才落盘；不一致则跳过。
3. 清理后如需升级搜狗输入法，建议先 `--restore` 还原，升级完成后再重新清理。
4. 空壳化的程序**只在被替换的位置生效**；若搜狗重新下载安装包修复自身，
   需要重新运行本工具。

---

## 旧版 PowerShell 版（无需 Python）

`legacy/` 下是早期实现，功能与 Python 版一致，**不需要安装 Python**，
系统自带的 Windows PowerShell 5.1 就能跑。

**双击 `legacy/搜狗清理-PowerShell版.bat`** 即可，用法与 Python 版完全相同。

也可手动运行：

```powershell
powershell -ExecutionPolicy Bypass -File sogou-debloat.ps1
powershell -ExecutionPolicy Bypass -File sogou-debloat.ps1 -DryRun -All
powershell -ExecutionPolicy Bypass -File sogou-debloat.ps1 -Restore
```


- 非管理员时**自动弹 UAC 提权重启**，并原样带上原有参数
- **每个退出路径都会暂停**等待回车：正常结束、取消、找不到安装目录、提权失败
- 加了 `trap` 兜底，未捕获的错误也会先显示出来再暂停
- `.bat` 用 `-ExecutionPolicy Bypass` 启动，并先 `Unblock-File` 解除网络来源标记
- 新增 `-NoPause` 开关，供脚本化调用时跳过暂停

**注意**：若机器上有组策略（GPO）强制指定执行策略，其优先级高于命令行参数，
`-ExecutionPolicy Bypass` 会失效。这种情况请改用 Python 版，或让管理员调整组策略。

---

## 文件说明

```
搜狗清理.bat                   双击入口：提权 + 定位 Python + 启动菜单 + 结束暂停
sogou_cleaner.py               主程序（单文件，标准库实现）
verify_cleanup.py              清理结果验证工具
README.md                      本文件
legacy/
  ├── 搜狗清理-PowerShell版.bat  旧版双击入口（无需 Python）
  └── sogou-debloat.ps1         早期 PowerShell 实现
```

运行环境：Windows 10/11，管理员权限。
Python 版需要 Python 3.8+；PowerShell 版只需要系统自带的 Windows PowerShell 5.1。
