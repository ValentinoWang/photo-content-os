# ui-copy-quality: FAIL

- errors: 1
- warnings: 0

studio/video_workflow.py:322: [copy.raw-identifier] (error) "p[0]] accepted.add(item['id']) elif op == 'retract' and not animation: if ite..."
    why: machine identifier 'video_suggestion_not_applied' is shown as prose
    fix: translate it to product language, or wrap it in <code>/.mono when the reader must see the field name, or allowlist it in the lexicon with a reason
