import yaml
import xml.etree.ElementTree as ET
from datetime import datetime
import difflib
import re
import time
import traceback
from cprint import cprint

class TCM:

    def __init__(self):
        with open("config.yaml", "rb") as f:
            plugin_config = yaml.safe_load(f)

        config = plugin_config["TCM"]
        self.enabled = config["enable"]
        self.user_state = None # 正在问诊的用户状态
        self.tree = config['tree']
        self.prescription = config['prescription']

    def process_message(self, msg):
        # 如果TCM功能未启用，则直接返回
        if not self.enabled:
            return

        # 如果消息内容为"中药"，则发送帮助信息
        if msg == '中药':
            cprint.info("中药药方查询, 可输入最明显症状后开始问诊\n开始问诊命令格式: '症状序号', 若不确定你也可以选择输入'q 主要症状', 系统会自动帮你匹配关联度最高的诊断路径(但不保证你的症状会出现在诊断过程中)\n在问诊过程中, 请按照提示回答, 提示中可能仅为部分症状, 请严格按照提示回答(符合问题中症状即可), 每次回答同样以'中药 '开头, 直到问诊结束\n返回结果: 问诊期间的问题或者最终结论(药方)\n\n目前支持的病症:\n1.感冒, 发热等 (具体症状请参见问诊过程)\n2.水肿, 咳嗽, 发热等\n3.咳嗽, 虚弱, 心悸等\n4.咽部难受, 腹泻呕吐等\n5.发热, 食欲不佳等\n\n注意事项:\n1.提供的意见仅供参考, 如有不适请及时就医\n2.本项目不提供处方, 请勿用于实际治疗\n3.本项目提供的剂量仅为常用剂量, 具体剂量请根据医生建议或实际情况进行灵活调整\n\n命令示例:\n中药 -> 获取帮助信息\n1 -> 查询感冒, 发热等\nq 我心烦 -> 查询心烦相关的诊断路径\n是 -> 在问诊过程中答案为是")
            return

        try:
            f = 0
            # 如果消息内容为"结束"，则结束问诊
            if msg == '结束':
                cprint.ok('问诊结束')
                # 重置用户状态
                self.user_state = None
                return
            try:
                # 如果消息内容以"q "开头，则进行模糊匹配
                if msg.startswith('q '):
                    # 如果用户已经在问诊中，则发送提示信息
                    if self.user_state is not None:
                        cprint.warn("你已经处于一个问诊中了")

                    # 截取"q "后面的内容
                    msg = msg[2:]
                    # 进行模糊匹配
                    paths, _ = self.find_most_similar_question(self.tree, msg)
                    # 如果没有找到匹配的路径，则发送提示信息
                    if not paths:
                        cprint.fatal(f'没有找到与"{msg}"相关的诊断路径')
                        return
                    # 设置用户状态
                    self.user_state = self.tree[paths[0][0]]
                    s = ""
                    # 将匹配的路径拼接成字符串
                    for path in paths:
                        s += ' -> '.join(path) + '\n'
                    s = s.strip('\n')
                    # 发送匹配的路径
                    cprint.info(f"找到以下可能的诊断路径, 若系统匹配不准确, 你还可以尝试以下诊断:{s}\n")
                    # 发送提示信息
                    cprint.ok("问诊开始, 请按照提示回答, 回答格式: '中药 选项'")
                    f = 1
                else:
                    # 将消息内容转换为整数
                    msg = int(msg) - 1
                    if list(self.tree.keys())[msg]:
                        if self.user_state is not None:
                            cprint.warn("你已经处于一个问诊中了")

                        self.user_state = self.tree[list(self.tree.keys())[msg]]
                        cprint.ok("问诊开始, 请按照提示回答, 回答格式: '选项'")
                        f = 1
            except:
                pass

            if self.user_state is None:
                return

            elif msg in self.user_state:
                self.user_state = self.user_state[msg]

            elif f == 0:
                return

            if isinstance(self.user_state, str):
                title = self.user_state
                prescription = self.prescription[title]
                cprint.ok(f'问诊结束, 药方名称: {title}, 药方内容: {prescription}')
                if '附子' in prescription:
                    cprint.warn(f'注意, {title}内含有附子类风险方剂, 使用不当会导致中毒, 请谨慎使用')
                self.user_state = None
                return

            else:
                cprint.info(self.user_state['q'])

            return
        except Exception as e:
            cprint.err(f"发生错误: {e}")

    @staticmethod
    def find_most_similar_question(tree, user_input):
        # 遍历树形结构，返回所有问题及其路径
        def traverse_tree(tree, path=[]):
            # 定义一个空列表，用于存储问题及其路径
            questions = []
            # 遍历树形结构的每个节点
            for key, value in tree.items():
                # 如果节点的值是一个字典
                if isinstance(value, dict):
                    # 如果字典中包含问题
                    if 'q' in value:
                        # 将问题及其路径添加到列表中
                        questions.append((value['q'], path + [key]))
                    # 递归调用traverse_tree函数，继续遍历子节点
                    questions.extend(traverse_tree(value, path + [key]))
            # 返回问题及其路径的列表
            return questions

        questions = traverse_tree(tree)
        question_texts = [q[0] for q in questions]
        most_similar = difflib.get_close_matches(user_input, question_texts, n=3, cutoff=0.0)

        paths = []
        ques = []
        if most_similar:
            for question, path in questions:
                if question in most_similar:
                    paths.append(path)
                    ques.append(question)
            return paths, ques
        return [], []

if __name__ == "__main__":
    tcm = TCM()
    msg = input("请输入命令(输入中药查看用法, exit退出程序, tree查看决策树): ")
    while msg != "exit":
        if msg == "tree":
            print(tcm.tree)
            msg = input("$ ")
            continue
        tcm.process_message(msg)
        msg = input("$ ")