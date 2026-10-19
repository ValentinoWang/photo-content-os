# Acceptance Contract: 2026-10-19-R210-photo-music-link-import

- Task ID: 2026-10-19-R210-photo-music-link-import
- Contract version: 1
- Contract status: APPROVED
- Test baseline: LOCKED
- Acceptance owner: 任务委托人
- Approval evidence: 用户 2026-10-20 阶段 2f 指令：提交既有成果，抖音待处理及会员样例缺口如实递交；不代签人工通过
- Request source: acceptance/requests/2026-W43/2026-10-19-R210-photo-music-link-import/request.json; evidence/2026-10-20/r210-music-link-import/delivery/scope.md
- SSOT node: none
- SSOT path: none
- Readiness mode: FORMAL
- Decision refs: none
- Assumption IDs: none
- Invalidation keys: music.import
- AC budget: 3
- Baseline identity: cd7a30e; 用户阶段 2f 指令
- Product Context refs: none
- Role Context refs: none
- Resolved Surface Contract refs: none
- Screen Contract ref: none
- Visual Contract refs: none
- UI Change declaration: none
- Human acceptance workspace: acceptance/human/2026-W43/2026-10-19-R210-photo-music-link-import


## User and scenario

本机用户粘贴单曲、视频或图文作品的分享文字，或导入客户端下载的音频。只使用命令行，不增加页面。

## Problem

已有网易云和汽水实际成功；抖音匿名签名作品接口已用满额度，分享页也没有提供作品音乐。失败必须透明保留，不能伪造三首导入成功。

## Expected outcome

有完整可核验音源时入库并记录元数据、授权和测量；已入库输入不重复联网；不可读或受限响应明确失败，不产生残缺条目。三平台完整目标仍由 H-01 保留，当前抖音待处理。

## Non-goals

不批量抓取、不绕过会员、不读抖音浏览器登录态、不发布作品、不删除另一个仓库的旧工具、不修改真实剪映草稿。

## Normal path

Given 单首分享输入或本地文件；When 执行导入；Then 查库后按授权节点取数，完整性和授权校验通过再原子写入库，重复输入直接返回已在库里。

## Exception paths

会员、地区限制、HTTP 错误、无作品音乐、跳转、半下载、缓存不可读或代理失败均报错；不自动重试，不回退直连或签名作品接口。只有新的明确授权可安排独立请求，历史记录保留。

## Invariants

素材根只从 runtime_paths 获取；原文件不动；平台曲为 platform_copyrighted；未知授权不可发布；来源与索引一致；重复不打开隧道；匿名抖音分享不带 Cookie、不跟随跳转。

## Data impact

库内写音频、track.json、索引及私有尝试/响应缓存；按平台编号及音频哈希去重；失败不写条目；写入失败回滚，不删除历史缓存。

## Permissions

仅用户授权的本机导入与单节点请求；出口配置和匿名凭据位于仓库外；只有用户或总控可授权重新联网和决定下一步登录态。人工结果由用户签署。

## Performance and reliability

每请求禁用自动重试，30 秒请求超时；先持久记录后发送；隧道按需启动并在退出时关闭。时长与平台详情差不超过 2 秒。

## Acceptance criteria

| ID | Class | Lane | Requirement | Verification layer | Mode | Blocking |
| --- | --- | --- | --- | --- | --- | --- |
| AC-01 | behavior | machine/integration-contract | 可核验完整音源按元数据和授权入库；缺失作品数据或会员/地区限制明确失败且不留残缺条目 | Integration | Automatic | Yes |
| AC-02 | behavior | machine/integration-contract | 平台编号及音频哈希去重，重复导入零请求且不启动隧道；本地加密文件原件不动 | Integration | Automatic | Yes |
| AC-03 | behavior | machine/integration-contract | 匿名手机分享不跟随跳转，缓存重放不联网；代理失败不回直连，退出关闭隧道 | Integration | Automatic | Yes |

## Human acceptance

| ID | Summary | Checklist path | Required role | Blocking |
| --- | --- | --- | --- | --- |
| H-01 | 三平台真实导入体验；当前抖音待处理，不能判通过 | acceptance/human/2026-W43/2026-10-19-R210-photo-music-link-import/checklist.md#h-01 | 产品负责人 | Yes |
| H-02 | 已入库歌曲重复导入体验 | acceptance/human/2026-W43/2026-10-19-R210-photo-music-link-import/checklist.md#h-02 | 产品负责人 | Yes |
| H-03 | 真实会员曲边界；待用户提供会员曲链接 | acceptance/human/2026-W43/2026-10-19-R210-photo-music-link-import/checklist.md#h-03 | 产品负责人 | Yes |

## Protected acceptance tests

| Path | SHA-256 | Covers |
| --- | --- | --- |
| tests/test_music_library.py | 5ca163c44c0b30b61e3ab7b023d43dc961bfd1bae0746d7077ecaa533ff2df1e | AC-01, AC-02, AC-03 |
| tests/test_music_network.py | 6c7b0dfd9ada9c8d518c776be90ffd9d676db6593b1062c99760419ca322eafe | AC-01, AC-02, AC-03 |
| tests/test_musicdl_engine.py | 3002c872f10f9ca590dc91932564e03db7e6cd938c1294a8a5b0bc29eea6d85d | AC-01, AC-02, AC-03 |
| tests/test_music_egress.py | c90fc2903577034b315fe1c4e72a345deac38128e3a27121068a095bed788fef | AC-01, AC-02, AC-03 |
| tests/test_douyin_music_api.py | b78aa7e0af9d67513c8001724b9b6c9f09f7552f21b93371e059fddc0760d017 | AC-01, AC-02, AC-03 |
| tests/test_douyin_share_page.py | b221d275bc7a7f6bda384e5b2e129a5659d019bf3b6eeea5455d140871939701 | AC-01, AC-02, AC-03 |

## Requirements-test traceability

| Requirement | Verification | Evidence target | Mode | Blocking |
| --- | --- | --- | --- | --- |
| AC-01 | 离线协议与失败隔离测试；已有两首实际音频本地核验 | tests/test_music_library.py; tests/test_musicdl_engine.py; tests/test_douyin_share_page.py | Automatic | Yes |
| AC-02 | 去重及本地文件测试、真实两首重复验证 | tests/test_music_library.py; tests/test_music_egress.py | Automatic | Yes |
| AC-03 | 匿名与缓存、跳转及隧道生命周期测试 | tests/test_music_network.py; tests/test_douyin_share_page.py; tests/test_music_egress.py | Automatic | Yes |
| H-01 | 用户真实体验，当前抖音缺失 | acceptance/human/2026-W43/2026-10-19-R210-photo-music-link-import/checklist.md#h-01 | Human | Yes |
| H-02 | 用户选择已入库歌曲重复导入 | acceptance/human/2026-W43/2026-10-19-R210-photo-music-link-import/checklist.md#h-02 | Human | Yes |
| H-03 | 用户提供会员曲后再安排 | acceptance/human/2026-W43/2026-10-19-R210-photo-music-link-import/checklist.md#h-03 | Human | Yes |

## Exploratory testing

真实手机分享页仅一次匿名请求并离线检查全部嵌入数据；不得为了探索追加 API 或读取登录态。

## Production monitoring and rollback

本任务无部署。CLI 失败提示和私有缓存保留；发现残缺条目或来源/授权错误立即停止后续导入，维护者先离线检查。回滚软件提交不删除用户音乐或原始文件。

## Risks and open decisions

抖音分享页 HTTP 200 只有页面配置，没有音乐。是否使用用户登录态由总控另行询问；本任务不作此决定。不具备完整三平台交付证据，禁止推送；真实会员曲仍无样例。
