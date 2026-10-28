# 发布清单与操作步骤

本文件用于把 `policy-tool-extractor/` 发布成一个独立的 GitHub 仓库。
**所有命令由你本人执行**；本目录内的文件已经准备好，无需再改动内容。

---

## 一、推荐仓库信息

| 字段 | 建议值 |
|---|---|
| 仓库名 | `policy-tool-extractor` |
| 描述（Description） | 省级数字政府政策文本的政策工具提取：Rothwell & Zegveld 三分法 + 关键词词典 + 可复现统计 |
| 可见性 | Public（学术工具，公开便于复现） |
| Topics | `policy-analysis`、`digital-government`、`text-analysis`、`computational-social-science`、`china` |
| 默认分支 | `main` |
| 初始化选项 | **不要**勾选 "Add a README" / ".gitignore" / "license"（本目录已有） |

---

## 二、发布前检查清单

已完成的检查：

- [x] 目录结构符合 `README / data / docs / code / output`
- [x] 主编码样本 4 份，附录 2 份已隔离到 `data/appendix/`
- [x] `data/metadata.csv` 路径为仓库内相对路径
- [x] 三个脚本串行跑通（提取 → 信度 → 报告）
- [x] 敏感串扫描：token / 密码 / 密钥 **0 命中**
- [x] `output/` 含 4 个 csv + 1 个 html，无大文件、无图表依赖
- [x] LICENSE（MIT）、CITATION.cff、.gitignore 已就位
- [x] 最大文件：`data/raw/四川…正文.txt` 约 87 KB，远低于 GitHub 100 MB 限制

推送前建议本地自检一次（约 2 秒）：

```powershell
python code/extractor.py --binary
python code/report.py
```

看到 `output/report.html` 生成即说明环境正常。

你可以在推送前再确认一次文件清单：

```powershell
Get-ChildItem -Recurse -File | Sort-Object Length -Descending |
  Select-Object -First 5 Name, Length
```

---

## 三、方式 A：网页建仓 + 本地推送（推荐）

### 步骤 1：在 GitHub 网页创建空仓库

1. 打开 <https://github.com/new>
2. Repository name 填 `policy-tool-extractor`
3. 选 **Public**
4. **不要**勾选 README / .gitignore / license
5. 点 **Create repository**

### 步骤 2：本地初始化并推送

在 PowerShell 里执行（把路径换成你实际的位置）：

```powershell
cd C:\Users\baro\Documents\deepseek-harness\default-workspace\batch_output\repo_staging\policy-tool-extractor

git init -b main
git add .
git commit -m "feat: 数字政府政策工具提取器 v1.0.0

- 4 份省级数字政府文件主编码样本（广东/辽宁/浙江/四川）
- 附录材料与文献题录（不纳入编码）
- Rothwell & Zegveld 三分法编码手册（14 个二级子工具）
- 关键词提取器（仅标准库，输出词次与篇次两种口径）

"
git remote add origin https://github.com/barohency-cyber/policy-tool-extractor.git
git push -u origin main
```

### 步骤 3：认证

推送时会要求输入用户名与密码：

- Username：你的 GitHub 用户名
- Password：**粘贴 Personal Access Token**（不是账号密码）

Token 需要 `Contents: Read and write` 权限。若之前那个 token 只有读权限，去
<https://github.com/settings/personal-access-tokens> 修改。

---

## 四、方式 B：本机 git 的 SSL 问题（这台机器已知）

这台机器的 Windows Schannel 栈有问题，`git push` 可能报：

```
schannel: AcquireCredentialsHandle failed: SEC_E_NO_CREDENTIALS
```

解决办法：强制使用 OpenSSL 后端，二选一：

```powershell
# 单次生效
git -c http.sslBackend=openssl push -u origin main

# 写入本仓库配置（推荐，只影响这个仓库）
git config http.sslBackend openssl
git push -u origin main
```

若报 `Could not connect to server` 或超时，说明网络到 `github.com:443` 不稳定；
可稍后重试，或改用代理：

```powershell
git config http.proxy http://127.0.0.1:7890   # 换成你的代理端口
```

---

## 五、推送后的收尾

1. 在仓库页面确认文件树与 `README.md` 渲染正常
2. About 区域填入 Description 与 Topics（见第一节）
3. 可选：Settings → Releases → 创建 `v1.0.0` 标签
4. 可选：把 `CITATION.cff` 的 author 改成你的真实姓名与 ORCID

---

## 六、注意事项

1. **不要把 token 写进 remote URL**（如 `https://token@github.com/...`），
   它会永久留在 `.git/config` 里；用 Credential Manager 或每次手动输入更安全。
2. **政策文本的版权**归原发布机关，仓库中已注明仅用于学术研究、不转授。
   如果担心合规，可以只发布 `code/`、`docs/` 与 `data/metadata.csv`，
   把 `data/raw/*.txt` 替换成来源 URL 清单（metadata 里已有）。
3. `output/` 里的两份 csv 是**示例结果**，不是必须提交；若要精简仓库可以删除，
   运行 `python code/extractor.py` 即可重新生成。
4. 若仓库要用于论文投稿，建议同时打一个 Zenodo DOI，并在 README 顶部加徽章。
