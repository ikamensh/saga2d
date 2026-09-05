# Audio asset provenance

These WAV files are original Shardbound compositions generated from
`eador/sound.py` by `tools/build_eador_audio.py`, using the project's shared
`saga2d.synth` sample primitives. No external recordings, sampled instruments,
Eador assets or externally sourced melodies are included.

The files and composition source are covered by the repository MIT license
(`LICENSE`). `audio-manifest.json` records generator version, source/runtime
versions, file hashes, durations, peaks and review status. Rebuild before
packaging; runtime playback requires only the shipped WAVs.

Technical verification is not listening or artistic approval. Human listening
review remains required; see `docs/eador-audio.md` and the separate cue sampler
under `docs/evidence/shardbound-cue-sampler.wav`.
