# Model and hardware research snapshot

Checked against primary sources on 2026-09-07. This document records candidates and future checks, not an installed model, benchmark result, or promise that a training job fits memory.

## Verified candidate identities

The owner's Qwen3.8-27B identifier is valid. Its official model card describes image/video support and Apache-2.0 license metadata. Its configuration uses the Qwen3.5-family architecture; the marketing version must not be used to guess a loader class.

| Role | Model ID | Immutable model revision | Declared architecture |
| --- | --- | --- | --- |
| Owner's intended candidate | `Qwen/Qwen3.8-27B` | `1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0` | `Qwen3_5ForConditionalGeneration` |
| Smaller comparison/integration candidate | `Qwen/Qwen3-VL-8B-Instruct` | `0c351dd01ed87e9c1b53cbc748cba10e6187ff3b` | `Qwen3VLForConditionalGeneration` |

The smaller model also declares image/video support and Apache-2.0 metadata. Neither candidate has been evaluated for this project, so neither is established as the best Arknights policy. The base models' license metadata does not choose a license for this repository or grant rights to training recordings.

Sources:

- [Qwen3.8 model card](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/README.md)
- [Qwen3.8 configuration](https://huggingface.co/Qwen/Qwen3.8-27B/blob/1d4bf0f2ff6012fd82039f2fa52739d0dd7c60c0/config.json)
- [Qwen3-VL-8B model card](https://huggingface.co/Qwen/Qwen3-VL-8B-Instruct/blob/0c351dd01ed87e9c1b53cbc748cba10e6187ff3b/README.md)

## Hardware identity is not a memory measurement

NVIDIA documents H20 SXM5 141 GB as well as the 96 GB variant. Its NIM support matrix also names H20-3e (141 GB) separately from H200. The owner's H20/141 GB description should not be automatically corrected to H200. These sources do not establish which device or GPU partition is available to the project, or whether a proposed video fine-tuning workload will fit.

Sources:

- [NVIDIA H20 reference](https://docs.nvidia.com/ai-enterprise/release-8/latest/infra-software/vgpu/reference/hopper-h20.html)
- [NVIDIA NIM VLM 2.1.1 support matrix](https://docs.nvidia.com/nim/vision-language-models/2.1.1/support-matrix.html)

## Proposed integration checks

The following are project decisions to implement in a separate bounded plan:

1. Keep the model backend disabled by default; config validation must not download weights, load a GPU model, or start a service.
2. Use an explicitly approved local snapshot, immutable revision, and locked dependencies. Record file and processor/template hashes. No implicit network fallback or remotely fetched model code.
3. Match the declared architecture to the loader. Keep typed image/video messages and the processor's output fields together, rather than treating vision input as ordinary text tokens.
4. Begin with one local image and bounded input/output budgets. Test multi-image/video sampling, ordering, pixel/frame limits, and timestamps separately before enabling video.
5. Parse only the final proposed action. Record the thinking-mode choice explicitly; do not let model defaults bypass the JSON action contract.
6. Preserve the existing guard and require fresh observations after execution. A model's confidence or a controller API return value is not proof of a correct game action.

Reference for the Qwen3.5-family processor/loading interface: [Transformers v5.16.1 model documentation](https://github.com/huggingface/transformers/blob/v5.16.1/docs/source/en/model_doc/qwen3_5.md). This source version has not been installed or tested here.

## Fine-tuning preparation, not a launch instruction

After private data and GPU access are approved, a small image-only adapter experiment on the 8B candidate is a useful first compatibility test. It does not commit the project to that model. Start with short causal observation windows and a tiny bounded batch; verify labels, assistant-only loss, matched trainable modules, and actual optimizer-step memory before increasing frames, resolution, sequence length, or batch size. Compare against an unchanged pretrained baseline and report peak memory and latency as measured values.

The official Qwen3-VL training source provides image/video demonstration formatting and LoRA support. Its model-name dispatch must not be reused unchanged for Qwen3.8: a broad `qwen3` match selects the Qwen3-VL class, which is not Qwen3.8's declared architecture. Training Qwen3.8 requires a separately checked backend.

Sources:

- [Pinned Qwen3-VL training README](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/qwen-vl-finetune/README.md)
- [Pinned trainer source](https://github.com/QwenLM/Qwen3-VL/blob/96588727e44c78b25ba03ea03b8e12f7e64fd0da/qwen-vl-finetune/qwenvl/train/train_qwen.py)

Outstanding evidence: H02/H03 data and label review, H05 actual GPU/software/preflight measurements, and later H04/H07 real-game validation. No weights were downloaded and no training or model inference was run during this research.
