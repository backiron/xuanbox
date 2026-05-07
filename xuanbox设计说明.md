下面这版可以直接作为 **XuanBox 最终形态项目提案 / 产品蓝图** 使用。它不是“第一版、第二版”的阶段拆分，而是按最终产品完整设计来写。以后如果有新想法，再作为模块补充。

# XuanBox 玄匣

## 私有加密个人资料系统完整项目提案

## 1. 项目名称

**XuanBox**

中文名：**玄匣**

产品定位：

> XuanBox 是一个自托管、加密、跨端友好的个人资料保险库，用于保存、管理、检索和传输照片、文件、票据、合同、证件、项目资料和重要数字资产。

它不是普通 NAS，不是家庭共享盘，也不是简单网盘。

它的核心是：

> **每个人拥有自己的加密私有空间。资料默认私密。只有主动分享，别人才能访问。**

---

# 2. 核心理念

XuanBox 的设计原则是：

## 2.1 个人优先

系统不是“全家共享一个盘”，而是每个用户都有自己的独立空间。

每个用户拥有：

```text
我的照片
我的文件
我的票据
我的证件
我的合同
我的相册
我的快传
我的分享
我的回收站
我的设备
```

即使是家人，也默认不能互相看到对方资料。

## 2.2 默认私密

所有资料默认都是私有状态。

默认规则：

```text
用户 A 不能看用户 B 的文件
用户 A 不能搜索用户 B 的资料
用户 A 不能下载用户 B 的照片
管理员不能直接浏览用户私有文件内容
分享必须由所有者主动发起
```

## 2.3 高加密

XuanBox 必须从底层就按加密系统设计，而不是先做明文网盘再后补安全。

核心要求：

```text
文件加密存储
缩略图权限保护
下载必须鉴权
预览必须鉴权
分享链接必须可过期
所有敏感操作写入审计日志
```

## 2.4 跨端友好

XuanBox 必须同时适合：

```text
Windows PC
Mac
Android 手机
iPhone
iPad
Android 平板
浏览器
PWA
局域网设备
远程设备
```

不依赖 Windows 手机连接，不依赖苹果生态，不依赖 USB 线，不依赖蓝牙。

## 2.5 自托管

系统优先部署在个人服务器上，比如：

```text
790 Pro
低功耗 Mini PC
双盘位 NAS
x86 小主机
家用服务器
```

通过 Cloudflare Tunnel 或反向代理提供安全访问。

## 2.6 可迁移

系统不能写死在某台机器上。数据、数据库、文件、配置都必须可备份、可恢复、可迁移。

---

# 3. 产品目标

XuanBox 最终要成为一个完整的个人资料中心。

它解决这些问题：

## 3.1 照片分散

手机、电脑、微信、邮箱、下载目录、云盘里都有照片和截图，长期以后很难找。

XuanBox 解决方式：

```text
统一上传
按时间线查看
按相册管理
按标签分类
按设备来源记录
支持手机上传
支持 PC 批量整理
```

## 3.2 文件混乱

合同、文档、PDF、软件许可、项目资料、压缩包、账单都分散在不同设备上。

XuanBox 解决方式：

```text
文件夹管理
标签管理
收藏
搜索
分类
版本记录预留
加密存储
跨设备访问
```

## 3.3 票据难找

汽车维修票据、工具发票、家庭支出票据、税务相关资料、软件订阅账单，很容易丢。

XuanBox 解决方式：

```text
票据拍照上传
金额记录
商家记录
日期记录
分类
保修期
标签
OCR 识别
税务导出
车辆维修历史
```

## 3.4 手机和电脑互传麻烦

三星手机和 Windows 之间传图片、视频、PDF、票据经常不稳定。

XuanBox 解决方式：

```text
XuanDrop 设备快传
手机扫码传 PC
PC 拖拽传手机
临时文件中转
一键保存到照片库
一键保存到票据库
一键保存到文件库
```

## 3.5 私密资料缺少安全容器

证件、合同、票据、财务文件、项目资料不适合随便放公共云盘。

XuanBox 解决方式：

```text
私有空间
加密存储
权限隔离
设备管理
分享控制
登录审计
备份加密
```

---

# 4. 用户体系

## 4.1 用户类型

系统支持多用户，但不是开放注册平台。

用户类型：

```text
系统拥有者 Owner
普通用户 User
受邀用户 Invited User
临时访客 Guest
系统管理员 Admin
```

## 4.2 Owner

Owner 是系统拥有者。

权限：

```text
管理系统配置
管理存储空间
创建邀请码
管理用户状态
查看系统健康
查看备份状态
查看审计日志
管理设备
管理服务运行状态
```

限制：

```text
Owner 不应直接浏览其他用户私有文件内容
Owner 可以禁用用户
Owner 可以删除用户账号
Owner 可以查看容量占用
Owner 可以查看文件数量
Owner 不直接读取文件原始内容
```

## 4.3 User

普通用户拥有自己的私有空间。

权限：

```text
上传文件
管理照片
管理相册
管理票据
管理文件夹
使用设备快传
创建分享
管理自己的设备
查看自己的登录记录
删除和恢复自己的文件
```

## 4.4 Guest

临时访客用于临时分享、临时上传或短期访问。

权限可限制为：

```text
只读
只下载
只能上传到指定文件夹
只能访问指定分享
过期后自动失效
```

---

# 5. 注册与邀请系统

XuanBox 不开放自由注册，默认采用邀请制。

## 5.1 邀请码

邀请码字段：

```text
invite_code
created_by
role_to_assign
max_uses
used_count
expires_at
is_active
note
created_at
```

邀请码规则：

```text
可以设置有效期
可以设置使用次数
可以绑定默认角色
可以手动禁用
可以记录使用者
```

## 5.2 邀请链接

支持生成邀请链接：

```text
https://xuanbox.domain.com/invite/xxxx
```

用户通过邀请链接注册后，进入自己的私有空间。

## 5.3 邀请审计

系统记录：

```text
谁创建了邀请
谁使用了邀请
何时使用
注册 IP
注册设备
分配角色
```

---

# 6. 登录与账号安全

## 6.1 登录方式

支持：

```text
用户名 / 邮箱 + 密码
长期登录
刷新 Token
设备记住
退出登录
注销所有设备
```

## 6.2 密码安全

密码必须使用：

```text
Argon2id 或 bcrypt
```

不能使用：

```text
明文密码
MD5
SHA1
简单 hash
```

## 6.3 Token 体系

建议使用：

```text
Access Token
Refresh Token
Device Token
Session ID
```

每个登录设备都应该记录。

## 6.4 登录保护

包含：

```text
登录失败次数限制
异常 IP 记录
新设备登录提醒预留
强制退出所有设备
密码修改后清理旧 session
```

## 6.5 2FA 预留

系统应预留两步验证：

```text
TOTP
邮箱验证码
备用恢复码
```

---

# 7. 设备管理

XuanBox 必须有设备概念，因为它要支持跨设备互传。

## 7.1 设备类型

```text
Windows PC
Mac
Android Phone
iPhone
iPad
Android Tablet
Browser
Unknown Device
```

## 7.2 设备表

```text
device_id
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

## 7.3 设备功能

用户可以：

```text
查看已登录设备
给设备改名
设为可信设备
移除设备
远程退出设备
查看设备最近活动
```

## 7.4 设备快传关联

XuanDrop 使用设备系统识别：

```text
当前 PC
当前手机
当前平板
目标设备
来源设备
```

---

# 8. 私有空间系统

## 8.1 用户空间

每个用户拥有独立空间：

```text
/user/{user_id}/photos
/user/{user_id}/files
/user/{user_id}/receipts
/user/{user_id}/albums
/user/{user_id}/drop
/user/{user_id}/trash
```

但真实文件路径不应暴露给前端。

## 8.2 存储配额

系统支持容量限制：

```text
用户总容量
照片容量
文件容量
票据容量
临时快传容量
回收站容量
```

配额字段：

```text
user_id
storage_limit_bytes
used_storage_bytes
photo_storage_bytes
file_storage_bytes
receipt_storage_bytes
drop_storage_bytes
trash_storage_bytes
```

## 8.3 空间统计

用户 Dashboard 显示：

```text
总容量
已用容量
照片数量
文件数量
票据数量
最近上传
最近快传
最近分享
回收站大小
```

---

# 9. 加密存储系统

这是 XuanBox 的核心。

## 9.1 文件加密原则

所有用户上传文件必须加密保存。

上传流程：

```text
用户上传文件
后端校验权限
生成 file_key
使用 file_key 加密文件内容
生成 encrypted_file.bin
保存加密文件
保存 metadata
生成缩略图或预览图
缩略图也进入受保护存储
```

## 9.2 加密方式

建议：

```text
AES-256-GCM
每文件独立密钥
每文件独立 nonce
密钥版本管理
```

## 9.3 文件密钥

每个文件有独立 file_key。

file_key 不能明文存在数据库里，需要被包装加密。

字段：

```text
file_id
owner_id
encryption_method
key_version
encrypted_file_key
nonce
auth_tag
encrypted_path
created_at
```

## 9.4 服务器端可解密模式

为了支持在线预览、缩略图、OCR、搜索，XuanBox 采用服务器端可解密的高安全模式。

也就是说：

```text
文件在磁盘上是加密的
访问必须经过后端权限检查
后端在授权后解密并流式返回
```

完全零知识加密可作为未来增强模式，但不作为默认模式，因为它会影响预览、OCR、图片缩略图、票据识别和搜索。

## 9.5 禁止公开静态目录

禁止这种设计：

```text
/static/uploads/user_photo.jpg
/static/files/invoice.pdf
```

必须使用 API：

```text
GET /api/files/{file_id}/download
GET /api/photos/{photo_id}/preview
GET /api/photos/{photo_id}/thumbnail
GET /api/receipts/{receipt_id}/file
```

后端先鉴权，再解密，再返回。

---

# 10. 文件系统

## 10.1 文件上传

支持：

```text
单文件上传
多文件上传
拖拽上传
移动端上传
大文件上传
上传进度
失败重试
文件类型识别
重复文件检测
```

## 10.2 文件类型

支持：

```text
图片
视频
PDF
Word
Excel
PowerPoint
文本
压缩包
代码文件
扫描件
其他二进制文件
```

## 10.3 文件 Metadata

```text
file_id
owner_id
folder_id
original_filename
display_name
mime_type
file_ext
file_size
sha256_hash
encrypted_path
file_category
source
is_favorite
is_deleted
created_at
updated_at
deleted_at
```

## 10.4 文件夹

支持多级文件夹。

字段：

```text
folder_id
owner_id
parent_id
name
path_cache
created_at
updated_at
deleted_at
```

功能：

```text
创建文件夹
重命名
移动
删除
恢复
查看文件夹大小
```

## 10.5 文件操作

支持：

```text
上传
下载
预览
重命名
移动
复制
删除
恢复
永久删除
收藏
标签
分享
查看详情
```

## 10.6 文件视图

PC 端支持：

```text
列表视图
网格视图
详情面板
按名称排序
按时间排序
按大小排序
按类型筛选
```

移动端支持：

```text
卡片视图
简洁列表
底部操作菜单
长按多选
```

---

# 11. 照片系统

## 11.1 照片上传

照片可以来自：

```text
手机上传
PC 上传
XuanDrop 快传保存
票据模块转入
批量导入
```

## 11.2 时间线

照片按时间线展示：

```text
今天
昨天
本周
本月
按年份
按月份
按日期
```

如果有 EXIF 拍摄时间，优先使用拍摄时间。没有则使用上传时间。

## 11.3 缩略图与预览

系统生成：

```text
thumbnail
preview
original
```

但这些都不能公开暴露。

访问方式：

```text
/api/photos/{photo_id}/thumbnail
/api/photos/{photo_id}/preview
/api/photos/{photo_id}/original
```

## 11.4 大图预览

支持：

```text
点击放大
左右切换
键盘左右键
移动端滑动
双指缩放预留
下载原图
查看详情
```

## 11.5 照片 Metadata

```text
photo_id
file_id
owner_id
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
is_favorite
created_at
```

GPS 信息属于敏感信息，应默认隐藏。

## 11.6 相册

支持：

```text
创建相册
编辑相册
设置封面
添加照片
移除照片
相册排序
相册分享
删除相册
```

相册字段：

```text
album_id
owner_id
title
description
cover_file_id
visibility
created_at
updated_at
```

## 11.7 照片标签

照片可以绑定标签：

```text
家庭
车辆
项目
票据
旅行
工作
截图
重要
```

## 11.8 照片搜索

支持：

```text
按日期
按相册
按标签
按文件名
按设备
按收藏
```

未来可扩展：

```text
AI 物体识别
人脸聚类
场景识别
语义搜索
```

---

# 12. 票据系统

票据系统是 XuanBox 的重点模块。

## 12.1 票据来源

票据可以来自：

```text
手机拍照上传
PC 上传
XuanDrop 快传保存为票据
PDF 导入
图片导入
邮件附件导入预留
```

## 12.2 票据类型

```text
汽车
家庭
工具
电子产品
医疗
超市
软件订阅
项目支出
税务
保险
维修
其他
```

英文内部枚举：

```text
vehicle
home
tools
electronics
medical
grocery
software
business
tax
insurance
repair
other
```

## 12.3 票据字段

```text
receipt_id
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
tags
ocr_status
created_at
updated_at
```

## 12.4 票据功能

支持：

```text
上传票据
拍照上传
手动录入金额
手动录入商家
手动录入日期
选择分类
添加备注
添加标签
设置保修期
关联文件
关联车辆
关联项目
搜索
筛选
导出
删除
恢复
```

## 12.5 票据 OCR

系统支持 OCR 识别：

```text
图片文字识别
PDF 文字识别
商家提取
日期提取
金额提取
税额提取
币种识别
字段待确认
```

OCR 流程：

```text
上传票据
创建 OCR 任务
Worker 异步处理
保存 raw_text
解析字段
用户确认
写入票据结构化字段
```

OCR 表：

```text
ocr_task_id
owner_id
file_id
receipt_id
status
raw_text
parsed_json
error_message
created_at
finished_at
confirmed_at
```

OCR 状态：

```text
pending
processing
completed
failed
confirmed
```

## 12.6 车辆票据

针对汽车相关票据可以扩展：

```text
车辆名称
车牌
里程数
维修项目
保养项目
维修店
下次保养提醒
```

例如：

```text
F150 oil change
F150 tire replacement
F150 brake service
```

## 12.7 保修提醒

票据可设置保修期。

提醒：

```text
保修即将到期
订阅即将续费
车辆保养到期
保险到期
```

---

# 13. 证件与重要文档系统

XuanBox 应该专门支持重要资料。

## 13.1 资料类型

```text
身份证明
护照
驾照
签证
PR 卡
保险
税务文件
银行文件
合同
房屋文件
车辆文件
医疗文件
学校文件
软件许可
```

## 13.2 安全级别

重要文档可以设置安全等级：

```text
normal
sensitive
high_sensitive
vault_locked
```

高敏资料可要求二次验证后打开。

## 13.3 文档字段

```text
document_id
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

## 13.4 到期提醒

支持：

```text
证件过期提醒
保险到期提醒
合同续期提醒
软件许可证到期提醒
```

---

# 14. XuanDrop 设备快传系统

XuanDrop 是 XuanBox 的核心亮点之一。

中文名：**设备快传**

## 14.1 功能定位

XuanDrop 用于解决手机、平板、PC 之间传文件不方便的问题。

典型场景：

```text
三星手机传照片到 Windows
Windows 传 PDF 到手机
手机拍票据传到 PC
PC 拖拽文件到手机
临时传文件给自己的另一台设备
把临时传输文件保存进正式资料库
```

## 14.2 两种传输模式

### 临时快传

用于设备之间临时中转。

特点：

```text
文件临时保存
自动过期
可下载
可删除
可一键保存到资料库
```

过期时间：

```text
1 小时
24 小时
7 天
自定义
```

### 归档传输

上传后直接保存到：

```text
照片库
文件库
票据库
证件库
指定文件夹
指定相册
```

## 14.3 PC 接收手机文件

流程：

```text
PC 打开 XuanDrop
显示二维码
手机扫码
选择照片或文件
上传
PC 页面实时显示
PC 下载或保存到资料库
```

## 14.4 手机接收 PC 文件

流程：

```text
手机打开 XuanDrop
PC 拖拽文件
选择目标设备为手机
手机端显示接收文件
用户下载或保存
```

## 14.5 同账号设备列表

用户可以看到自己的设备：

```text
Nick Windows PC
Samsung Phone
Tablet
Laptop
```

并选择目标设备发送。

## 14.6 扫码上传

二维码必须短期有效。

二维码 token 包含：

```text
target_device_id
owner_id
expires_at
one_time_token
permission_scope
```

过期后失效。

## 14.7 批量传输

支持：

```text
批量图片
批量视频
批量 PDF
批量文档
打包下载 zip
批量保存到相册
批量保存到文件夹
```

## 14.8 快传表结构

### transfer_sessions

```text
session_id
owner_id
source_device_id
target_device_id
mode
status
expires_at
created_at
```

### transfer_items

```text
item_id
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

## 14.9 实时更新

使用 WebSocket。

```text
PC 打开 XuanDrop
建立 WebSocket
手机上传文件
后端推送通知
PC 端实时显示新文件
```

如果 WebSocket 暂时不可用，可降级轮询。

## 14.10 安全规则

```text
必须登录
二维码短期有效
临时文件加密存储
下载必须鉴权
公开链接默认关闭
传输记录写入审计日志
设备可撤销
```

---

# 15. 标签系统

标签跨所有模块使用。

适用对象：

```text
照片
文件
票据
证件
合同
相册
快传文件
```

标签字段：

```text
tag_id
owner_id
name
color
created_at
updated_at
```

功能：

```text
创建标签
修改标签
删除标签
添加到文件
从文件移除
按标签筛选
标签颜色
标签统计
```

---

# 16. 搜索系统

搜索必须按用户隔离。

## 16.1 搜索范围

```text
文件名
文件夹名
照片时间
照片标签
相册名称
票据商家
票据金额
票据分类
票据备注
OCR 文本
证件标题
文档类型
分享记录
```

## 16.2 搜索规则

所有搜索必须带：

```text
owner_id
```

禁止跨用户搜索。

## 16.3 高级搜索

支持：

```text
按日期范围
按文件类型
按金额范围
按分类
按标签
按收藏
按是否分享
按是否删除
```

## 16.4 OCR 全文搜索

票据 OCR 后，可以搜索票据文字内容。

例如：

```text
Costco
oil change
F150
Home Depot
CRA
invoice
```

---

# 17. 分享系统

## 17.1 分享原则

默认不共享。

分享必须由文件所有者主动发起。

## 17.2 分享类型

```text
分享给指定用户
生成临时链接
生成上传文件夹
分享相册
分享单个文件
分享多个文件
```

## 17.3 分享权限

```text
read
download
upload
comment 预留
```

## 17.4 分享限制

支持：

```text
过期时间
下载次数限制
密码访问
取消分享
访问日志
```

## 17.5 分享表

```text
share_id
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

## 17.6 访问日志

记录：

```text
谁访问
何时访问
访问 IP
访问设备
下载次数
是否失败
```

---

# 18. 回收站系统

所有删除默认软删除。

## 18.1 回收站对象

```text
文件
照片
票据
证件
相册
文件夹
快传文件
```

## 18.2 功能

```text
查看回收站
恢复
永久删除
批量清理
自动清理
```

## 18.3 自动清理

可设置：

```text
30 天
60 天
90 天
永不自动清理
```

---

# 19. 收藏与快捷访问

用户可以收藏：

```text
照片
文件
票据
文件夹
相册
证件
```

Dashboard 显示最近收藏和常用文件夹。

---

# 20. 审计日志

XuanBox 必须记录重要操作。

## 20.1 用户行为

```text
登录
退出
上传
下载
预览
删除
恢复
永久删除
分享
取消分享
修改密码
添加设备
移除设备
快传
```

## 20.2 管理行为

```text
创建邀请码
禁用用户
修改用户容量
查看系统状态
执行备份
恢复备份
修改系统配置
```

## 20.3 审计字段

```text
log_id
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

# 21. 管理后台

管理后台只管理系统，不浏览用户隐私内容。

## 21.1 后台功能

```text
用户管理
邀请码管理
存储统计
系统健康
磁盘状态
备份状态
登录日志
审计日志
错误日志
OCR 任务
缩略图任务
快传任务
设备列表
系统配置
```

## 21.2 用户管理

可以查看：

```text
用户名
状态
角色
注册时间
最后登录
容量占用
文件数量
设备数量
是否禁用
```

不能直接查看：

```text
用户照片内容
用户票据内容
用户文件内容
```

## 21.3 系统健康

显示：

```text
CPU
内存
磁盘空间
数据库状态
Redis 状态
Worker 状态
Cloudflare Tunnel 状态
最近备份
错误数量
```

---

# 22. 备份系统

备份是 XuanBox 的基础能力。

## 22.1 备份内容

```text
PostgreSQL 数据库
加密文件目录
缩略图目录
OCR 数据
配置文件
Docker Compose
.env 安全副本
审计日志
```

## 22.2 备份方式

支持：

```text
本地备份
外接硬盘备份
另一台机器备份
加密压缩包
手动备份
定时备份
```

## 22.3 备份策略

建议：

```text
数据库每日备份
文件每周增量备份
重要资料每日增量备份
每月完整备份
备份文件加密保存
```

## 22.4 恢复能力

系统应支持：

```text
恢复数据库
恢复文件目录
恢复单个用户
恢复单个文件
恢复配置
迁移到新服务器
```

---

# 23. 前端整体设计

XuanBox 必须是完整产品界面，不是后台模板。

## 23.1 视觉风格

关键词：

```text
私密
安全
现代
清爽
有秩序
像个人保险库
不像传统 NAS 后台
```

## 23.2 PC 端布局

PC 端适合整理和管理。

布局：

```text
左侧主导航
顶部搜索栏
中间内容区
右侧详情面板
底部状态提示
```

左侧导航：

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

## 23.3 移动端布局

移动端适合查看、上传、拍照、快传。

底部导航：

```text
Home
Photos
Files
Receipts
Drop
Me
```

移动端设计：

```text
大按钮
卡片式
底部弹窗菜单
滑动预览照片
浮动上传按钮
扫码快传入口明显
拍照上传票据入口明显
```

## 23.4 Dashboard

Dashboard 显示：

```text
容量使用
最近照片
最近文件
最近票据
最近快传
待确认 OCR
保修提醒
证件到期提醒
最近分享
快捷上传
```

---

# 24. 移动端体验

XuanBox 虽然是 Web 系统，但必须移动端友好。

## 24.1 PWA

支持：

```text
添加到主屏幕
移动端全屏体验
基础离线页面
推送通知预留
```

## 24.2 手机上传

支持：

```text
从相册选择
拍照上传
选择文件
批量上传
票据拍照后直接进入表单
```

## 24.3 手机照片查看

支持：

```text
时间线
大图滑动
双指缩放预留
下载
收藏
添加相册
分享
```

## 24.4 手机快传

支持：

```text
扫码发送到 PC
接收 PC 文件
临时文件下载
保存到资料库
```

---

# 25. 技术架构

## 25.1 推荐技术栈

```text
Frontend:
Vue 3
Vite
Pinia
Vue Router
Element Plus / Naive UI
PWA support

Backend:
FastAPI
Python 3.11+

Database:
PostgreSQL

Cache / Queue:
Redis

Worker:
Python async worker

Storage:
Local encrypted file storage

Proxy:
Caddy or Nginx

Remote Access:
Cloudflare Tunnel

Deploy:
Docker Compose
```

## 25.2 服务划分

```text
xuanbox-web
xuanbox-api
xuanbox-worker
xuanbox-postgres
xuanbox-redis
xuanbox-proxy
xuanbox-tunnel
```

---

# 26. 后端模块结构

建议：

```text
app/
  api/
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

  models/
    user.py
    invite.py
    device.py
    file_asset.py
    folder.py
    photo_asset.py
    album.py
    receipt.py
    document.py
    tag.py
    share.py
    transfer.py
    audit_log.py
    backup_job.py

  services/
    auth_service.py
    encryption_service.py
    storage_service.py
    file_service.py
    folder_service.py
    photo_service.py
    thumbnail_service.py
    receipt_service.py
    document_service.py
    ocr_service.py
    share_service.py
    drop_service.py
    search_service.py
    backup_service.py
    audit_service.py

  workers/
    thumbnail_worker.py
    ocr_worker.py
    cleanup_worker.py
    backup_worker.py
```

---

# 27. 存储目录设计

建议：

```text
/data/xuanbox/
  storage/
    encrypted_files/
    encrypted_thumbnails/
    encrypted_previews/
    temp_uploads/
    drop_temp/

  appdata/
    postgres/
    redis/

  backups/
    database/
    files/
    configs/
    exports/

  logs/
```

真实存储路径：

```text
/data/xuanbox/storage/encrypted_files/{owner_id}/{year}/{month}/{file_id}.bin
```

但前端永远不直接知道真实路径。

---

# 28. API 设计方向

## 28.1 Auth

```text
POST /api/auth/login
POST /api/auth/logout
POST /api/auth/refresh
POST /api/auth/register-by-invite
POST /api/auth/change-password
GET  /api/auth/me
```

## 28.2 Files

```text
POST /api/files/upload
GET  /api/files
GET  /api/files/{file_id}
GET  /api/files/{file_id}/download
PATCH /api/files/{file_id}
DELETE /api/files/{file_id}
POST /api/files/{file_id}/restore
```

## 28.3 Photos

```text
GET  /api/photos
POST /api/photos/upload
GET  /api/photos/{photo_id}/thumbnail
GET  /api/photos/{photo_id}/preview
GET  /api/photos/{photo_id}/original
PATCH /api/photos/{photo_id}
DELETE /api/photos/{photo_id}
```

## 28.4 Receipts

```text
GET  /api/receipts
POST /api/receipts
POST /api/receipts/upload
GET  /api/receipts/{receipt_id}
PATCH /api/receipts/{receipt_id}
DELETE /api/receipts/{receipt_id}
POST /api/receipts/{receipt_id}/ocr
```

## 28.5 XuanDrop

```text
GET  /api/drop/devices
POST /api/drop/session
GET  /api/drop/session/{session_id}
POST /api/drop/upload
GET  /api/drop/items
GET  /api/drop/items/{item_id}/download
POST /api/drop/items/{item_id}/save-to-library
DELETE /api/drop/items/{item_id}
GET  /api/drop/qr-token
```

## 28.6 Share

```text
POST /api/shares
GET  /api/shares
PATCH /api/shares/{share_id}
DELETE /api/shares/{share_id}
GET  /api/public-share/{token}
```

---

# 29. 部署方案

## 29.1 当前部署

初期部署在 790 Pro。

结构：

```text
790 Pro
Docker Compose
PostgreSQL
Redis
FastAPI
Vue
Encrypted local storage
Cloudflare Tunnel
```

## 29.2 未来迁移

可迁移到：

```text
N100 Mini PC
N150 Mini PC
双盘位低功耗设备
x86 NAS
家庭服务器
VPS
```

## 29.3 迁移要求

必须支持：

```text
导出数据库
迁移加密文件目录
迁移配置
迁移备份
切换域名
恢复服务
```

---

# 30. 安全底线

XuanBox 永远不能违反以下底线：

```text
不能明文保存密码
不能把用户文件放在公开目录
不能绕过 owner_id 查询
不能让管理员后台直接浏览用户私密内容
不能生成永久无限制公开分享链接
不能没有备份
不能没有审计日志
不能把加密作为以后再补的功能
```

---

# 31. 完整产品形态总结

XuanBox 最终是一个：

```text
个人私有网盘
照片保险箱
票据管理系统
证件资料库
跨设备快传工具
加密文件保险库
自托管个人云
```

它的核心价值不是“能存文件”，而是：

> **把一个人的重要数字资料安全、清晰、长期地管理起来，并且让手机和 PC 之间的资料流动变得简单。**

---

# 32. 一句话最终定义

**XuanBox 是一个自托管的私有加密个人资料系统，集照片管理、文件管理、票据归档、证件保存、跨设备快传和安全分享于一体，让每个用户拥有属于自己的数字资料保险库。**
