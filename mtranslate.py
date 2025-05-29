#!/usr/bin/env python3
import argparse
import base64
import time
import os

from mlx_engine.generate import load_model, load_draft_model, create_generator, tokenize
from mlx_engine.utils.token import Token
from mlx_engine.model_kit import VALID_KV_BITS, VALID_KV_GROUP_SIZE
from transformers import AutoTokenizer, AutoProcessor

DEFAULT_PROMPT = "Explain the rules of chess in one sentence"
DEFAULT_TEMP = 0.8

DEFAULT_SYSTEM_PROMPT = {"role": "system", "content": "You are a helpful assistant."}


def setup_arg_parser():
    """Set up and return the argument parser."""
    parser = argparse.ArgumentParser(
        description="LM Studio mlx-engine inference script"
    )
    parser.add_argument(
        "--model",
        required=True,
        type=str,
        help="The file system path to the model",
    )
    parser.add_argument(
        "--prompt",
        default=DEFAULT_PROMPT,
        type=str,
        help="Message to be processed by the model",
    )
    parser.add_argument(
        "--images",
        type=str,
        nargs="+",
        help="Path of the images to process",
    )
    parser.add_argument(
        "--temp",
        default=DEFAULT_TEMP,
        type=float,
        help="Temperature for sampling. Higher values increase randomness",
    )
    parser.add_argument(
        "--stop-strings",
        type=str,
        nargs="+",
        help="List of strings that will trigger generation to stop when encountered",
    )
    parser.add_argument(
        "--top-logprobs",
        type=int,
        default=0,
        help="Number of top token probabilities to return per token. Must be <= MAX_TOP_LOGPROBS",
    )
    parser.add_argument(
        "--max-kv-size",
        type=int,
        help="Max context size of the model",
    )
    parser.add_argument(
        "--kv-bits",
        type=int,
        choices=VALID_KV_BITS,
        help="Number of bits for KV cache quantization. Must be between 3 and 8 (inclusive)",
    )
    parser.add_argument(
        "--kv-group-size",
        type=int,
        choices=VALID_KV_GROUP_SIZE,
        help="Group size for KV cache quantization",
    )
    parser.add_argument(
        "--quantized-kv-start",
        type=int,
        help="When --kv-bits is set, start quantizing the KV cache from this step onwards",
    )
    parser.add_argument(
        "--draft-model",
        type=str,
        help="The file system path to the draft model for speculative decoding",
    )
    parser.add_argument(
        "--num-draft-tokens",
        type=int,
        help="Number of tokens to draft when using speculative decoding",
    )
    parser.add_argument(
        "--print-prompt-progress",
        action="store_true",
        help="Enable printed prompt processing progress callback",
    )
    # New generation parameters
    parser.add_argument(
        "--repetition-penalty",
        type=float,
        help="Penalty factor for repeated tokens. Higher values discourage repetition",
    )
    parser.add_argument(
        "--repetition-context-size",
        type=int,
        default=20,
        help="Number of previous tokens to consider for repetition penalty. Defaults to 20",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        help="Top-p (nucleus) sampling parameter",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        help="Top-k sampling parameter",
    )
    parser.add_argument(
        "--min-p",
        type=float,
        help="Minimum probability threshold for token sampling",
    )
    parser.add_argument(
        "--min-tokens-to-keep",
        type=int,
        help="Minimum number of tokens to keep during sampling",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducible generation",
    )
    parser.add_argument(
        "--json-schema",
        type=str,
        help="JSON schema for structured output generation",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=1024,
        help="Maximum number of tokens to generate. Defaults to 1024",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--speculative-decoding",
        dest="speculative_decoding_toggle",
        action="store_true",
        help="Enable speculative decoding regardless of draft model loading",
    )
    group.add_argument(
        "--disable-speculative-decoding",
        dest="speculative_decoding_toggle",
        action="store_false",
        help="Disable speculative decoding even if a draft model is loaded",
    )
    parser.set_defaults(speculative_decoding_toggle=None)
    return parser


def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


class GenerationStatsCollector:
    def __init__(self):
        self.start_time = time.time()
        self.first_token_time = None
        self.total_tokens = 0
        self.num_accepted_draft_tokens: int | None = None

    def add_tokens(self, tokens: list[Token]):
        """Record new tokens and their timing."""
        if self.first_token_time is None:
            self.first_token_time = time.time()

        draft_tokens = sum(1 for token in tokens if token.from_draft)
        if self.num_accepted_draft_tokens is None:
            self.num_accepted_draft_tokens = 0
        self.num_accepted_draft_tokens += draft_tokens

        self.total_tokens += len(tokens)

    def print_stats(self):
        """Print generation statistics."""
        end_time = time.time()
        total_time = end_time - self.start_time
        time_to_first_token = self.first_token_time - self.start_time
        effective_time = total_time - time_to_first_token
        tokens_per_second = (
            self.total_tokens / effective_time if effective_time > 0 else float("inf")
        )
        print("\n\nGeneration stats:")
        print(f" - Tokens per second: {tokens_per_second:.2f}")
        if self.num_accepted_draft_tokens is not None:
            print(
                f" - Number of accepted draft tokens: {self.num_accepted_draft_tokens}"
            )
        print(f" - Time to first token: {time_to_first_token:.2f}s")
        print(f" - Total tokens generated: {self.total_tokens}")
        print(f" - Total time: {total_time:.2f}s")


def resolve_model_path(model_arg):
    # If it's a full path or local file, return as-is
    if os.path.exists(model_arg):
        return model_arg

    # Check common local directories
    local_paths = [
        os.path.expanduser("~/.lmstudio/models"),
        os.path.expanduser("~/.cache/lm-studio/models"),
    ]

    for path in local_paths:
        full_path = os.path.join(path, model_arg)
        if os.path.exists(full_path):
            return full_path

    raise ValueError(f"Could not find model '{model_arg}' in local directories")


if __name__ == "__main__":
    # Parse arguments
    parser = setup_arg_parser()
    args = parser.parse_args()
    if isinstance(args.images, str):
        args.images = [args.images]

    # Set up prompt processing callback
    def prompt_progress_callback(percent):
        if args.print_prompt_progress:
            width = 40  # bar width
            filled = int(width * percent / 100)
            bar = "█" * filled + "░" * (width - filled)
            print(f"\rProcessing prompt: |{bar}| ({percent:.1f}%)", end="", flush=True)
            if percent >= 100:
                print()  # new line when done
        else:
            pass

    # Load the model
    model_path = resolve_model_path(args.model)
    print("Loading model...", end="\n", flush=True)
    model_kit = load_model(
        str(model_path),
        max_kv_size=args.max_kv_size,
        trust_remote_code=False,
        kv_bits=args.kv_bits,
        kv_group_size=args.kv_group_size,
        quantized_kv_start=args.quantized_kv_start,
    )
    print("\rModel load complete ✓", end="\n", flush=True)

    # Load draft model if requested
    if args.draft_model:
        load_draft_model(model_kit=model_kit, path=resolve_model_path(args.draft_model))

    # Tokenize the prompt
    prompt = args.prompt

    # Handle the prompt according to the input type
    images_base64 = []
    if args.images:
        tf_tokenizer = AutoProcessor.from_pretrained(model_path)
        images_base64 = [image_to_base64(img_path) for img_path in args.images]
        conversation = [
            DEFAULT_SYSTEM_PROMPT,
            {
                "role": "user",
                "content": [
                    {"type": "text", "content": prompt},
                    *[
                        {"type": "image", "base64": image_b64}
                        for image_b64 in images_base64
                    ],
                ],
            },
        ]
    else:
        tf_tokenizer = AutoTokenizer.from_pretrained(model_path)
        conversation = [
            DEFAULT_SYSTEM_PROMPT,
            {"role": "user", "content": prompt},
        ]
    prompt = tf_tokenizer.apply_chat_template(
        conversation, tokenize=False, add_generation_prompt=True
    )
    prompt_tokens = tokenize(model_kit, prompt)

    # Record top logprobs
    logprobs_list = []

    # Initialize generation stats collector
    stats_collector = GenerationStatsCollector()

    # Generate the response with all supported parameters
    generator = create_generator(
        model_kit,
        prompt_tokens,
        prompt_progress_callback=prompt_progress_callback,
        images_b64=images_base64,
        stop_strings=args.stop_strings,
        top_logprobs=args.top_logprobs,
        repetition_penalty=args.repetition_penalty,
        repetition_context_size=args.repetition_context_size,
        temp=args.temp,
        top_p=args.top_p,
        top_k=args.top_k,
        min_p=args.min_p,
        min_tokens_to_keep=args.min_tokens_to_keep,
        seed=args.seed,
        json_schema=args.json_schema,
        max_tokens=args.max_tokens,
        speculative_decoding_toggle=args.speculative_decoding_toggle,
        num_draft_tokens=args.num_draft_tokens,
    )
    for generation_result in generator:
        print(generation_result.text, end="", flush=True)
        stats_collector.add_tokens(generation_result.tokens)
        logprobs_list.extend(generation_result.top_logprobs)

        if generation_result.stop_condition:
            stats_collector.print_stats()
            print(
                f"\nStopped generation due to: {generation_result.stop_condition.stop_reason}"
            )
            if generation_result.stop_condition.stop_string:
                print(f"Stop string: {generation_result.stop_condition.stop_string}")

    if args.top_logprobs:
        [print(x) for x in logprobs_list]
