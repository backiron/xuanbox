# XuanBox 体检报告与产品蓝图

日期：2026-05-12

这份文档基于当前代码真实状态整理，不只沿用最早的施工蓝图。目标是先把 XuanBox 现在已经有什么、缺什么、风险在哪里、下一步应该先做什么讲清楚，然后再继续推进设置页、权限、管理员后台和文档智能。

## 一、总体判断

XuanBox 已经不是一个简单网盘 demo。现在它已经有加密文件底座、照片、文件、收据、XuanDrop、分享、备份、管理员基础能力、重要文件 PIN、移动端适配和部分搜索雏形。

但下一阶段不能再只是继续补页面。现在最重要的是建立三个边界：

1. 用户产品边界：普通用户只进入自己的文件、照片、收据、分享、设置。
2. 管理后台边界：管理员只进入独立后台，管理系统、用户、配额、消息、备份、任务，不进入用户个人文件空间。
3. 文档智能边界：OCR 不再只属于小票，而是所有上传文件都可以进入统一文档智能流水线。

我的建议很明确：先做权限和管理员拆分，再做设置页完整化，然后再开始通用 Document Intelligence。不要现在直接上 AI。

## 二、当前已完成能力

### 1. 账号与安全基础

当前已有：

- 登录、退出、全设备退出。
- JWT access token 和 refresh token。
- 邀请注册。
- 设备和会话记录。
- 角色字段：owner、admin、user、guest。
- 用户状态：active、disabled、locked、deleted。
- 管理员 API 使用角色保护。

当前问题：

- `/admin` 仍然挂在普通用户 AppShell 里面。
- 桌面侧边栏和移动端菜单仍显示 Admin。
- 管理员账号和普通用户账号没有从登录入口、token 用途、路由区域上分隔。
- 管理员理论上仍能进入普通用户前端页面。
- role 同时承担“系统权限”和“用户等级”的含义，后面会混乱。

结论：

下一步必须把 admin 从前端用户页面中拿掉，做独立 `/admin/login` 和 `/admin-console`。

### 2. 加密文件底座

当前已有：

- 上传文件后写入 `FileAsset`。
- 每个文件独立文件密钥。
- AES-GCM 加密。
- 文件密钥再通过 `MASTER_KEY` 包装。
- 存储 `nonce`、`auth_tag`、`sha256`。
- 所有用户资源按 `owner_id` 隔离。
- 下载必须走受保护 API。
- 文件支持软删除、恢复、彻底删除。
- 文件夹、标签、收藏、详情面板已有。
- vault_locked 重要文件会从普通文件列表隐藏。

当前问题：

- `storage_limit_bytes` 已经在用户表里，但没有形成完整的配额策略和全链路拦截。
- 文件全文搜索还没有后端索引。
- 文件生命周期还不完整，比如垃圾箱自动清理、衍生图清理、临时文件清理。

### 3. 照片与相册

当前已有：

- 照片上传。
- 缩略图、预览图、原图下载。
- 时间线展示。
- 相册。
- 多选编辑。
- 移动到相册、删除、从已选照片进入分享。
- 移动端体验经过多轮调整。

当前问题：

- 多图分享已经能进入分享设置，但“多图作为一个集合分享”的业务语义还不完整。
- 照片 OCR、截图识别、图片文档分类还没有接入。

### 4. 收据和 OCR

当前已有：

- 收据上传和结构化字段。
- `OcrTask` 收据 OCR 表。
- `WorkerTask` 通用任务队列表。
- 后台 worker。
- `receipt_ocr` 任务处理。
- RapidOCR / Tesseract 路径。
- 简单文本和 PDF 文本提取。
- 可选 Ollama 辅助小票解析。

当前问题：

- OCR 仍然是小票专属逻辑。
- worker 只认识 `receipt_ocr`，新任务类型会失败。
- PDF 处理还很粗，不应该当成最终文档智能能力。
- AI 配置是 `RECEIPT_AI_*`，后面应该升级成 `DOCUMENT_AI_*`。

结论：

不要继续把小票做成越来越大的孤岛。小票应该逐步迁移成文档智能的一种视图。

### 5. 文档与重要文件

当前已有：

- `DocumentAsset` 文档表。
- 文档上传和元数据。
- 安全等级：normal、sensitive、high_sensitive、vault_locked。
- 重要文件 PIN 已在当前工作树中加入。
- PIN 解锁 token 是短期有效。
- vault_locked 文件会从普通列表隐藏，并禁止公开分享。

当前问题：

- 用户设置里还没有把“重要文件、安全边界、PIN、备份风险”讲清楚。
- 当前不是零知识架构，因为服务端仍有 `MASTER_KEY`。

非常重要的产品表述：

- 可以说：文件静态加密、用户隔离、管理员产品层面不能浏览用户私有内容。
- 不能说：管理员或服务器永远无法解密。
- 如果未来要强到零知识，需要客户端持钥或用户独立密钥体系。

### 6. XuanDrop

当前已有：

- 临时会话。
- 二维码和公开上传链接。
- 手机向电脑上传已经跑通。
- 上传进度已经补过。
- 收到的文件可以保存到 Files、Photos、Receipts。
- 过期会话显示已经开始收敛。

当前问题：

- PC 到手机的业务还需要更清晰：本质是电脑选择文件，手机打开同一个 session 后下载或保存。
- 临时项和过期 session 需要自动清理策略。
- 完成状态、失败状态、保存状态还可以更明确。

### 7. 分享

当前已有：

- 公开分享链接。
- 指定 XuanBox 用户分享。
- 文件、照片、收据、文档等目标类型。
- 公开分享默认 7 天和 3 次下载。
- 密码分享现在改成短期 access token，不再把密码一直带在 URL 里。
- Unicode 文件名下载已修复。
- vault_locked 重要文件禁止公开分享。
- 分享归档已改成 `archived_at` 软归档。
- 移动端 Shared 页面已经重构过。

当前问题：

- “Shared with me” 已改成 Received 更容易懂，但还需要用户文案解释。
- 归档入口要在桌面和移动端都稳定出现。
- 分享访问日志还没有展示给用户。
- 多图/相册分享的最终体验还没完全定型。

### 8. 管理后台与备份

当前已有：

- 管理员概览。
- 用户列表。
- 用户角色、状态、空间限制更新。
- 邀请。
- 审计日志。
- 备份任务和定时备份。
- 恢复脚本。

当前问题：

- 管理后台还在普通用户 App 里。
- 管理功能还不够目标形态：缺少用户等级、套餐、消息、站内信、OCR/AI 开关、worker 状态、系统策略。
- 备份包含加密文件和数据库元数据，仍是敏感资产，需要明确文档说明。

## 三、商业和开源策略建议

你说开源主要是为了让用户敢用，这个判断是对的。隐私文件类产品如果完全闭源，信任成本很高。

但你又希望保留商业用途，也合理。建议路线：

1. 社区版开源，提供个人和家庭自托管核心能力。
2. 商业版或商业授权覆盖公司使用、托管服务、高级后台、团队策略、审计增强、AI 批处理等能力。
3. 许可证可以考虑 AGPLv3 + 商业授权，或者 source-available + 商业授权。
4. 先别急着营销“企业级”，先把安全边界、备份、管理员后台、权限模型做扎实。

适合开源仓库公开的内容：

- 文件加密底座。
- 自托管部署。
- 用户自己的照片、文件、收据、文档管理。
- XuanDrop。
- 基础分享。
- 基础 OCR。

适合商业化增强的内容：

- 高级管理员后台。
- 团队空间。
- 多级套餐和配额策略。
- 高级审计。
- 批量文档智能。
- AI 摘要/分类/字段提取。
- 远程备份、对象存储、企业 SSO。
- 托管版或安装服务。

## 四、权限与用户等级设计

### 1. role 和 plan 必须分开

建议：

- `role` 只表示系统权力：owner、admin、user、guest。
- `plan` 表示用户等级：internal、free、plus、pro、business。

不要用 admin 表示高级用户。管理员是管理者，不是付费用户。

### 2. 普通用户权限

普通用户应该可以：

- 上传和管理自己的文件、照片、收据、文档。
- 使用自己的 XuanDrop。
- 创建分享链接，受套餐限制。
- 设置头像、昵称、密码。
- 管理自己的设备和会话。
- 查看自己的存储空间。
- 查看收到的站内信。

普通用户不能：

- 看其他用户文件。
- 看管理员后台。
- 改系统设置。
- 创建用户或封禁用户。
- 看全局审计。

### 3. 高级用户权限

高级用户不是 admin，而是更高 plan。

可增加：

- 更大空间。
- 更多分享链接。
- 更长分享有效期。
- 更高下载次数。
- 更多 XuanDrop session。
- 更多 OCR/AI 额度。
- 批量文档智能。
- 更长历史记录。

### 4. 管理员权限

管理员应该可以：

- 登录独立后台。
- 查看系统概览。
- 管理用户状态。
- 设置用户空间。
- 封禁、解封用户。
- 发站内信。
- 查看审计日志。
- 管理邀请。
- 管理备份。
- 查看 worker、OCR、AI 状态。
- 配置系统策略。

管理员不应该：

- 进入用户个人文件页面。
- 以用户身份浏览照片、文件、收据。
- 直接下载用户私人文件。

### 5. owner 权限

owner 是最高系统拥有者。

owner 可以：

- 管理管理员。
- 修改系统级设置。
- 管理许可证/商业配置。
- 管理备份恢复策略。

owner 也不应该默认绕过用户隐私内容边界。

## 五、设置页应该做成什么

用户设置页不是后台。它应该只管理“我自己的账号”。

建议分区：

1. 个人资料
   - 头像
   - 昵称
   - 邮箱
   - 用户名只读或有限修改

2. 安全
   - 修改密码
   - 全设备退出
   - 重要文件 PIN 设置
   - 安全提示

3. 设备
   - 当前登录设备
   - 可信设备
   - 撤销设备

4. 存储与套餐
   - 已用空间
   - 空间上限
   - 当前等级
   - 分享额度
   - OCR/AI 额度

5. 通知与消息
   - 站内信入口
   - 系统通知

6. 隐私与说明
   - 加密说明
   - 管理员边界说明
   - 备份风险说明
   - 用户自己保管密码/PIN 的说明
   - 免责声明

设置页文案要诚实，但不要吓人。重点是让用户知道自己该负责什么，系统保护什么。

## 六、管理员后台应该做成什么

管理员后台应该是独立产品，不属于用户文件管理界面。

建议模块：

1. 总览
   - 用户数
   - 活跃用户
   - 今日上传
   - 总存储
   - worker 状态
   - 最近备份

2. 用户管理
   - 用户列表
   - role
   - plan
   - status
   - storage usage
   - storage limit
   - 封禁/解封
   - 重置配额

3. 套餐与配额
   - free/plus/pro/internal 配置
   - 分享限制
   - OCR 限制
   - AI 限制

4. 消息中心
   - 给所有用户发站内信
   - 给指定用户发站内信
   - 系统公告

5. 邀请
   - 创建邀请码
   - 管理邀请码
   - 邀请过期和使用记录

6. 审计
   - 登录
   - 上传
   - 下载
   - 分享
   - 管理员操作
   - 失败事件

7. 备份
   - 手动备份
   - 定时备份
   - 备份列表
   - 恢复说明

8. 文档智能和 worker
   - OCR 队列
   - AI 开关
   - 当前模型
   - 并发限制
   - 失败任务

## 七、Document Intelligence 文档智能蓝图

我同意你给出的方向：不要继续扩展“小票功能”，而是抽象成通用文档智能流水线。

目标流程：

```text
上传原件
-> 保存加密文件
-> 创建识别任务
-> 抽取文本
-> 判断文档类型
-> 提取结构化字段
-> 生成搜索索引
-> 用户确认或修正
```

### 1. 新表建议

`document_intelligence_tasks`

- id
- owner_id
- file_id
- source_type：file、photo、receipt、document、drop
- status：pending、processing、completed、failed、confirmed、skipped
- detected_type：receipt、invoice、contract、warranty、manual、statement、general、unknown
- raw_text
- parsed_json
- confidence
- error_message
- created_at
- updated_at
- finished_at

`document_profiles`

- id
- owner_id
- file_id
- title
- summary
- document_type
- primary_date
- amount
- currency
- issuer
- counterparty
- warranty_until
- serial_number
- keywords
- labels
- confirmed_at

`document_text_chunks`

- id
- owner_id
- file_id
- task_id
- page_number
- chunk_index
- text
- search_vector

### 2. Worker 改造

当前 worker 只处理 `receipt_ocr`。下一步应该改成 handler registry。

任务类型：

- `receipt_ocr`
- `document_extract_text`
- `document_classify`
- `document_parse`
- `document_index`
- `backup_run`

并发策略：

- OCR 1 到 2 个并发。
- AI 只允许 1 个并发。
- 备份不能重叠。
- 失败不影响上传。
- 每个任务类型有自己的超时和重试次数。

### 3. AI 使用策略

不要一开始就让 AI 全量参与。

正确顺序：

1. OCR 和规则先跑。
2. 先实现全文搜索。
3. 再做规则分类。
4. 最后接 Ollama 本地 AI。

790Pro 上建议：

- Ollama 独立跑宿主机。
- API、Worker、Postgres、Redis 继续 Docker Compose。
- Worker 调 `host.docker.internal:11434`。
- 默认 AI 关闭。
- AI 只看抽取后的文本，不直接看大图片。
- 长文档按 chunk 处理。
- 单 AI 任务 30 到 60 秒超时。

推荐模型可以从小模型开始：

- qwen2.5:3b
- gemma2:2b
- 或更轻的分类模型实验。

## 八、搜索应该怎么升级

当前搜索是前端聚合各模块后本地过滤。这个不够。

目标：

- 新增 `/api/v1/search`。
- 后端统一搜索。
- 搜索范围包括：
  - 文件名
  - 标签
  - 收据字段
  - 文档字段
  - OCR 文本
  - 摘要
  - 结构化字段

返回结果应该统一：

- type
- id
- title
- subtitle
- snippet
- thumbnail
- route/action

先用 Postgres full-text search，后面需要模糊匹配再加 trigram。

## 九、阶段推进方案

### Phase 0：当前工作树稳定化

目标：

确认当前已经做的功能能从空库和已有库稳定启动。

任务：

- 迁移从 0001 到最新全部可跑。
- 前端 build 通过。
- 后端 compile 通过。
- smoke test：
  - 登录
  - 文件上传下载
  - 照片列表
  - XuanDrop
  - public share 下载
  - important docs PIN
  - share archive

完成标准：

- `docker compose up --build` 可以新环境启动。
- 有效公开分享不会 500。
- XuanDrop 过期 session 不再当成活跃项展示。

### Phase 1：权限与管理员拆分

目标：

建立产品信任边界。

任务：

- 新增 token audience 或 account scope。
- 新增 `/admin/login`。
- 新增 `/admin-console`。
- 普通 AppShell 移除 Admin。
- user token 不能进 admin API。
- admin-console token 不能进用户文件 API。
- 用户表增加 `plan`。
- 上传时真正检查空间配额。

完成标准：

- 普通用户看不到 Admin。
- 管理员不能进入用户文件页面。
- 配额超过后上传被拒绝。

### Phase 2：设置页完整化

目标：

把用户自己的账号、安全、设备、空间、说明统一放进设置。

任务：

- 资料修改 API。
- 头像上传 API。
- 存储用量 API。
- 重要文件 PIN 管理入口。
- 设备撤销。
- 安全说明、隐私说明、免责声明。

完成标准：

- 用户能完整管理自己的账号。
- 用户能看懂系统保护什么、不保护什么。

### Phase 3：管理员后台第一版

目标：

让管理员后台独立成型。

任务：

- 独立 admin layout。
- 用户管理。
- plan/quota 管理。
- 邀请。
- 站内信。
- 审计。
- 备份。
- worker/OCR 状态。

完成标准：

- 管理员日常管理不需要进入用户 App。

### Phase 4：文档智能底座

目标：

所有图片/PDF/文档上传后都能创建通用识别任务。

任务：

- 新增文档智能表。
- worker dispatcher。
- 图片 OCR。
- PDF 文本抽取。
- 扫描 PDF 后续再增强。
- 文件详情页增加 Intelligence 区块。

完成标准：

- 上传图片或 PDF 后能看到识别状态和抽取文本。

### Phase 5：全文搜索

目标：

OCR 内容能被搜到。

任务：

- `/api/v1/search`。
- document_text_chunks 索引。
- 前端 SearchView 改成后端搜索。

完成标准：

- 搜索只存在于图片/PDF 内的文字，也能找到文件。

### Phase 6：规则分类和结构化字段

目标：

从“能搜”升级到“能理解是什么文档”。

任务：

- receipt/invoice/contract/warranty/manual/statement/general 分类。
- 不同 extractor。
- 用户确认和修正。
- 小票页面逐步迁移为 `detected_type=receipt` 的专用视图。

完成标准：

- 常见小票、发票、保修卡、合同能被分类并提取基础字段。

### Phase 7：本地 AI 增强

目标：

在不压垮 790Pro 的情况下，提高摘要、分类、字段提取质量。

任务：

- `DOCUMENT_AI_*` 配置。
- 默认关闭。
- 单并发。
- 超时。
- 失败回退规则。
- 管理后台可看到 AI 状态。

完成标准：

- AI 能增强已抽文本的分类和摘要，但上传流程不依赖 AI。

### Phase 8：开源与商业准备

目标：

让项目可以被陌生用户信任，也能保留商业路线。

任务：

- Threat Model。
- Security Model。
- Backup Guide。
- 790Pro Deployment Guide。
- License 说明。
- Privacy / Disclaimer 文案。
- Roadmap。

完成标准：

- 用户看仓库能明白怎么部署、怎么保护、有哪些限制。

## 十、下一步最应该做什么

我的建议顺序：

1. 先做 Phase 0，保证当前功能稳定。
2. 立刻做 Phase 1，拆管理员后台和普通用户前端。
3. 接着做 Phase 2，把设置页作为用户安全和账号中心。
4. 再做 Phase 3，补管理员后台的用户、配额、消息、worker 管理。
5. 然后启动 Phase 4 文档智能底座。

原因：

- 权限边界是信任基础。
- 设置页是用户理解产品安全边界的地方。
- 用户等级和配额是商业化基础。
- 文档智能会影响上传、搜索、worker、文件详情、小票等多个模块，应该在账户模型清楚后再做。

## 十一、近期 Sprint 建议

### Sprint A：权限边界

- `users.plan` 字段。
- admin-console token。
- user-app token。
- `/admin/login`。
- `/admin-console`。
- 移除用户壳里的 Admin。
- 路由守卫。
- 上传配额检查。

### Sprint B：用户设置

- 资料修改。
- 头像。
- 密码。
- 设备。
- 空间。
- 重要文件 PIN。
- 安全说明。
- 隐私/免责声明。

### Sprint C：管理员后台

- 用户管理。
- 用户等级。
- 空间限制。
- 封禁。
- 邀请。
- 消息。
- 审计。
- 备份。
- worker/OCR。

### Sprint D：文档智能底座

- 通用识别任务表。
- 文档 profile。
- 文本 chunks。
- worker dispatcher。
- 图片/PDF 抽取。
- 文件详情 Intelligence 区块。

## 十二、产品文案原则

建议以后所有安全文案都遵循这几条：

- 说“静态加密”，不要说“任何人永远无法访问”。
- 说“管理员管理账号和空间，不进入你的私人文件页面”。
- 说“服务器拥有者控制部署和备份位置”。
- 说“重要文件可以设置 PIN 保护”。
- 说“公开链接像钥匙，拿到链接和密码的人在有效期内可以访问”。
- 不要提前说“零知识”。
- 不要提前说“企业合规”。
- 不要默认说“AI 私密”，除非明确使用本地 AI 并说明配置。

## 十三、最终产品形态

XuanBox 最终应该分成三个产品面：

1. User Vault
   - 文件、照片、收据、文档、搜索、XuanDrop、分享、设置。

2. Admin Console
   - 用户、等级、配额、邀请、站内信、审计、备份、worker、系统健康。

3. Intelligence Layer
   - OCR、分类、摘要、结构化字段、全文搜索。

正确顺序是：

```text
先信任边界
再文档智能
最后商业包装
```

