import json
import os
import re
import ipdb

class Tools:
    @staticmethod
    def read_json(filename):
        with open(filename, 'r', encoding='utf8') as f:
            return json.load(f)

    @staticmethod
    def write_json(filename, data):
        with open(filename, 'w', encoding='utf8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    @staticmethod
    def write_jsonl(filename, data):
        with open(filename, 'w', encoding='utf8') as f:
            for d in data:
                f.write(json.dumps(d, ensure_ascii=False) + '\n')

    @staticmethod
    def read_file(filename):
        with open(filename, 'r', encoding='utf8') as f:
            return f.read()

    @staticmethod
    def explore_dir(dirname):
        return os.listdir(dirname)
    
    @staticmethod
    def is_dir(filename):
        return os.path.isdir(filename)
    
    @staticmethod
    def is_file(filename):
        return os.path.isfile(filename)

class Path:
    gt_cases = 'apps_dataset/APPS/APPS/test/{task_no}/input_output.json'
    cano_solutions = 'apps_dataset/APPS/APPS/test/{task_no}/solutions.json'
    question = 'apps_dataset/APPS/APPS/test/{task_no}/question.txt'
    meta_data = 'apps_dataset/APPS/APPS/test/{task_no}/metadata.json'
    starter_code = 'apps_dataset/APPS/APPS/test/{task_no}/starter_code.py'

class Variables:
    reserve_notions = [
        '-----Input-----', '-----Output-----',
        '-----Constraints-----', '-----Notes-----',
        '-----Partial Score-----', '-----Print-----',
        '-----Inputs-----', '-----Outputs-----',
        '-----Subscores-----', '-----Input:-----', '-----Output:-----',
        '-----Constraints:-----', '-----Scoring-----', '-----Subtasks-----',
        '-----Input & Output-----', '-----Input Format:-----', '-----Output Format:-----',
        '-----Input format-----', '-----Output format-----', '-----Test data-----',
        '-----Subtaks-----', '-----Live evaluation data-----', '-----Task-----',
        '-----Latitude and longitude-----', '-----Limits-----',
        '-----Warning-----', '-----Description-----', '-----Limits and additional notes-----',
        '-----Input description-----', '-----Output description-----',
        '-----Thumb position-----', '-----Input Specification-----', '-----Output Specification-----',
        '-----Partial Scores-----', '-----Problem Statement-----', 
    ]

class Parser:
    @staticmethod
    def find_ones_without_notion(questions):
        for question, task_no in questions:
            found_notions = re.findall(r'\n(-----.*?-----)\n', question)
            if len(found_notions) == 0:
            #     ipdb.set_trace()
            # if '-----' not in question:
                print(task_no)
    
    @staticmethod
    def get_all_notions(questions):
        notions = set()
        for question, task_no in questions:
            found_notions = re.findall(r'\n(-----.*?-----)\n', question)
            new_notions = [i for i in found_notions if i not in notions]
            if len(new_notions) > 0:
                os.system('clear')
                print(question)
                print(new_notions)
                print(task_no)
                ipdb.set_trace()
            notions |= set(new_notions)
        return notions
    
    @staticmethod
    def remove_unexpected_notions(questions, examples):
        handled_questions = dict()
        toxic_tasks = list()
        for question, task_no in questions:
            handled_question = []
            flag_of_wanted = True
            flag_of_keyword = False
            for line in question.split('\n'):
                if line.startswith('-----') and line.endswith('-----'):
                    flag_of_keyword = True
                    if line not in Variables.reserve_notions:
                        flag_of_wanted = False
                    else:
                        flag_of_wanted = True
                if flag_of_wanted:
                    handled_question.append(line)
            if not flag_of_keyword:
                toxic_tasks.append(task_no)
            handled_question_str = '\n'.join(handled_question)
            handled_questions[task_no] = '\'\'\'\n' + handled_question_str + examples[task_no] + '\'\'\'\n' + 'def solution(stdin: str) -> str:\n'
        # print(toxic_tasks)
        return handled_questions

    @staticmethod
    def build_test_code(intput_output):
        test_code = '\ndef check(candidate):\n'
        raw_inputs = intput_output['inputs']
        raw_outputs = intput_output['outputs']
        
        inputs = []
        for input in raw_inputs:
            if isinstance(input, str):
                inputs.append(input)
            else:
                inputs.append(str([input])[1:-1])
        
        outputs = []
        for output in raw_outputs:
            if isinstance(output, str):
                outputs.append(output)
            else:
                outputs.append(str([output])[1:-1])

        example_io = '\n-----Sample Input-----\n'
        example_io += inputs[0].strip() + '\n'
        example_io += '\n-----Sample Output-----\n' + outputs[0].strip() + '\n'

        for idx, input in enumerate(inputs):
            test_code += '    assert candidate({}) == {}\n'.format(str([input.strip()])[1:-1], str([outputs[idx].strip()])[1:-1])
        return test_code, example_io

if __name__ == '__main__':
    tasks_to_skip = []
    
    # read all meta data
    meta_datas = dict()
    for task_no in Tools.explore_dir('apps_dataset/APPS/APPS/test'):
        meta_data = Tools.read_json(Path.meta_data.format(task_no=task_no))
        # if meta_data['difficulty'] != 'introductory':
        #     tasks_to_skip.append(task_no)
        meta_datas[task_no] = meta_data

    # read all gt cases
    tests = dict()
    examples = dict()
    for task_no in Tools.explore_dir('apps_dataset/APPS/APPS/test'):
        test_code, example_io = Parser.build_test_code(Tools.read_json(Path.gt_cases.format(task_no=task_no)))
        # if len(test_code) < 1:
        #     tasks_to_skip.append(task_no)
        tests[task_no] = test_code
        examples[task_no] = example_io
    
    # read all questions
    questions = []
    for task_no in Tools.explore_dir('apps_dataset/APPS/APPS/test'):
        questions.append((Tools.read_file(Path.question.format(task_no=task_no)), task_no))
    
    # get all notions
    # notions = Parser.get_all_notions(questions)
    handled_questions = Parser.remove_unexpected_notions(questions, examples)

    records = []
    for task_no in Tools.explore_dir('apps_dataset/APPS/APPS/test'):
        if task_no in tasks_to_skip:
            continue
        meta_data = meta_datas[task_no]
        test = tests[task_no]
        prompt = handled_questions[task_no]
        record = {
            'task_id': f'APPSEval/{task_no}',
            'entry_point': 'solution',
            # 'prompt': prompt,
            'prompt': prompt + '    pass\n\n# check the correctness of solution\nassert ',
            'test': test,
            'meta_data': meta_data,
            'canonical_solution': ''
        }
        records.append(record)

    Tools.write_jsonl('apps_hme_for_test_case_gen.jsonl', records)
