# Machine evidence

- Run ID: org-cleanup-flat
- Status: PASS
- Source identity: a266fcf78ec9b54473928fdbf6b083048e3cba06
- Layer: machine/unit

## Execution

Recorded at: 2026-11-28T16:28:36.043796+00:00

## Command 1

```
nice -n 10 /usr/bin/perl -e 'alarm 60; exec @ARGV' /Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python -m compileall -q /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/studio /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/scripts
```

Exit code: 0

```

```

## Command 2

```
nice -n 10 /usr/bin/perl -e 'alarm 60; exec @ARGV' /usr/bin/env PYTHONPATH=/Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup:/Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/scripts /Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python -m pytest --collect-only -q /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests
```

Exit code: 0

```
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_upstream_session.py::UpstreamSessionConsumerTests::test_default_state_keeps_all_local_features_available
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_upstream_session.py::UpstreamSessionConsumerTests::test_expiry_revocation_and_reader_failure_remove_session_reference
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_upstream_session.py::UpstreamSessionConsumerTests::test_logout_clears_all_upstream_state
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_upstream_session.py::UpstreamSessionConsumerTests::test_missing_unknown_and_secret_fields_are_rejected_without_echoing_values
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_upstream_session.py::UpstreamSessionConsumerTests::test_refresh_does_not_call_reader_without_a_current_session
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_upstream_session.py::UpstreamSessionConsumerTests::test_refresh_uses_injected_reader_and_replaces_old_session
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_upstream_session.py::UpstreamSessionConsumerTests::test_rejected_and_unavailable_results_keep_local_workbench_complete
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_black_frames.py::BlackFrameContentTests::test_content_with_small_area_is_not_empty
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_black_frames.py::BlackFrameContentTests::test_historical_misflagged_frames_keep_their_content
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_black_frames.py::BlackFrameContentTests::test_isolated_codec_speckle_does_not_count_as_content
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_black_frames.py::BlackFrameContentTests::test_one_empty_frame_between_content_frames_is_reported_by_index
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_black_frames.py::BlackFrameContentTests::test_uniform_black_and_deep_gray_fail
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_render.py::ManifestTests::test_audio_required_and_mixed_modes_rejected
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_render.py::ManifestTests::test_export_ownership_lock_and_reusable_workspace
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_render.py::ManifestTests::test_failed_preflight_clears_previous_candidate_receipt
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_render.py::ManifestTests::test_refuses_unowned_output_and_overlapping_roots
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_render.py::ManifestTests::test_rejects_duplicate_and_unsafe_ids
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_render.py::ManifestTests::test_rejects_escape_and_invalid_frame_geometry
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_render.py::ManifestTests::test_rejects_gap_and_overlap
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_render.py::ManifestTests::test_requires_explicit_fixed_font
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_render.py::ManifestTests::test_runtime_failure_updates_status_and_preserves_verified_cache
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_render.py::ManifestTests::test_timeout_must_be_finite
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_render.py::BrowserRenderTests::test_corrupt_cached_frame_invalidates_only_that_shot
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_render.py::BrowserRenderTests::test_independent_solid_and_alpha_teaching_clips
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_render.py::BrowserRenderTests::test_missing_line14_repair_only_renders_failed_shot
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_render.py::BrowserRenderTests::test_per_shot_wav_and_mismatch_rejection
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_render.py::BrowserRenderTests::test_remote_asset_is_rejected
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_render.py::BrowserRenderTests::test_same_input_produces_same_frame_hashes_and_explicit_seek
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_render.py::BrowserRenderTests::test_three_shot_mp4_schedule_tracks_and_original_inputs
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_render.py::BrowserRenderTests::test_timeout_is_bounded_and_other_shots_continue
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_subtitle_wrapping.py::SubtitleWrappingTests::test_balanced_punctuation_break_is_preferred_and_closing_marks_cannot_lead
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_subtitle_wrapping.py::SubtitleWrappingTests::test_four_real_captions_have_no_orphan_punctuation_or_short_tail
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_subtitle_wrapping.py::SubtitleWrappingTests::test_full_film_45_cues_preserve_raw_speech_and_obey_display_rules
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_subtitle_wrapping.py::SubtitleWrappingTests::test_single_line_and_question_exclamation_marks_are_preserved
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_wave6_bridge_contracts.py::Wave6BridgeContractTests::test_blocked_result_keeps_bridge_identity_and_retry_can_replace_it
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_wave6_bridge_contracts.py::Wave6BridgeContractTests::test_local_material_match_uses_one_declared_model_for_analysis_and_generation
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_wave6_bridge_contracts.py::Wave6BridgeContractTests::test_runner_uses_shared_creative_contract_constants
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_wave6_bridge_contracts.py::Wave6BridgeContractTests::test_snapshot_refresh_rebuilds_candidate_without_mutating_pin_until_approved
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_wave6_localprompts_creator_context.py::LocalPromptCreatorContextTests::test_edit_log_context_carries_only_declared_creator_fields
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_wave6_localprompts_creator_context.py::LocalPromptCreatorContextTests::test_storyboard_prompt_uses_explicit_creator_context_without_inference
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::WordTimingTests::test_chunk_and_pending_are_explicit
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::WordTimingTests::test_cloud_rejects_mismatched_task_or_failed_subtask
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::WordTimingTests::test_cloud_transport_uses_real_protocol_without_paid_calls
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::WordTimingTests::test_cloud_words_are_preserved_as_acoustic_seconds
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::WordTimingTests::test_invalid_word_intervals_fail_closed
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::WordTimingTests::test_local_funasr_pairs_only_explicit_raw_tokens
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::WordTimingTests::test_mixed_segments_use_weakest_precision
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::WordTimingTests::test_no_words_never_interpolates
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::WordTimingTests::test_nonfinite_sentence_and_confidence_fail
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::WordTimingTests::test_overlapping_or_reversed_words_fail
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::WordTimingTests::test_paid_providers_require_explicit_live
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::WordTimingTests::test_partial_word_coverage_disables_auto_cut
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::WordTimingTests::test_schema_forbids_auto_cut_without_words
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::WordTimingTests::test_sidecar_raw_cloud_and_normalized_word_results
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::WordTimingTests::test_top_level_words_are_bound_to_their_segment
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SuggestionTests::test_animation_can_cross_segment_boundaries
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SuggestionTests::test_animation_duplicate_ids_and_empty_text_fail
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SuggestionTests::test_animation_word_boundaries_ambiguity_and_unmatched
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SuggestionTests::test_different_speakers_do_not_become_retake
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SuggestionTests::test_divergent_restart_remains_review_only_even_with_words
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SuggestionTests::test_forged_precision_and_out_of_source_timing_fail
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SuggestionTests::test_repeat_gap_and_minimum_text_boundaries
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SuggestionTests::test_repeated_sentence_and_half_sentence_restart
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SuggestionTests::test_repetition_can_skip_an_intervening_filler_segment
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SuggestionTests::test_restart_inside_one_asr_sentence
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SuggestionTests::test_sentence_animation_has_only_coarse_bounds
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SuggestionTests::test_sentence_only_animation_repeated_in_same_sentence_is_ambiguous
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SuggestionTests::test_sentence_only_repeat_inside_one_segment_has_no_cut
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SuggestionTests::test_silence_duration_boundaries_and_eof
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SuggestionTests::test_word_repetition_has_only_original_clock_cut
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SyntheticAudioTests::test_asr_word_overlap_vetoes_silence_auto_cut
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SyntheticAudioTests::test_cli_writes_suggestions_only_and_preserves_inputs
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SyntheticAudioTests::test_minimum_silence_duration_is_adjustable
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SyntheticAudioTests::test_noise_threshold_is_adjustable
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SyntheticAudioTests::test_probe_uses_audio_clock_when_video_is_longer
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SyntheticAudioTests::test_process_project_sidecar_persists_word_contract
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SyntheticAudioTests::test_real_ffmpeg_and_stub_asr_find_silence_and_repeat
.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_word_timing_and_spoken_edit.py::SyntheticAudioTests::test_sentence_timing_disables_every_cut

2075 tests collected in 5.03s
```

## Command 3

```
nice -n 10 /usr/bin/perl -e 'alarm 60; exec @ARGV' /usr/bin/env PYTHONPATH=/Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup:/Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/scripts /Users/vsiyo/Desktop/创业项目/内容创作/production-desk/.venv/bin/python -m pytest -q /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_desktop_openapi_route_sync.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_full_checklist_acceptance.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_archive_location_config.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_chatcut_mcp.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_edit_backend_interface.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_music_library.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_project_structure_v2.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_media_manifest_contract.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_p3_tiering_preview.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_p5b_storyboard_contracts.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_video_black_frames.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_openclaw_queue.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_jianying_draft_plan.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_review_capability_registry.py /Users/vsiyo/.agy-account2/.local/share/task-worktrees/production-desk-org-cleanup/tests/test_demo_trial.py
```

Exit code: 0

```
......................................................... [ 41%]
...................................................... [ 80%]
...........................                                           [100%]
138 passed, 36 subtests passed in 6.78s
```
