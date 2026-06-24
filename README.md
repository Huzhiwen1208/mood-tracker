# 我的心情记录

记录当下，留住每一天的小确幸 —— 一个部署在 GitHub Pages 上的个人心情记录网站，使用 GitHub Actions 进行数据同步，零服务器成本，安全私密。

## 功能

- 发送心情：输入文字 + 心情标签
- 撤销：仅最新一条（24小时内）可撤销
- 本地存储：无需部署也能用，云端：同步到 GitHub Actions 永久保存
- 加密存储：数据加密后保存在仓库中，隐私安全
- 极简设计：响应式布局，适配手机/桌面
- 操作日志：每次同步都会记录在仓库中

## 部署步骤

### 1. 准备 GitHub 仓库

1. 在 GitHub 上创建一个新仓库（建议设为私有或公开均可）
2. 将本项目代码推送到你的仓库

```bash
cd mood-tracker
git add .
git commit -m "init mood tracker"
git branch -M main
git remote add origin https://github.com/你的用户名/你的仓库名.git
git push -u origin main
```

### 2. 配置仓库设置

#### 2.1 启用 GitHub Pages

1. 进入仓库 Settings -> Pages
2. Source: Deploy from a branch (默认)
3. Branch: main / root
4. 保存，稍后部署好后就能访问 `https://你的用户名.github.io/仓库名`

#### 2.2 添加加密密钥

1. 进入仓库 Settings -> Secrets and variables -> Actions
2. 添加一个名为 `MOOD_PASSWORD` 的 Secret，值为你想设定的密码（建议用长一点）

#### 2.3 配置同步脚本中的密码

编辑 `index.html` 和 `sync-data.js`，把两处的 `demo-secret-key-change-me` 替换为你刚才在 Secrets 中设置的密码

#### 2.4 编辑 `index.html` 的 repo 字段

```javascript
const CONFIG = {
  repo: '你的用户名/你的仓库名', // 例如: 'jackhu/my-mood'
  password: '你的密码'
};
```

保存并提交推送到 GitHub

### 3. 使用方法

#### 本地预览
```bash
cd mood-tracker
# 使用任意静态服务器，例如
npx serve .
# 然后打开浏览器 http://localhost:8080
```

#### 发送心情

1. 在本地编辑完心情，点击发送，先保存在本地
2. 打开你的 GitHub 仓库 -> Actions -> Sync Mood Data -> Run workflow
3. 选择操作类型：send
4. 填入心情内容与标签，点击运行
5. 运行完成后，数据会自动提交到仓库的 `data/moods.json` 中，GitHub Pages 会自动部署更新

#### 撤销心情

1. 本地点击撤销，然后去 Actions 选择 undo 运行即可（必须在24小时内操作）

## 目录结构

```
.
├── .github
│   └── workflows
│       └── sync.yml     # GitHub Actions 同步配置
├── data/                  # 加密后的数据存放目录
│   ├── moods.json     # 加密后的心情数据
│   └── actions.log    # 操作日志
├── index.html          # 个人主页
├── sync-data.js       # 同步脚本
└── README.md
```

## 技术架构

```
GitHub Pages    -> 前端展示
GitHub Actions -> 后端同步数据写入
data/moods.json -> 加密后的存储
```

## 安全说明

数据使用简单的 XOR + Base64 加密，对于个人使用足够安全，但请注意保管好你的 `MOOD_PASSWORD`。

## 许可证

MIT
