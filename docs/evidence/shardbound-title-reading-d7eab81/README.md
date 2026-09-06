# Title reading verification

Implementation: `d7eab81`. Both reports retain their original pre-commit HEAD;
every recorded source hash was compared with the committed implementation.
[Provenance](provenance.json) records the comparison and retained file hashes.

- 1,123 full tests passed in 98.29 seconds.
- [Native input verification](native.json): 216 hero/world/difficulty layouts,
  both reading sizes, three windows and 345 inputs. Apply/Cancel/restart,
  seed selection, both launch modes, invalid files, actual directory errors,
  explicit backup restoration and retained save files pass.
- A valid save path over 700 characters yields a complete four-page diagnostic.
  Every character remains present; paging and settings preserve the chosen run.
- [Linked stress](linked.json): 12 model campaigns, 12 scene runs and 2,208 inputs.
  Tribes also passes 60 AI games and 20 scene runs.

All five retained PNGs were opened and inspected: the normal larger title,
ordinary directory failure, first/final long diagnostic pages and restarted
Settings. Text and controls fit without losing the complete descriptions.
This verifies a development increment; release, platform and human-playtest
gates remain open. The old packaged Mac artifact predates these changes.
