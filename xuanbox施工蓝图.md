可以。现在这份《xuanbox设计说明.md》已经把**最终产品形态**定下来了，核心定位是“自托管、加密、跨端友好的个人资料保险库”，包含照片、文件、票据、证件、XuanDrop 快传、安全分享、备份和后台管理等完整模块。
接下来这份就是 **XuanBox 开发蓝图 V1.0**，重点是：**怎么从零开发、怎么分模块、怎么设计数据库、怎么做前端样式、怎么让 PC 和移动端都好用。**

---

# XuanBox 玄匣

## 私有加密个人资料系统开发蓝图 V1.0

## 1. 项目开发总原则

XuanBox 不能按普通网盘、普通 NAS 前端、普通后台管理系统来开发。

开发时必须坚持这几个原则：

```text
1. 先建立安全骨架，再开发业务功能。
2. 所有用户数据必须 owner_id 隔离。
3. 所有文件必须通过后端鉴权访问。
4. 上传文件从第一天开始就按加密存储设计。
5. PC 端和移动端同时设计，不做后期补丁式适配。
6. XuanDrop 快传作为核心模块开发，不作为附属小功能。
7. 管理后台只管理系统，不直接浏览用户隐私内容。
8. 所有模块都要支持后期迁移到独立 NAS / Mini PC。
```

---

# 2. 推荐技术栈

## 2.1 后端

```text
Python 3.11+
FastAPI
SQLAlchemy 2.x
Alembic
PostgreSQL
Redis
Pydantic
python-jose / PyJWT
passlib + bcrypt 或 argon2-cffi
cryptography
Pillow
python-multipart
aiofiles
```

后端定位：

```text
身份认证
权限校验
加密 / 解密
文件流式上传下载
照片缩略图
票据 OCR 任务
XuanDrop 快传
审计日志
后台管理
备份任务
```

---

## 2.2 前端

```text
Vue 3
Vite
Pinia
Vue Router
Axios
Element Plus 或 Naive UI
PWA 插件
QR Code 组件
图片预览组件
拖拽上传组件
虚拟滚动组件
```

我建议优先用：

```text
Vue 3 + Vite + Pinia + Naive UI
```

原因：

```text
Naive UI 更现代
移动端适配比 Element Plus 更轻
视觉上更容易做出“私有保险库”的高级感
适合暗色 / 浅色主题切换
```

如果你想延续之前 Vue 项目经验，也可以用 Element Plus。
但 XuanBox 更偏产品化，我更推荐 Naive UI。

---

## 2.3 部署

```text
Docker Compose
PostgreSQL 容器
Redis 容器
FastAPI 容器
Vue build 后由 Caddy / Nginx 托管
Cloudflare Tunnel
/data/xuanbox 作为统一数据目录
```

---

# 3. 项目目录结构

## 3.1 总目录

```text
xuanbox/
  backend/
  frontend/
  docker/
  docs/
  scripts/
  data/
    storage/
    backups/
    logs/
  docker-compose.yml
  .env.example
  README.md
```

---

## 3.2 后端目录

```text
backend/
  app/
    main.py

    core/
      config.py
      database.py
      security.py
      dependencies.py
      permissions.py
      constants.py
      logging.py

    api/
      v1/
        auth.py
        users.py
        invites.py
        devices.py
        files.py
        folders.py
        photos.py
        albums.py
        receipts.py
        documents.py
        tags.py
        shares.py
        drop.py
        trash.py
        search.py
        admin.py
        backup.py
        health.py

    models/
      user.py
      invite.py
      device.py
      file_asset.py
      folder.py
      photo_asset.py
      album.py
      receipt.py
      document_asset.py
      tag.py
      share.py
      transfer.py
      audit_log.py
      backup_job.py
      system_setting.py

    schemas/
      auth.py
      user.py
      invite.py
      device.py
      file_asset.py
      photo.py
      album.py
      receipt.py
      document.py
      tag.py
      share.py
      drop.py
      admin.py
      common.py

    services/
      auth_service.py
      user_service.py
      invite_service.py
      device_service.py
      encryption_service.py
      storage_service.py
      file_service.py
      folder_service.py
      photo_service.py
      thumbnail_service.py
      album_service.py
      receipt_service.py
      document_service.py
      ocr_service.py
      tag_service.py
      share_service.py
      drop_service.py
      search_service.py
      trash_service.py
      audit_service.py
      backup_service.py
      admin_service.py

    workers/
      worker_main.py
      thumbnail_worker.py
      ocr_worker.py
      cleanup_worker.py
      backup_worker.py

    utils/
      file_type.py
      hash.py
      time.py
      image.py
      qr.py
      zip.py

  alembic/
  tests/
  requirements.txt
  Dockerfile
```

---

## 3.3 前端目录

```text
frontend/
  src/
    main.js
    App.vue

    router/
      index.js

    stores/
      authStore.js
      userStore.js
      deviceStore.js
      uploadStore.js
      themeStore.js

    api/
      http.js
      authApi.js
      fileApi.js
      photoApi.js
      receiptApi.js
      dropApi.js
      adminApi.js
      shareApi.js

    layouts/
      DesktopLayout.vue
      MobileLayout.vue
      AuthLayout.vue
      AdminLayout.vue

    views/
      auth/
        LoginView.vue
        InviteRegisterView.vue

      dashboard/
        DashboardView.vue

      photos/
        PhotosTimelineView.vue
        AlbumsView.vue
        AlbumDetailView.vue
        PhotoPreviewView.vue

      files/
        FilesView.vue
        FolderView.vue

      receipts/
        ReceiptsView.vue
        ReceiptDetailView.vue
        ReceiptEditView.vue

      documents/
        DocumentsView.vue
        DocumentDetailView.vue

      drop/
        XuanDropView.vue
        DropReceiveView.vue
        DropSendView.vue

      shared/
        SharedView.vue
        PublicShareView.vue

      trash/
        TrashView.vue

      settings/
        SettingsView.vue
        DeviceSettingsView.vue
        SecuritySettingsView.vue

      admin/
        AdminDashboardView.vue
        AdminUsersView.vue
        AdminInvitesView.vue
        AdminStorageView.vue
        AdminAuditLogsView.vue
        AdminBackupView.vue

    components/
      common/
        AppLogo.vue
        AppHeader.vue
        AppSidebar.vue
        AppBottomNav.vue
        PageContainer.vue
        PageHeader.vue
        EmptyState.vue
        LoadingState.vue
        ConfirmDialog.vue
        ActionMenu.vue
        FloatingUploadButton.vue

      upload/
        UploadDropzone.vue
        UploadProgressPanel.vue
        MobileUploadSheet.vue

      files/
        FileGrid.vue
        FileList.vue
        FileCard.vue
        FileDetailDrawer.vue
        FolderBreadcrumb.vue

      photos/
        PhotoGrid.vue
        PhotoTimelineGroup.vue
        PhotoCard.vue
        PhotoPreviewModal.vue
        AlbumCard.vue

      receipts/
        ReceiptCard.vue
        ReceiptList.vue
        ReceiptForm.vue
        ReceiptFilterBar.vue

      drop/
        DeviceCard.vue
        QRReceiveBox.vue
        DropItemCard.vue
        DropSessionPanel.vue

      layout/
        DesktopSidebar.vue
        DesktopTopbar.vue
        MobileTopbar.vue
        MobileTabbar.vue

    styles/
      variables.css
      theme.css
      layout.css
      mobile.css
      components.css

  public/
  package.json
  vite.config.js
  Dockerfile
```

---

# 4. 数据库核心模型设计

## 4.1 users

```text
id
username
email
password_hash
display_name
avatar_file_id
role
status
storage_limit_bytes
created_at
updated_at
last_login_at
```

role：

```text
owner
admin
user
guest
```

status：

```text
active
disabled
locked
deleted
```

---

## 4.2 invites

```text
id
invite_code
created_by_user_id
role_to_assign
max_uses
used_count
expires_at
is_active
note
created_at
```

---

## 4.3 devices

```text
id
owner_id
device_name
device_type
os_name
browser_name
last_ip
last_seen_at
is_trusted
created_at
revoked_at
```

---

## 4.4 file_assets

这是所有文件的基础表。照片、票据、证件本质上都关联它。

```text
id
owner_id
folder_id
original_filename
display_name
mime_type
file_ext
file_size
sha256_hash
encrypted_path
encrypted_file_key
encryption_method
nonce
auth_tag
key_version
file_category
source
is_favorite
is_deleted
created_at
updated_at
deleted_at
```

file_category：

```text
photo
video
document
receipt
identity_document
drop_temp
archive
other
```

source：

```text
manual_upload
mobile_upload
xuan_drop
receipt_scan
system_import
```

---

## 4.5 folders

```text
id
owner_id
parent_id
name
path_cache
is_deleted
created_at
updated_at
deleted_at
```

---

## 4.6 photo_assets

```text
id
owner_id
file_id
taken_at
uploaded_at
width
height
camera_model
orientation
exif_json
location_lat_encrypted
location_lng_encrypted
location_text
thumbnail_file_id
preview_file_id
is_favorite
created_at
```

---

## 4.7 albums

```text
id
owner_id
title
description
cover_file_id
visibility
created_at
updated_at
```

## 4.8 album_photos

```text
id
album_id
photo_id
sort_order
created_at
```

---

## 4.9 receipts

```text
id
owner_id
file_id
vendor_name
purchase_date
total_amount
tax_amount
currency
category
payment_method
warranty_until
note
ocr_status
is_deleted
created_at
updated_at
deleted_at
```

---

## 4.10 documents

```text
id
owner_id
file_id
document_type
title
issuer
issued_date
expires_at
note
security_level
created_at
updated_at
```

---

## 4.11 tags

```text
id
owner_id
name
color
created_at
updated_at
```

## 4.12 tag_links

```text
id
owner_id
tag_id
target_type
target_id
created_at
```

target_type：

```text
file
photo
receipt
document
album
drop_item
```

---

## 4.13 shares

```text
id
owner_id
target_type
target_id
shared_with_user_id
public_token
permission
password_hash
max_downloads
download_count
expires_at
is_active
created_at
```

---

## 4.14 transfer_sessions

```text
id
owner_id
source_device_id
target_device_id
mode
status
expires_at
created_at
```

mode：

```text
temporary
archive
device_to_device
```

status：

```text
active
completed
expired
cancelled
```

---

## 4.15 transfer_items

```text
id
session_id
owner_id
file_id
original_filename
mime_type
file_size
status
expires_at
saved_to_library
created_at
```

---

## 4.16 audit_logs

```text
id
actor_user_id
action
target_type
target_id
ip_address
device_id
user_agent
metadata_json
created_at
```

---

## 4.17 backup_jobs

```text
id
job_type
status
backup_path
size_bytes
started_at
finished_at
error_message
metadata_json
created_at
```

---

# 5. 后端开发蓝图

## 5.1 基础系统

必须先完成：

```text
FastAPI 项目骨架
PostgreSQL 连接
Alembic 迁移
Redis 连接
统一响应格式
统一错误处理
统一日志
CORS 配置
.env 配置管理
Docker Compose
health check
```

统一响应格式：

```json
{
  "success": true,
  "data": {},
  "message": "ok"
}
```

错误格式：

```json
{
  "success": false,
  "error_code": "permission_denied",
  "message": "Permission denied"
}
```

---

## 5.2 认证系统

接口：

```text
POST /api/v1/auth/login
POST /api/v1/auth/logout
POST /api/v1/auth/refresh
GET  /api/v1/auth/me
POST /api/v1/auth/register-by-invite
POST /api/v1/auth/change-password
POST /api/v1/auth/logout-all-devices
```

实现重点：

```text
密码 hash
JWT access token
refresh token
设备记录
登录日志
失败限制
当前用户依赖 get_current_user
```

---

## 5.3 权限系统

核心依赖：

```text
get_current_user()
require_owner()
require_admin()
require_file_owner(file_id)
require_resource_access(target_type, target_id)
```

核心原则：

```text
所有资源查询默认带 owner_id
所有下载接口必须检查权限
所有预览接口必须检查权限
所有分享访问必须检查 token / password / expires_at
```

---

## 5.4 加密服务

文件加密服务必须独立出来。

```text
encryption_service.py
```

核心方法：

```text
generate_file_key()
encrypt_file_stream()
decrypt_file_stream()
wrap_file_key()
unwrap_file_key()
rotate_key()
```

推荐算法：

```text
AES-256-GCM
```

第一阶段采用服务器端可解密模式：

```text
主密钥来自 .env 或密钥文件
每个文件独立 file_key
file_key 被主密钥包装加密后入库
```

必须注意：

```text
主密钥不能写入数据库
主密钥不能提交 Git
.env 必须备份但不能明文乱放
```

---

## 5.5 存储服务

```text
storage_service.py
```

职责：

```text
生成真实存储路径
保存加密文件
读取加密文件
删除物理文件
计算文件大小
计算 hash
临时上传目录管理
```

路径规则：

```text
/data/xuanbox/storage/encrypted_files/{owner_id}/{year}/{month}/{file_id}.bin
```

---

## 5.6 文件服务

```text
file_service.py
```

功能：

```text
上传文件
列出文件
文件详情
下载文件
移动文件
重命名文件
收藏文件
删除文件
恢复文件
永久删除
```

接口：

```text
POST /api/v1/files/upload
GET  /api/v1/files
GET  /api/v1/files/{id}
GET  /api/v1/files/{id}/download
PATCH /api/v1/files/{id}
DELETE /api/v1/files/{id}
POST /api/v1/files/{id}/restore
DELETE /api/v1/files/{id}/purge
```

---

## 5.7 照片服务

```text
photo_service.py
thumbnail_service.py
```

功能：

```text
图片上传后自动识别为 photo
读取 EXIF
生成 thumbnail
生成 preview
照片时间线
照片详情
照片删除 / 恢复
照片收藏
```

接口：

```text
GET  /api/v1/photos
POST /api/v1/photos/upload
GET  /api/v1/photos/{id}
GET  /api/v1/photos/{id}/thumbnail
GET  /api/v1/photos/{id}/preview
GET  /api/v1/photos/{id}/original
PATCH /api/v1/photos/{id}
DELETE /api/v1/photos/{id}
```

注意：

```text
thumbnail 和 preview 也必须通过 API 返回
不能暴露静态路径
```

---

## 5.8 相册服务

接口：

```text
GET  /api/v1/albums
POST /api/v1/albums
GET  /api/v1/albums/{id}
PATCH /api/v1/albums/{id}
DELETE /api/v1/albums/{id}
POST /api/v1/albums/{id}/photos
DELETE /api/v1/albums/{id}/photos/{photo_id}
```

---

## 5.9 票据服务

接口：

```text
GET  /api/v1/receipts
POST /api/v1/receipts
POST /api/v1/receipts/upload
GET  /api/v1/receipts/{id}
PATCH /api/v1/receipts/{id}
DELETE /api/v1/receipts/{id}
POST /api/v1/receipts/{id}/ocr
```

功能：

```text
票据文件上传
结构化字段录入
分类筛选
金额筛选
日期筛选
保修期提醒
OCR 任务创建
```

---

## 5.10 XuanDrop 服务

这是核心体验模块，要认真做。

接口：

```text
GET  /api/v1/drop/devices
POST /api/v1/drop/session
GET  /api/v1/drop/session/{id}
GET  /api/v1/drop/qr-token
POST /api/v1/drop/upload
GET  /api/v1/drop/items
GET  /api/v1/drop/items/{id}/download
POST /api/v1/drop/items/{id}/save-to-library
DELETE /api/v1/drop/items/{id}
WS   /api/v1/drop/ws
```

功能：

```text
设备列表
创建快传会话
二维码 token
手机扫码上传
PC 实时接收
临时文件过期
保存到照片库
保存到文件库
保存到票据库
批量下载
```

二维码 token 规则：

```text
5 分钟过期
一次性使用
绑定 owner_id
绑定 target_device_id
绑定 session_id
```

---

## 5.11 分享服务

接口：

```text
POST /api/v1/shares
GET  /api/v1/shares
PATCH /api/v1/shares/{id}
DELETE /api/v1/shares/{id}
GET  /api/v1/public-share/{token}
POST /api/v1/public-share/{token}/verify-password
GET  /api/v1/public-share/{token}/download
```

分享必须支持：

```text
过期时间
密码
最大下载次数
取消分享
访问日志
```

---

## 5.12 搜索服务

```text
GET /api/v1/search?q=&type=&date_from=&date_to=&tag=
```

搜索范围：

```text
文件名
照片日期
票据商家
票据备注
标签
文档标题
OCR 文本
```

必须按 owner_id 限制。

---

## 5.13 管理后台 API

```text
GET /api/v1/admin/overview
GET /api/v1/admin/users
PATCH /api/v1/admin/users/{id}
GET /api/v1/admin/storage
GET /api/v1/admin/audit-logs
GET /api/v1/admin/backup-jobs
POST /api/v1/admin/backup/run
GET /api/v1/admin/health
```

注意：

```text
后台不能返回用户文件内容
只能返回统计信息
```

---

# 6. 前端开发蓝图

## 6.1 前端整体风格

XuanBox 前端不能像传统后台系统。

视觉关键词：

```text
深色高级
浅色清爽
卡片式
保险库感
科技感
柔和阴影
圆角
玻璃质感少量使用
移动端大按钮
PC 端信息密度适中
```

---

## 6.2 推荐主题色

主色：

```text
玄青蓝：#1E3A5F
深海蓝：#0F172A
安全绿：#10B981
强调紫：#7C3AED
背景浅灰：#F6F8FB
卡片白：#FFFFFF
暗色背景：#0B1020
暗色卡片：#151B2E
```

建议默认浅色，支持暗色。

---

## 6.3 字体

中文 / 英文都要清楚。

推荐：

```text
system-ui
-apple-system
BlinkMacSystemFont
Segoe UI
PingFang SC
Microsoft YaHei
Arial
sans-serif
```

---

## 6.4 圆角和阴影

```text
普通按钮：10px
卡片：16px
弹窗：20px
移动端底部弹窗：24px 24px 0 0
主卡片阴影：0 8px 24px rgba(15, 23, 42, 0.08)
暗色卡片边框：1px solid rgba(255,255,255,0.08)
```

---

## 6.5 PC 端布局

PC 端结构：

```text
左侧 Sidebar：240px
顶部 Topbar：64px
主内容区：自适应
右侧详情 Drawer：360px，可折叠
```

页面结构：

```text
DesktopLayout
  Sidebar
  Topbar
  MainContent
  DetailDrawer
```

Sidebar 菜单：

```text
Dashboard
Photos
Albums
Files
Receipts
Documents
XuanDrop
Favorites
Shared
Trash
Settings
Admin
```

Sidebar 风格：

```text
深色半磨砂背景
logo 在顶部
当前菜单高亮
每个菜单有 icon
底部显示当前用户头像和容量
```

---

## 6.6 移动端布局

移动端结构：

```text
顶部 MobileTopbar：56px
中间内容区
底部 Tabbar：64px
右下角 FloatingUploadButton
```

底部导航：

```text
Home
Photos
Files
Receipts
Drop
Me
```

移动端原则：

```text
不显示复杂 Sidebar
操作尽量放 bottom sheet
上传按钮始终明显
照片浏览支持滑动
文件操作支持长按
票据拍照入口必须醒目
```

---

# 7. 关键页面设计

## 7.1 登录页

风格：

```text
左侧品牌介绍
右侧登录卡片
移动端只显示登录卡片
背景使用深蓝渐变
Logo 使用 XuanBox / 玄匣
```

内容：

```text
账号
密码
登录按钮
邀请码注册入口
记住此设备
```

视觉：

```text
大标题：Your Private Digital Vault
副标题：Photos, files, receipts and documents. Securely stored in your own cloud.
```

---

## 7.2 Dashboard

PC 端布局：

```text
顶部：欢迎语 + 快捷上传按钮
第一行：容量卡片 / 照片数量 / 文件数量 / 票据数量
第二行：最近上传 / 最近快传
第三行：待处理票据 / 到期提醒 / 最近分享
```

移动端布局：

```text
用户问候
容量圆环
快捷按钮：上传照片 / 上传票据 / 快传
最近照片横向滚动
最近文件列表
```

卡片设计：

```text
白色卡片
16px 圆角
轻阴影
图标色块
数字大号字体
```

---

## 7.3 Photos 页面

PC 端：

```text
顶部工具栏：
时间筛选 / 相册筛选 / 标签筛选 / 上传按钮

主体：
按日期分组照片网格

右侧：
照片详情 Drawer
```

照片卡片：

```text
宽高比 1:1
圆角 12px
hover 显示勾选 / 收藏 / 更多
图片加载 skeleton
```

移动端：

```text
两列或三列瀑布网格
顶部月份筛选
点击进入全屏预览
左右滑动切换
```

---

## 7.4 Albums 页面

相册卡片：

```text
封面图
标题
照片数量
最后更新时间
右上角更多菜单
```

移动端：

```text
双列卡片
长按显示操作菜单
```

---

## 7.5 Files 页面

PC 端：

```text
顶部：
路径面包屑
搜索框
上传按钮
新建文件夹
视图切换

主体：
列表视图 / 网格视图

右侧：
文件详情
```

列表字段：

```text
名称
类型
大小
更新时间
标签
操作
```

移动端：

```text
文件夹优先
文件卡片
底部弹窗操作
```

---

## 7.6 Receipts 页面

PC 端：

```text
左侧：筛选栏
中间：票据列表 / 卡片
右侧：票据详情
```

筛选：

```text
分类
年份
金额范围
商家
保修状态
标签
```

票据卡片：

```text
商家名
金额
日期
分类图标
保修状态
OCR 状态
```

移动端：

```text
顶部搜索
分类横向 chip
票据卡片列表
右下角拍照上传按钮
```

票据详情页：

```text
左侧/顶部：票据图片或 PDF 预览
右侧/下方：结构化字段表单
保存按钮
OCR 按钮
标签
备注
```

---

## 7.7 Documents 页面

用于证件、合同、重要文件。

卡片字段：

```text
文档类型
标题
到期时间
安全等级
最近查看
```

安全等级视觉：

```text
normal：灰色
sensitive：蓝色
high_sensitive：橙色
vault_locked：红色/紫色
```

打开 high_sensitive 文档时：

```text
要求再次输入密码或 2FA 预留
```

---

## 7.8 XuanDrop 页面

这是必须做得好看的核心页面。

PC 端布局：

```text
左侧：我的设备列表
中间：拖拽上传区 + 当前传输会话
右侧：二维码接收区 + 最近快传
```

拖拽区样式：

```text
虚线边框
大图标
“Drop files here to send”
支持点击选择文件
```

二维码卡片：

```text
标题：Scan to send files to this PC
二维码
过期倒计时
刷新二维码按钮
```

设备卡片：

```text
设备图标
设备名称
最后在线
可信状态
发送按钮
```

移动端 XuanDrop：

```text
顶部：当前设备名
主按钮：扫码发送到 PC
按钮：选择照片
按钮：选择文件
按钮：拍照上传票据
最近接收文件
最近发送文件
```

实时状态：

```text
Waiting
Uploading
Received
Saved
Expired
```

---

## 7.9 Shared 页面

分两个 Tab：

```text
我分享的
分享给我的
```

分享卡片：

```text
目标名称
目标类型
权限
过期时间
访问次数
复制链接
取消分享
```

---

## 7.10 Trash 页面

功能：

```text
按类型筛选
恢复
永久删除
清空回收站
显示剩余保留天数
```

---

## 7.11 Settings 页面

设置项：

```text
个人资料
安全设置
设备管理
主题设置
存储空间
通知设置
导出数据
```

---

## 7.12 Admin 后台

后台风格要和主系统一致，但更偏管理。

页面：

```text
系统概览
用户管理
邀请码
存储统计
审计日志
备份任务
系统健康
配置管理
```

Admin Dashboard 显示：

```text
总用户数
总存储
今日上传
错误数量
最近备份
服务状态
磁盘空间
```

---

# 8. 组件设计标准

## 8.1 PageHeader

所有页面统一：

```text
标题
副标题
右侧主要操作按钮
次要筛选按钮
```

---

## 8.2 EmptyState

空状态必须友好。

例如 Photos 空状态：

```text
No photos yet
Upload your first photo to start building your private timeline.
[Upload Photos]
```

中文：

```text
还没有照片
上传第一张照片，开始建立你的私有时间线。
[上传照片]
```

---

## 8.3 UploadProgressPanel

所有上传统一显示：

```text
文件名
进度条
速度
剩余时间
成功 / 失败
重试按钮
```

---

## 8.4 DetailDrawer

PC 端所有资源详情统一右侧抽屉：

```text
缩略图 / 图标
名称
类型
大小
创建时间
标签
操作按钮
审计信息
```

---

## 8.5 MobileBottomSheet

移动端所有“更多操作”统一 bottom sheet：

```text
下载
分享
移动
重命名
收藏
删除
```

---

# 9. 样式规范

## 9.1 CSS 变量

```css
:root {
  --xb-color-primary: #1E3A5F;
  --xb-color-primary-soft: #E8EEF7;
  --xb-color-accent: #7C3AED;
  --xb-color-success: #10B981;
  --xb-color-warning: #F59E0B;
  --xb-color-danger: #EF4444;

  --xb-bg-page: #F6F8FB;
  --xb-bg-card: #FFFFFF;
  --xb-bg-sidebar: #0F172A;

  --xb-text-main: #0F172A;
  --xb-text-muted: #64748B;
  --xb-border: #E2E8F0;

  --xb-radius-sm: 8px;
  --xb-radius-md: 12px;
  --xb-radius-lg: 16px;
  --xb-radius-xl: 24px;

  --xb-shadow-card: 0 8px 24px rgba(15, 23, 42, 0.08);
}
```

暗色：

```css
[data-theme="dark"] {
  --xb-bg-page: #0B1020;
  --xb-bg-card: #151B2E;
  --xb-bg-sidebar: #080C18;
  --xb-text-main: #F8FAFC;
  --xb-text-muted: #94A3B8;
  --xb-border: rgba(255,255,255,0.08);
}
```

---

## 9.2 按钮规范

主按钮：

```text
高度 40px PC
高度 44px Mobile
圆角 10px
主色背景
白色文字
```

危险按钮：

```text
红色
二次确认
```

移动端主操作按钮：

```text
全宽
高度 48px
大圆角
```

---

## 9.3 卡片规范

```text
背景：白色 / 暗色卡片
圆角：16px
padding：20px PC，16px Mobile
阴影：轻阴影
hover：轻微上浮或边框高亮
```

---

## 9.4 表格规范

PC 后台可以用表格。
普通用户页面尽量少用表格，多用卡片和列表。

表格适合：

```text
用户管理
审计日志
备份任务
文件列表高级模式
```

---

# 10. 开发顺序蓝图

这里不是产品分期，而是实际工程开发顺序。

## Step 1：基础工程

```text
创建 xuanbox 项目
Docker Compose
FastAPI skeleton
Vue skeleton
PostgreSQL
Redis
.env
health check
```

验收：

```text
localhost 可访问前端
/api/health 正常
数据库迁移可执行
```

---

## Step 2：认证与用户

```text
User model
Invite model
Device model
登录
邀请码注册
/me
refresh token
设备记录
基础布局
```

验收：

```text
可以通过邀请码注册
可以登录
可以保持登录
可以查看当前用户
可以看到设备记录
```

---

## Step 3：加密文件基础

```text
Encryption service
Storage service
FileAsset model
文件上传
文件加密保存
文件下载解密
文件列表
文件删除
```

验收：

```text
磁盘上不能直接打开原文件
下载必须登录
用户只能看到自己的文件
```

---

## Step 4：PC / Mobile 主布局

```text
DesktopLayout
MobileLayout
Sidebar
Topbar
BottomNav
Dashboard
主题变量
响应式规则
```

验收：

```text
PC 有完整 Sidebar 布局
手机有 Bottom Tab
主要页面不溢出
```

---

## Step 5：文件系统完整化

```text
文件夹
重命名
移动
收藏
标签
回收站
详情抽屉
上传进度
```

验收：

```text
基本网盘体验可用
PC 能批量整理
手机能上传下载
```

---

## Step 6：照片系统

```text
图片识别
缩略图生成
预览图生成
照片时间线
大图预览
相册
移动端滑动预览
```

验收：

```text
手机上传照片
PC 时间线查看
缩略图通过 API 加载
原图不公开暴露
```

---

## Step 7：票据系统

```text
Receipt model
票据上传
票据表单
分类
金额
日期
商家
保修期
筛选
搜索
```

验收：

```text
手机拍照上传票据
PC 编辑票据信息
可以按分类/年份/商家搜索
```

---

## Step 8：XuanDrop

```text
TransferSession
TransferItem
设备列表
二维码 token
扫码上传
PC 实时显示
临时文件过期
保存到资料库
```

验收：

```text
PC 显示二维码
手机扫码上传图片
PC 立即看到
可以保存到照片/文件/票据
```

---

## Step 9：分享系统

```text
指定用户分享
临时链接
密码
过期时间
下载限制
分享日志
```

验收：

```text
可以安全分享文件
过期后无法访问
取消分享立即失效
```

---

## Step 10：证件与重要文档

```text
Document model
安全等级
到期提醒
二次验证预留
```

验收：

```text
可以保存证件/合同
可以设置到期日
Dashboard 显示提醒
```

---

## Step 11：OCR 与 Worker

```text
Worker 框架
OCR task
票据 OCR
字段待确认
缩略图异步任务
清理任务
```

验收：

```text
票据可触发 OCR
OCR 结果可确认
失败可重试
```

---

## Step 12：后台管理

```text
Admin overview
用户管理
邀请码管理
存储统计
审计日志
备份任务
系统健康
```

验收：

```text
Owner 可以管理系统
不能直接浏览用户私有文件内容
```

---

## Step 13：备份与迁移

```text
数据库备份
文件备份
配置备份
手动备份
定时备份
恢复说明
```

验收：

```text
可以导出数据库
可以备份加密文件目录
可以在新机器恢复
```

---

# 11. Codex 开发总命令模板

后续可以把这个喂给 Codex：

```text
You are working on XuanBox, a self-hosted encrypted personal data vault.

The product is not a normal NAS, not a family shared drive, and not an admin dashboard.
It is a private secure cloud for photos, files, receipts, documents, XuanDrop device transfer, and encrypted storage.

Development rules:
1. Every user resource must be owner_id isolated.
2. Never expose user files through public static paths.
3. All file access must go through authenticated backend APIs.
4. Uploaded files must be encrypted from the beginning.
5. Admin pages must not directly browse private user file content.
6. PC and mobile layouts must be designed together.
7. XuanDrop is a core module, not an optional add-on.
8. Use Docker Compose, FastAPI, PostgreSQL, Redis, Vue 3, Pinia.
9. Keep the project deployable on a self-hosted 790 Pro server and migratable to a low-power NAS later.
10. Do not create temporary demo-only architecture. Build production-oriented modules.
```

---

# 12. 当前最建议先做的文件

第一批要让 Codex 创建：

```text
docs/XUANBOX_DEVELOPMENT_BLUEPRINT.md
docker-compose.yml
backend/app/main.py
backend/app/core/config.py
backend/app/core/database.py
backend/app/core/security.py
backend/app/models/user.py
backend/app/models/invite.py
backend/app/models/device.py
backend/app/models/file_asset.py
frontend/src/main.js
frontend/src/App.vue
frontend/src/router/index.js
frontend/src/layouts/DesktopLayout.vue
frontend/src/layouts/MobileLayout.vue
frontend/src/styles/variables.css
frontend/src/styles/theme.css
```

---

# 13. 总结

XuanBox 的开发重点不是“先做一个能上传文件的小工具”，而是从第一天就建立：

```text
安全账号体系
私有空间隔离
加密文件存储
跨端友好 UI
照片管理
票据管理
XuanDrop 设备快传
可迁移部署结构
```

这样后面功能越加越稳，不会变成一堆临时补丁。

下一步最合理的是：
**先让 Codex 根据这份开发蓝图创建项目骨架、Docker 环境、认证系统、基础 PC / Mobile 布局和加密文件上传主链路。**
