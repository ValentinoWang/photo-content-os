# 制作台后端平铺目录拆分方案（BE-38）

按 Backend_Flow 代码组织体检「目录太平」4 处命中（`studio/` 29→30、`scripts/edit_backends/` 16→17、`scripts/music_library/` 16→17、`scripts/` 101→102）按领域分层拆分。拆分目标：
- 每个目录直接放置的 `.py` 文件数 **≤ 15**（含 `__init__.py`、`constants.py`）。
- 文件名不重复所在目录名、不引入冗余前后缀（`_common` / `_helper` / `_service` / `_v2` 等）。
- 对外核心入口（`scripts/launch_studio.py`、`scripts/doctor.py`、`scripts/media.py`、`scripts/llm.py`、`scripts/runtime_paths.py`、`scripts/edl_contract.py`、`scripts/run_analyze_project.py`、静态门禁入口等）保留在 `scripts/` 顶层，避免破坏外部启动器和适配配置。

---

## 1. `studio/`（30 → 顶层 13 + 3 个领域子包）

顶层保留（13 个）：`__init__.py`、`constants.py`、`server.py`、`api_contract.py`、`project_store.py`、`work_trash.py`、`ai_patch.py`、`media_review.py`、`review_jobs.py`、`edl_bridge.py`、`returned_candidate.py`、`video_workflow.py`、`music_analysis.py`。

| 领域子包 | 旧路径 | 新路径 |
| --- | --- | --- |
| `studio/direct/`（6） | `studio/direct_handoff_contract.py` | `studio/direct/handoff_contract.py` |
| `studio/direct/` | `studio/direct_recipes.py` | `studio/direct/recipes.py` |
| `studio/direct/` | `studio/direct_revision_contract.py` | `studio/direct/revision_contract.py` |
| `studio/direct/` | `studio/direct_style_contract.py` | `studio/direct/style_contract.py` |
| `studio/direct/` | `studio/direct_video.py` | `studio/direct/video.py` |
| `studio/roughcut/`（6） | `studio/roughcut.py` | `studio/roughcut/application.py` |
| `studio/roughcut/` | `studio/roughcut_drafts.py` | `studio/roughcut/drafts.py` |
| `studio/roughcut/` | `studio/roughcut_jobs.py` | `studio/roughcut/jobs.py` |
| `studio/roughcut/` | `studio/roughcut_store.py` | `studio/roughcut/store.py` |
| `studio/roughcut/` | `studio/roughcut_transcription.py` | `studio/roughcut/transcription.py` |
| `studio/settings/`（8） | `studio/analysis_budget.py` | `studio/settings/analysis_budget.py` |
| `studio/settings/` | `studio/archive_location_config.py` | `studio/settings/archive_location_config.py` |
| `studio/settings/` | `studio/chatcut_mcp.py` | `studio/settings/chatcut_mcp.py` |
| `studio/settings/` | `studio/model_provider_config.py` | `studio/settings/model_provider_config.py` |
| `studio/settings/` | `studio/onboarding_state.py` | `studio/settings/onboarding_state.py` |
| `studio/settings/` | `studio/upstream_identity.py` | `studio/settings/upstream_identity.py` |
| `studio/settings/` | `studio/upstream_session.py` | `studio/settings/upstream_session.py` |

---

## 2. `scripts/edit_backends/`（17 → 顶层 7 + `editors/` 11）

顶层保留（7 个）：`__init__.py`、`constants.py`、`interface.py`、`registry.py`、`execution.py`、`handoff_pack.py`、`precut.py`。

| 领域子包 | 旧路径 | 新路径 |
| --- | --- | --- |
| `scripts/edit_backends/editors/`（11） | `scripts/edit_backends/chatcut_adapter.py` | `scripts/edit_backends/editors/chatcut_adapter.py` |
| `scripts/edit_backends/editors/` | `scripts/edit_backends/chatcut_handoff.py` | `scripts/edit_backends/editors/chatcut_handoff.py` |
| `scripts/edit_backends/editors/` | `scripts/edit_backends/concat_adapter.py` | `scripts/edit_backends/editors/concat_adapter.py` |
| `scripts/edit_backends/editors/` | `scripts/edit_backends/concat_mcp.py` | `scripts/edit_backends/editors/concat_mcp.py` |
| `scripts/edit_backends/editors/` | `scripts/edit_backends/kdenlive_adapter.py` | `scripts/edit_backends/editors/kdenlive_adapter.py` |
| `scripts/edit_backends/editors/` | `scripts/edit_backends/kdenlive_readback.py` | `scripts/edit_backends/editors/kdenlive_readback.py` |
| `scripts/edit_backends/editors/` | `scripts/edit_backends/kdenlive_render.py` | `scripts/edit_backends/editors/kdenlive_render.py` |
| `scripts/edit_backends/editors/` | `scripts/edit_backends/openchatcut_adapter.py` | `scripts/edit_backends/editors/openchatcut_adapter.py` |
| `scripts/edit_backends/editors/` | `scripts/edit_backends/openfilm_adapter.py` | `scripts/edit_backends/editors/openfilm_adapter.py` |
| `scripts/edit_backends/editors/` | `scripts/edit_backends/otio_kdenlive.py` | `scripts/edit_backends/editors/otio_kdenlive.py` |

---

## 3. `scripts/music_library/`（17 → 顶层 10 + `sources/` 8）

顶层保留（10 个）：`__init__.py`、`constants.py`、`errors.py`、`audio.py`、`cache.py`、`library.py`、`links.py`、`network.py`、`egress.py`、`platforms.py`。

| 领域子包 | 旧路径 | 新路径 |
| --- | --- | --- |
| `scripts/music_library/sources/`（8） | `scripts/music_library/ai_generate.py` | `scripts/music_library/sources/ai_generate.py` |
| `scripts/music_library/sources/` | `scripts/music_library/browser_cookies.py` | `scripts/music_library/sources/browser_cookies.py` |
| `scripts/music_library/sources/` | `scripts/music_library/client_files.py` | `scripts/music_library/sources/client_files.py` |
| `scripts/music_library/sources/` | `scripts/music_library/douyin_api.py` | `scripts/music_library/sources/douyin_api.py` |
| `scripts/music_library/sources/` | `scripts/music_library/douyin_share.py` | `scripts/music_library/sources/douyin_share.py` |
| `scripts/music_library/sources/` | `scripts/music_library/musicdl_engine.py` | `scripts/music_library/sources/musicdl_engine.py` |
| `scripts/music_library/sources/` | `scripts/music_library/netease.py` | `scripts/music_library/sources/netease.py` |

---

## 4. `scripts/`（102 → 顶层 14 + 9 个领域子包）

顶层保留（14 个）：`constants.py`、`runtime_paths.py`、`media.py`、`llm.py`、`edl_contract.py`、`document_contract.py`、`launch_studio.py`、`doctor.py`、`run_analyze_project.py`、`check_repository_safety.py`、`check_obsidian_doc_sync.py`、`check_outline_contract.py`、`validate_music_analysis_registry.py`、`validate_content_os_task.py`。

| 领域子包 | 旧路径 | 新路径 |
| --- | --- | --- |
| `scripts/intake/`（13） | `scripts/ensure_project_structure.py` | `scripts/intake/ensure_project_structure.py` |
| `scripts/intake/` | `scripts/ensure_project_from_inbox_batch.py` | `scripts/intake/ensure_project_from_inbox_batch.py` |
| `scripts/intake/` | `scripts/project_bootstrap.py` | `scripts/intake/project_bootstrap.py` |
| `scripts/intake/` | `scripts/plan_inbox_batches.py` | `scripts/intake/plan_inbox_batches.py` |
| `scripts/intake/` | `scripts/promote_inbox_batch_to_project.py` | `scripts/intake/promote_inbox_batch_to_project.py` |
| `scripts/intake/` | `scripts/link_batch_to_content_project.py` | `scripts/intake/link_batch_to_content_project.py` |
| `scripts/intake/` | `scripts/plan_additions_merge.py` | `scripts/intake/plan_additions_merge.py` |
| `scripts/intake/` | `scripts/apply_additions_merge.py` | `scripts/intake/apply_additions_merge.py` |
| `scripts/intake/` | `scripts/select_repeat_photo_groups.py` | `scripts/intake/select_repeat_photo_groups.py` |
| `scripts/intake/` | `scripts/archive_project.py` | `scripts/intake/archive_project.py` |
| `scripts/intake/` | `scripts/asset_library_index.py` | `scripts/intake/asset_library_index.py` |
| `scripts/intake/` | `scripts/register_reusable_asset.py` | `scripts/intake/register_reusable_asset.py` |
| `scripts/media_ops/`（11） | `scripts/scan_media_manifest.py` | `scripts/media_ops/scan_media_manifest.py` |
| `scripts/media_ops/` | `scripts/validate_media_decisions.py` | `scripts/media_ops/validate_media_decisions.py` |
| `scripts/media_ops/` | `scripts/rename_media_file.py` | `scripts/media_ops/rename_media_file.py` |
| `scripts/media_ops/` | `scripts/media_delete_recommendations.py` | `scripts/media_ops/media_delete_recommendations.py` |
| `scripts/media_ops/` | `scripts/media_trash_flow.py` | `scripts/media_ops/media_trash_flow.py` |
| `scripts/media_ops/` | `scripts/media_project_selection.py` | `scripts/media_ops/media_project_selection.py` |
| `scripts/media_ops/` | `scripts/migrate_media_layout.py` | `scripts/media_ops/migrate_media_layout.py` |
| `scripts/media_ops/` | `scripts/migrate_project_metadata.py` | `scripts/media_ops/migrate_project_metadata.py` |
| `scripts/media_ops/` | `scripts/rollback_media_migration.py` | `scripts/media_ops/rollback_media_migration.py` |
| `scripts/media_ops/` | `scripts/distribute_group_photos_by_name.py` | `scripts/media_ops/distribute_group_photos_by_name.py` |
| `scripts/pipeline/`（12） | `scripts/analysis_tiering.py` | `scripts/pipeline/analysis_tiering.py` |
| `scripts/pipeline/` | `scripts/extract_audio.py` | `scripts/pipeline/extract_audio.py` |
| `scripts/pipeline/` | `scripts/extract_keyframes.py` | `scripts/pipeline/extract_keyframes.py` |
| `scripts/pipeline/` | `scripts/transcribe_audio.py` | `scripts/pipeline/transcribe_audio.py` |
| `scripts/pipeline/` | `scripts/transcript_to_srt.py` | `scripts/pipeline/transcript_to_srt.py` |
| `scripts/pipeline/` | `scripts/write_content_summary.py` | `scripts/pipeline/write_content_summary.py` |
| `scripts/pipeline/` | `scripts/prepare_studio_media.py` | `scripts/pipeline/prepare_studio_media.py` |
| `scripts/pipeline/` | `scripts/shot_aesthetics.py` | `scripts/pipeline/shot_aesthetics.py` |
| `scripts/pipeline/` | `scripts/shot_previews.py` | `scripts/pipeline/shot_previews.py` |
| `scripts/pipeline/` | `scripts/shot_quality.py` | `scripts/pipeline/shot_quality.py` |
| `scripts/pipeline/` | `scripts/select_shots.py` | `scripts/pipeline/select_shots.py` |
| `scripts/creative/`（12） | `scripts/llm_evidence_context.py` | `scripts/creative/llm_evidence_context.py` |
| `scripts/creative/` | `scripts/generate_ai_prompt.py` | `scripts/creative/generate_ai_prompt.py` |
| `scripts/creative/` | `scripts/match_materials_to_brief.py` | `scripts/creative/match_materials_to_brief.py` |
| `scripts/creative/` | `scripts/generate_storyboard_edl.py` | `scripts/creative/generate_storyboard_edl.py` |
| `scripts/creative/` | `scripts/generate_ai_edit_log.py` | `scripts/creative/generate_ai_edit_log.py` |
| `scripts/creative/` | `scripts/review_output_video.py` | `scripts/creative/review_output_video.py` |
| `scripts/creative/` | `scripts/audio_plan.py` | `scripts/creative/audio_plan.py` |
| `scripts/creative/` | `scripts/render_preview.py` | `scripts/creative/render_preview.py` |
| `scripts/creative/` | `scripts/spoken_edit.py` | `scripts/creative/spoken_edit.py` |
| `scripts/creative/` | `scripts/roughcut_capabilities.py` | `scripts/creative/roughcut_capabilities.py` |
| `scripts/creative/` | `scripts/roughcut_planner.py` | `scripts/creative/roughcut_planner.py` |
| `scripts/video_tools/`（10） | `scripts/video_black_frames.py` | `scripts/video_tools/video_black_frames.py` |
| `scripts/video_tools/` | `scripts/video_candidate.py` | `scripts/video_tools/video_candidate.py` |
| `scripts/video_tools/` | `scripts/video_derivatives.py` | `scripts/video_tools/video_derivatives.py` |
| `scripts/video_tools/` | `scripts/video_subtitle_bilingual.py` | `scripts/video_tools/video_subtitle_bilingual.py` |
| `scripts/video_tools/` | `scripts/video_subtitles.py` | `scripts/video_tools/video_subtitles.py` |
| `scripts/video_tools/` | `scripts/generate_avatar_clip.py` | `scripts/video_tools/generate_avatar_clip.py` |
| `scripts/video_tools/` | `scripts/generate_music.py` | `scripts/video_tools/generate_music.py` |
| `scripts/video_tools/` | `scripts/import_music.py` | `scripts/video_tools/import_music.py` |
| `scripts/video_tools/` | `scripts/migrate_music_library.py` | `scripts/video_tools/migrate_music_library.py` |
| `scripts/bridge/`（12） | `scripts/enqueue_openclaw_queue_job.py` | `scripts/bridge/enqueue_openclaw_queue_job.py` |
| `scripts/bridge/` | `scripts/mac_openclaw_runner.py` | `scripts/bridge/mac_openclaw_runner.py` |
| `scripts/bridge/` | `scripts/process_openclaw_queue.py` | `scripts/bridge/process_openclaw_queue.py` |
| `scripts/bridge/` | `scripts/queue_identity.py` | `scripts/bridge/queue_identity.py` |
| `scripts/bridge/` | `scripts/openclaw_media_agent.py` | `scripts/bridge/openclaw_media_agent.py` |
| `scripts/bridge/` | `scripts/openclaw_product_contract.py` | `scripts/bridge/openclaw_product_contract.py` |
| `scripts/bridge/` | `scripts/openclaw_video_execution.py` | `scripts/bridge/openclaw_video_execution.py` |
| `scripts/bridge/` | `scripts/refresh_openclaw_media_contract_snapshot.py` | `scripts/bridge/refresh_openclaw_media_contract_snapshot.py` |
| `scripts/bridge/` | `scripts/upstream_identity.py` | `scripts/bridge/upstream_identity.py` |
| `scripts/bridge/` | `scripts/migrate_content_os.py` | `scripts/bridge/migrate_content_os.py` |
| `scripts/bridge/` | `scripts/validate_state_transition.py` | `scripts/bridge/validate_state_transition.py` |
| `scripts/legacy_jianying/`（10） | `scripts/jianying_roughcut.py` | `scripts/legacy_jianying/jianying_roughcut.py` |
| `scripts/legacy_jianying/` | `scripts/create_jianying_roughcut_draft.py` | `scripts/legacy_jianying/create_jianying_roughcut_draft.py` |
| `scripts/legacy_jianying/` | `scripts/create_native_import_pack.py` | `scripts/legacy_jianying/create_native_import_pack.py` |
| `scripts/legacy_jianying/` | `scripts/generate_jianying_draft_plan.py` | `scripts/legacy_jianying/generate_jianying_draft_plan.py` |
| `scripts/legacy_jianying/` | `scripts/generate_jianying_import_readme.py` | `scripts/legacy_jianying/generate_jianying_import_readme.py` |
| `scripts/legacy_jianying/` | `scripts/probe_jianying_environment.py` | `scripts/legacy_jianying/probe_jianying_environment.py` |
| `scripts/legacy_jianying/` | `scripts/validate_jianying_draft.py` | `scripts/legacy_jianying/validate_jianying_draft.py` |
| `scripts/legacy_jianying/` | `scripts/validate_native_import_pack.py` | `scripts/legacy_jianying/validate_native_import_pack.py` |
| `scripts/legacy_jianying/` | `scripts/rewrite_media_references.py` | `scripts/legacy_jianying/rewrite_media_references.py` |
| `scripts/qa/`（8） | `scripts/capture_nfd_gallery.py` | `scripts/qa/capture_nfd_gallery.py` |
| `scripts/qa/` | `scripts/compare_r220_screenshots.py` | `scripts/qa/compare_r220_screenshots.py` |
| `scripts/qa/` | `scripts/measure_r227_real_audio.py` | `scripts/qa/measure_r227_real_audio.py` |
| `scripts/qa/` | `scripts/verify_r227_real_audio.py` | `scripts/qa/verify_r227_real_audio.py` |
| `scripts/qa/` | `scripts/r275_browser_fixture.py` | `scripts/qa/r275_browser_fixture.py` |
| `scripts/qa/` | `scripts/r275_screenshot_bundle.py` | `scripts/qa/r275_screenshot_bundle.py` |
| `scripts/qa/` | `scripts/check_r223_design.py` | `scripts/qa/check_r223_design.py` |
| `scripts/tooling/`（9） | `scripts/check_runtime_contract.py` | `scripts/tooling/check_runtime_contract.py` |
| `scripts/tooling/` | `scripts/check_obsidian_links.py` | `scripts/tooling/check_obsidian_links.py` |
| `scripts/tooling/` | `scripts/sync_obsidian_docs.py` | `scripts/tooling/sync_obsidian_docs.py` |
| `scripts/tooling/` | `scripts/validate_review_capability_registry.py` | `scripts/tooling/validate_review_capability_registry.py` |
| `scripts/tooling/` | `scripts/export_studio_openapi.py` | `scripts/tooling/export_studio_openapi.py` |
| `scripts/tooling/` | `scripts/edit_tools_runtime.py` | `scripts/tooling/edit_tools_runtime.py` |
| `scripts/tooling/` | `scripts/setup_edit_tools.py` | `scripts/tooling/setup_edit_tools.py` |
| `scripts/tooling/` | `scripts/create_demo_project.py` | `scripts/tooling/create_demo_project.py` |
