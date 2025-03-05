SYSTEM_PROMPT = """
You may use the following imports:

import sys
import time
import itertools
from itertools import accumulate, product, permutations, combinations
import collections
from collections import Counter, OrderedDict, deque, defaultdict, ChainMap
from functools import lru_cache
import math

Respond in the following format:

<reasoning>
...
</reasoning>
<answer>
...
</answer>   
"""
import re
from wasmtime import Config, Engine, Linker, Module, Store, WasiConfig
import math


class Result:
    def __init__(self, result, mem_size, data_len, consumed):
        self.result = result
        self.mem_size = mem_size
        self.data_len = data_len
        self.consumed = consumed

    def __str__(self):
        return f"""\
result:

{self.result}

mem size pages of 64kb: {self.mem_size}
data length: {self.data_len}
fuel consumed: {self.consumed}
"""
def axolotl_acecode_transform(cfg, *args, **kwargs):
    def transform_fn(example, tokenizer=None):
        return {
            "prompt": [{"role": "user", "content": SYSTEM_PROMPT + "\n\n" + example["question"]}],
            "answers": example["test_cases"],
        }
    return transform_fn, {"remove_columns": ["question", "test_cases"]}

def run_python_code(code: str, fuel: int = 400_000_000) -> str:
    engine_cfg = Config()
    engine_cfg.consume_fuel = True
    engine_cfg.cache = True

    linker = Linker(Engine(engine_cfg))
    linker.define_wasi()

    python_module = Module.from_file(linker.engine, "wasm/python-3.12.0.wasm")

    config = WasiConfig()

    config.argv = ("python", "-c", code)
    config.preopen_dir(".", "/")

    # with tempfile.TemporaryDirectory() as chroot:
    #     out_log = os.path.join(chroot, "out.log")
    #     err_log = os.path.join(chroot, "err.log")
    #     config.stdout_file = out_log
    #     config.stderr_file = err_log

    store = Store(linker.engine)

    # Limits how many instructions can be executed:
    store.set_fuel(fuel)
    store.set_wasi(config)
    instance = linker.instantiate(store, python_module)

    #     # _start is the default wasi main function
    start = instance.exports(store)["_start"]
    #     mem = instance.exports(store)["memory"]
    #     try:
    start(store)
    #     except Exception as e:
    #         with open(err_log) as f:
    #             error = f.read()
    #         return error

    #     with open(out_log) as f:
    #         result = f.read()

    #     return Result(result, mem.size(store), mem.data_len(store), fuel - store.get_fuel())


def compiles_reward_func(predicted_answers: list[str], **kwargs) -> list[float]:
    results = []
    for predicted_answer in predicted_answers:
        try:
            run_python_code(predicted_answer)
            results.append(1.0)
        except Exception as e:
            results.append(-1.0)
    return results


def answer_reward_func(completions: list[str], answers: list[str], **kwargs) -> list[float]:
    """
    Reward function for having the correct answer.
    """
    results = []
    for completion, test_cases in zip(completions, answers):
        num_success = 0
        for test_case in test_cases:
            try:
                print(completion + "\n\n" + test_case)
                run_python_code(completion + "\n\n" + test_case)
                num_success += 1
            except Exception as e:
                # print(e)
                pass
        accuracy = num_success / len(test_cases)
        results.append(math.pow(accuracy, 4))
    return results


def correctness_reward_func(completions: list[list[dict]], answers: list[list[str]], **kwargs) -> list[float]:
    """
    Args:
        completions (list[list[dict]]): A list of completions from the model to be scored.
        answers (list[list[str]]): A list of answers to be scored against. These will be in the format
            ["assert fn() == test_case_zero", "assert fn() == test_case_one", ...]

    """
    import pdb; pdb.set_trace()
    # let's extract the correct fn name from the first element of the answers
    # i.e. the text after assert and before () and also not including anything after ()
    correct_fn_names = [answers[0].split("(")[0].split(" ")[1] for answers in answers]

    fn_name_rewards = [
        0.5 if correct_fn_name in completion[0]["content"] else 0.0
        for correct_fn_name, completion in zip(correct_fn_names, completions)
    ]

    model_answers = [extract_xml_answer(completion[0]["content"]) for completion in completions]

    # check if the completion compiles
    compile_rewards = []
    for fn_name_reward, completion in zip(fn_name_rewards, completions):
        if fn_name_reward == 1.0:
            compile_rewards.append(compiles_reward_func([completion]))
        else:
            compile_rewards.append(0.0)

    # check if the completion is correct
    correct_rewards = []
    for i in range(len(completions)):
        if fn_name_rewards[i] == 1.0 and compile_rewards[i] == 1.0:
            correct_rewards.append(answer_reward_func(model_answers[i], answers[i]))
        else:
            correct_rewards.append(0.0)

    # combine all the rewards
    return [
        fn_name_reward + compile_reward + correct_reward
        for fn_name_reward, compile_reward, correct_reward in zip(fn_name_rewards, compile_rewards, correct_rewards)
    ]


def extract_xml_answer(text: str) -> str:
    # collect the answer between the last <answer></answer> tag
    answer = text.split("<answer>")[-1]
    answer = answer.split("</answer>")[0]
    return answer.strip()


def xmlcount_reward_func(completions, **kwargs) -> list[float]:
    """
    Reward function for having exactly one of each <reasoning>, </reasoning>, <answer>, and </answer> tag.
    """
    contents = [completion[0]["content"] for completion in completions]
    return [count_xml(c) for c in contents]

def strict_format_reward_func(completions, **kwargs) -> list[float]:
    """Reward function that checks if the completion has a specific format."""
    pattern = r"^<reasoning>\n.*?\n</reasoning>\n<answer>\n.*?\n</answer>\s?$"
    responses = [completion[0]["content"] for completion in completions]
    matches = [re.match(pattern, r) for r in responses]
    return [0.5 if match else 0.0 for match in matches]

def count_xml(text) -> float:
    count = 0.0
    if text.count("<reasoning>") == 1:
        count += 0.125
    if text.count("</reasoning>") == 1:
        count += 0.125
    if text.count("<answer>") == 1:
        count += 0.125
    if text.count("</answer>") == 1:
        count += 0.125
        # penalize extra tokens after the answer tag
    count -= (len(text.split("</answer>")[-1]) - 1) * 0.001
    return count


if __name__ == "__main__":
    example_completion = [
        [
            {
                "role": "user",
                "content": """
    <reasoning>
    ...
    </reasoning>
    <answer>
    def foo(a):
        return a + 
    </answer>""",
            }
        ]
    ]

    answers = [["assert foo(1) == 2", "assert foo(2) == 5"]]

    print("-" * 100)
    correct_fn_name = answers[0][0].split("(")[0].split(" ")[1]
    fn_name_rewards = [
        0.2 if correct_fn_name in example_completion else 0.0 for example_completion in example_completion
    ]
    print("fn name reward", fn_name_rewards)
    print("-" * 100)
    print("format reward", xmlcount_reward_func(example_completion))
    print("-" * 100)
    model_answers = [extract_xml_answer(example_completion[0])]
    print("-" * 100)
    print("compiles reward", compiles_reward_func(model_answers))
    print("-" * 100)
    print("answer reward", answer_reward_func(model_answers, answers))
    print("-" * 100)
    print("correctness reward", correctness_reward_func(example_completion, answers))
