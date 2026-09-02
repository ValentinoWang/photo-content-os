# 来源与当前代码基线

## 身份

- 要求来源：`agents-results/2026-09-01/openclaw-media-ui-prototype-and-checklist/openclaw-dev-checklist.html`
- 要求来源 SHA-256：`73554eb91c80c8a85b267f15dd07e7f89c06eeea27a907c254f00c35813b9eeb`
- 视觉原型：`agents-results/2026-09-01/openclaw-media-ui-prototype-and-checklist/openclaw-media-ui-prototype.html`
- 视觉原型 SHA-256：`aae220ef70cf7aeceefaf9a35ab4ee43d85366e92f2831513b53c36023a49cc8`
- 源码基线：`main@2b4f5c61f5cb3cc6a2284fcf19d22f3eaa1d5d35`，创建本 SSOT 时本地、跟踪分支与远端主分支一致。
- 新鲜回归基线：304 项通过，0 跳过。它只证明现有行为，不证明 45 项需求完成。

## 已接受的产品决定

以用户在本任务会话中的明确拍板为来源，登记为决定版本 1：

1. 整理台自动分事件、分批，但移动前必须由用户确认。
2. 素材库增加结构化索引，不删除现有卡片展示。
3. 生产删除只生成建议；用户勾选并二次确认后才进入当前操作系统回收站。
4. 创意模型由用户配置，可使用 Codex/OpenAI、Claude/Anthropic、DeepSeek 或兼容接口。
5. 本地剪辑工具（ChatCut）只通过桌面本地模型上下文协议（MCP）集成；只有实时探测成功且用户主动连接后才显示。
6. 归档同时配置生命周期和物理位置，每个位置独立保存清单、校验值和回读状态。
7. 上游账号配对是主动可选行为；未登录、未配对或平台不支持时，本地功能保持完整。
8. 结构化剪辑决策列表（`06_edit_decision_list.json`）是机器执行的唯一剪辑方案权威。
9. 剪映脚本只作历史材料；自动化不得修改生产剪映草稿。

## 45 项基线矩阵

| ID | 来源分组 | HTML 判定 | 当前审计判定 | 当前代码定位 | 条目内容 SHA-256 |
| --- | --- | --- | --- | --- | --- |
| D1 | 已拍板的三件事 | build | PARTIAL | `99_System_OpenClaw/scripts/01_scan_media_manifest.py:185` | `50d5bf241ee0a6f960fcc9f4ac16ea054d2b3a8810bba7930373d9fae8651bdf` |
| D2 | 已拍板的三件事 | build | PARTIAL | `99_System_OpenClaw/scripts/15_register_reusable_asset.py:66` | `302bfbb04e8a93b8ec4d4d81967dcc396aba1db3eade2e1f88c03269e5f0df96` |
| D3 | 已拍板的三件事 | build | PARTIAL | `99_System_OpenClaw/scripts/03_transcribe_audio.py:321` | `bdbc6e23c92d1e2efc5515f5b21faf1a9270024d3a89260b49cb3c4713cda87f` |
| A1 | 登录与安装向导 | build | PARTIAL | `99_System_OpenClaw/desktop/upstream_session.py:70` | `d40f9c169b8d069256d430ba99478845bedc4d4ee63c067a78d94e7e5ea9f4e2` |
| A2 | 登录与安装向导 | ready | PARTIAL | `99_System_OpenClaw/scripts/41_setup_dev_environment.sh:6` | `53e9fe7d17a4168e57739b6ab1627e6701db53714e3bf46548635bd7b80c089d` |
| H1 | 工作台 | ready | PARTIAL | `99_System_OpenClaw/desktop/project_store.py:334` | `62505f0198d94492f7928a09ac65eef3cb47ae987a251f9bf2e69a12f276fe60` |
| H2 | 工作台 | build | PARTIAL | `99_System_OpenClaw/desktop/server.py:380` | `f41f5f096b62a26cf2abce887bfa589f1d95645f3af3d9974e1b363467c24c69` |
| H3 | 工作台 | build | NOT_READY | `99_System_OpenClaw/scripts/15_register_reusable_asset.py:22` | `1e441c9f3b9c026906311db527424ed651d5d86e0007485a54a0ce603dd7aa44` |
| H4 | 工作台 | build | NOT_READY | `99_System_OpenClaw/desktop/project_store.py:529` | `7c963a415ec7a8d8d2b61f93c771c2094a55e4fddab31c2561b6a326c3ef7555` |
| I1 | 整理台 | build | NOT_READY | `99_System_OpenClaw/scripts/34_ensure_project_from_inbox_batch.py:18` | `e930dc68a37eac1397c3c5aac431b9b5f789c8a98c263ae8fdc15ffdd37d5659` |
| I2 | 整理台 | ready | PARTIAL | `99_System_OpenClaw/scripts/01_scan_media_manifest.py:1` | `b719c64ccef84189369b8f959d5ebdf48f56f6cbaeab847a314e1377652742cc` |
| I3 | 整理台 | build | PARTIAL | `99_System_OpenClaw/scripts/12_select_repeat_photo_groups.py:98` | `5d10cf7c10d68902b1776ff7e73c4e0020a676ad5d8d10ff1804ce903ea933f0` |
| I4 | 整理台 | build | PARTIAL | `99_System_OpenClaw/scripts/media_delete_recommendations.py:2` | `84db19eaa6c87a0f3643d301c8163ee300b9549c2cc810f24ec1821df74eec49` |
| I5 | 整理台 | fix | PARTIAL_PLATFORM | `99_System_OpenClaw/desktop/media_trash_flow.py:missing` | `70832037ae6b44e53213ae2dda34fc5d414efd386994fa7cb4a00c3c1b6618cc` |
| L1 | 素材库 | build | NOT_READY | `99_System_OpenClaw/scripts/15_register_reusable_asset.py:66` | `0d73f9f416d542b54dda41d761623095dbc0ddaffc61f58fe764ddcb5fad362a` |
| L2 | 素材库 | build | NOT_READY | `99_System_OpenClaw/scripts/15_register_reusable_asset.py:73` | `3eacbc24ba837aa8bd0ddacae52aeea7904ef6ba12bcb52773512ac0ab3d0109` |
| L3 | 素材库 | ready | PARTIAL | `99_System_OpenClaw/scripts/45_archive_project.py:43` | `f3f4c0356d08bf80f59c2745b0411c38153d856685ce67ac6185935443553af7` |
| L4 | 素材库 | ready | PARTIAL | `99_System_OpenClaw/scripts/45_archive_project.py:73` | `be32d0ad62be4d29aff05a52891e6c1e633c5f1ac53fc62aab0ae880d6df0236` |
| L5 | 素材库 | fix | NOT_READY | `99_System_OpenClaw/scripts/17_match_materials_to_brief.py:224` | `fe8ff8cea2b42eb4d4968a00169178d2e7f580440cb21deb1e59f626efc3a468` |
| P1 | 项目 | ready | PARTIAL | `99_System_OpenClaw/desktop/edl_bridge.py:1` | `d0c0fb4d0b7fe31fa5222c5dd3051d917766243ebb6672b553e12f3f0e56aa84` |
| P2 | 项目 | ready | NOT_READY | `99_System_OpenClaw/scripts/edit_backends/otio_kdenlive.py:58` | `370b1698151feaf7ceb610cf60406cd76144b7fad3330ae7f30e7bb10eec86f5` |
| P3 | 项目 | fix | NOT_USER_ACCESSIBLE | `99_System_OpenClaw/desktop/static/app.js:1` | `1645f1d6a7c955af49b7c5e6ad1d2a75c526be0fe9caa9ba9e34aa814117cf7a` |
| P4 | 项目 | ready | PARTIAL | `99_System_OpenClaw/schemas/edit_decision_list.schema.json:15` | `25593a521d90e2eb47bf0c362b6c4383925f61eda461f4df50f46b1102a8bea1` |
| P5 | 项目 | ready | PARTIAL | `99_System_OpenClaw/scripts/validate_content_os_task.py:28` | `6ebf1e44e88d8d87909ee4bc4c029f91aeddaa85360b0d564f61b2b9c736b654` |
| P6 | 项目 | fix | POLICY_ONLY | `99_System_OpenClaw/docs/05_剪映与HyperFrames.md:7` | `9d469e28dfa340c499040faf057c439855579f276eac1792eaa5c40ecc836dac` |
| S1 | 设置与诊断 | ready | PARTIAL | `99_System_OpenClaw/scripts/analysis_tiering.py:73` | `78a6ab868a769129410aae2fb2513ad4c457c71d1538428fdb3d821a38783aa4` |
| S2 | 设置与诊断 | ready | PARTIAL | `99_System_OpenClaw/desktop/archive_location_config.py:2` | `101f030d1ab26f50041c43f6a7ad9225760ac725189e3ba89c3c5f3a7b50ac2c` |
| S3 | 设置与诊断 | ready | PARTIAL | `99_System_OpenClaw/scripts/43_content_os_doctor.py:64` | `f07a378f3eb22333d54a54155a726e875cabe52857a1f16c3e5e014fe3570062` |
| S4 | 设置与诊断 | fix | PARTIAL | `99_System_OpenClaw/desktop/upstream_session.py:24` | `8239734c0bbbf58452e353c9136b99ab1c27bde6f7222e6076992a7c6b883132` |
| S5 | 设置与诊断 | build | PARTIAL | `99_System_OpenClaw/desktop/model_provider_config.py:1` | `2f7ec9554acd857ecc0589a2b27dc2f603093722e9dff60cf49ea3de872ec47b` |
| C1 | 网页中台 | ready | PARTIAL | `99_System_OpenClaw/schemas/openclaw_media_contract_snapshot.json:11` | `1a9ea657fb57b959790247c969ea8605269fb46f91dbeefcc43b17d37f5789f3` |
| C2 | 网页中台 | ready | NOT_READY | `99_System_OpenClaw/schemas/openclaw_media_contract_snapshot.json:10` | `501345c132e3c972b49713e5532752f075e73391517f8c9ee53480561ffced3c` |
| C3 | 网页中台 | fix | PARTIAL | `99_System_OpenClaw/schemas/openclaw_media_contract_snapshot.json:4` | `bee98ec69fd375563b3356c2040da7cb82d26ff015dbf4448a7dbd7c2b523818` |
| T1 | 接界面之前该还的债 | build | PARTIAL | `99_System_OpenClaw/tests/test_promote_inbox_batch_to_project.py:41` | `56383d571da30fb227a738021ab02cd4a8ac6294631b56f2fe5b36941b8754ae` |
| T2 | 接界面之前该还的债 | build | NOT_READY | `99_System_OpenClaw/scripts/12_select_repeat_photo_groups.py:284` | `3ba7338a27bb54f01b8cd5f14059a6764498a753e0de93de5aea58a1e8757da2` |
| T3 | 接界面之前该还的债 | build | PARTIAL | `99_System_OpenClaw/tests/test_media_manifest_contract.py:59` | `b0981754873ca3edb7a7bc315038902d3fcda032a95e93432b758e017484e6ef` |
| T4 | 接界面之前该还的债 | build | NOT_READY | `99_System_OpenClaw/scripts/analysis_tiering.py:20` | `bca41792617d2f3beaa2391cdcb018ed705f53f9eb0904cf407531fa2fa4b7c8` |
| T5 | 接界面之前该还的债 | ready | PARTIAL | `99_System_OpenClaw/desktop/server.py:349` | `cc526f681ae04ad05ec73433cf1db27dfcb6a9fbf76a9b41358dc31b32cb7470` |
| T6 | 接界面之前该还的债 | build | PARTIAL | `99_System_OpenClaw/scripts/README.md:3` | `249ca4346591ecb296047cd340b529767719c20b24d26ef9033c9f45cf776c60` |
| K1 | 换界面时不要丢的东西 | fix | PARTIAL | `99_System_OpenClaw/desktop/ai_patch.py:2` | `9e11aa783e5209a85b2e38ebceb1d0da2f8c92a1cd8222d4a3dbc7466780c041` |
| K2 | 换界面时不要丢的东西 | fix | PARTIAL | `99_System_OpenClaw/desktop/project_store.py:5` | `a76f17510c99f03520f67e962fcb00ddc77c8725b2a453455a706fbb6862d7c2` |
| K3 | 换界面时不要丢的东西 | fix | PARTIAL | `99_System_OpenClaw/desktop/project_store.py:155` | `bb42356400e18dbe3c6cab632a28bddbf5dbc0b514d898f467272d63a3a5025d` |
| K4 | 换界面时不要丢的东西 | fix | PARTIAL | `99_System_OpenClaw/desktop/project_store.py:31` | `1b251c23eb82cdd0ef41c730c2fe0b3f2d5b225b2a7ec4070a86d167755d6c16` |
| K5 | 换界面时不要丢的东西 | fix | PARTIAL | `99_System_OpenClaw/desktop/project_store.py:28` | `292a85f96b6f474aff295829bca32be75b4510d32560dd76c63820ba0f4fe033` |
| K6 | 换界面时不要丢的东西 | fix | PARTIAL | `99_System_OpenClaw/scripts/mac_openclaw_runner.py:594` | `23c574c4a58e433ade1f16544530a3befec922bda085b76266b5ae5d219c069b` |

## 证据边界

原 HTML 中的“可直接接”是设计阶段判断，不是当前验收状态。上表重新绑定当前主分支；所有 45 项仍需独立合同、受保护测试、本地运行或外部证据和最终九屏人工验收。
